import json

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from classes import SessionLocal, UserDataModel

users_data = {}


async def get_or_create_user_data(user_id: int):
    """
    Возвращает словарь-данные пользователя, либо создаёт запись в БД, если её нет.
    Если возникает гонка при создании, обрабатываем IntegrityError и повторно получаем запись.
    """
    if user_id in users_data:
        return users_data[user_id]

    str_user_id = str(user_id)
    async with SessionLocal() as session:
        stmt = select(UserDataModel).where(UserDataModel.user_id == str_user_id)
        result = await session.execute(stmt)
        user_db_obj = result.scalars().first()

        if not user_db_obj:
            user_db_obj = UserDataModel(user_id=str_user_id)
            session.add(user_db_obj)
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                result = await session.execute(stmt)
                user_db_obj = result.scalars().first()
                if not user_db_obj:
                    user_db_obj = UserDataModel(user_id=str_user_id)
                    session.add(user_db_obj)
                    await session.commit()

            if user_db_obj is None:
                raise RuntimeError("Не удалось создать или найти пользователя в БД.")

            await session.refresh(user_db_obj)

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
            user_db_obj.assistant_thread_id = user_data_dict["assistant_thread_id"]

            await session.commit()
        else:
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
                assistant_thread_id=user_data_dict["assistant_thread_id"],
            )
            session.add(new_obj)
            await session.commit()
