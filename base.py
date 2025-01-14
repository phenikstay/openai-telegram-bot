import json

from sqlalchemy import select

from classes import SessionLocal, UserDataModel

# Локальный кэш
users_data = {}


async def get_or_create_user_data(user_id: int):
    """
    Возвращает словарь-данные пользователя, либо создаёт запись в БД, если нет.
    """
    if user_id in users_data:
        return users_data[user_id]

    str_user_id = str(user_id)  # Приведение к строке, если нужно
    async with SessionLocal() as session:
        stmt = select(UserDataModel).where(UserDataModel.user_id == str_user_id)
        result = await session.execute(stmt)
        user_db_obj = result.scalars().first()

        if not user_db_obj:
            # Создаём новую запись в БД
            user_db_obj = UserDataModel(user_id=str_user_id)
            session.add(user_db_obj)
            await session.commit()
            await session.refresh(user_db_obj)

        # Превращаем модель в dict и кладём в кэш
        user_data_dict = user_db_obj.to_dict()
        users_data[user_id] = user_data_dict
        return user_data_dict


async def save_user_data(user_id: int) -> None:
    """
    Сохраняем изменения из локального кэша в БД.
    """
    user_data_dict = users_data.get(user_id)
    if not user_data_dict:
        return

    str_user_id = str(user_id)
    async with SessionLocal() as session:
        stmt = select(UserDataModel).where(UserDataModel.user_id == str_user_id)
        result = await session.execute(stmt)
        user_db_obj = result.scalars().first()

        if user_db_obj:
            # Обновляем поля
            user_db_obj.model = user_data_dict["model"]
            user_db_obj.model_message_info = user_data_dict["model_message_info"]
            user_db_obj.model_message_chat = user_data_dict["model_message_chat"]
            user_db_obj.messages = json.dumps(user_data_dict["messages"])
            user_db_obj.count_messages = user_data_dict["count_messages"]
            user_db_obj.max_out = user_data_dict["max_out"]
            user_db_obj.voice_answer = user_data_dict["voice_answer"]
            user_db_obj.system_message = user_data_dict["system_message"]
            user_db_obj.pic_grade = user_data_dict["pic_grade"]
            user_db_obj.pic_size = user_data_dict["pic_size"]

            await session.commit()
        else:
            # Если по какой-то причине записи нет - создаём
            new_obj = UserDataModel(
                user_id=str_user_id,
                model=user_data_dict["model"],
                model_message_info=user_data_dict["model_message_info"],
                model_message_chat=user_data_dict["model_message_chat"],
                messages=json.dumps(user_data_dict["messages"]),
                count_messages=user_data_dict["count_messages"],
                max_out=user_data_dict["max_out"],
                voice_answer=user_data_dict["voice_answer"],
                system_message=user_data_dict["system_message"],
                pic_grade=user_data_dict["pic_grade"],
                pic_size=user_data_dict["pic_size"],
            )
            session.add(new_obj)
            await session.commit()
