import json
import logging
from collections import OrderedDict
from typing import Dict

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from classes import SessionLocal, UserDataModel

# Локальный кэш с ограничением размера
# Используем OrderedDict для LRU-поведения
_MAX_CACHE_SIZE = 1000  # Максимальное количество пользователей в кэше
users_data: Dict[int, dict] = OrderedDict()


def _manage_cache_size() -> None:
    """
    Управляет размером кэша, удаляя самые старые записи при превышении лимита.
    """
    while len(users_data) > _MAX_CACHE_SIZE:
        # Удаляем самую старую запись (первую в OrderedDict)
        oldest_user_id = next(iter(users_data))
        users_data.pop(oldest_user_id)
        logging.info(f"Удален из кэша пользователь {oldest_user_id} (кэш переполнен)")


async def get_or_create_user_data(user_id: int):
    """
    Возвращает словарь-данные пользователя, либо создаёт запись в БД, если её нет.
    Если возникает гонка при создании, обрабатываем IntegrityError и повторно получаем запись.
    """
    # Если пользователь уже в кэше, перемещаем его в конец (LRU)
    if user_id in users_data:
        # Перемещаем в конец для LRU-поведения
        users_data.move_to_end(user_id)
        return users_data[user_id]

    str_user_id = str(user_id)
    try:
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
                    raise RuntimeError(
                        "Не удалось создать или найти пользователя в БД."
                    )

                await session.refresh(user_db_obj)

            user_data_dict = user_db_obj.to_dict()

            # Добавляем в кэш и управляем его размером
            users_data[user_id] = user_data_dict
            _manage_cache_size()

            return user_data_dict

    except Exception as e:
        logging.error(f"Ошибка при получении данных пользователя {user_id}: {e}")
        raise


async def save_user_data(user_id: int) -> None:
    """
    Сохраняем изменения из локального кэша в БД.
    """
    user_data_dict = users_data.get(user_id)
    if not user_data_dict:
        logging.warning(
            f"Попытка сохранить данные пользователя {user_id}, но он не найден в кэше"
        )
        return

    str_user_id = str(user_id)
    try:
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

                # Поля для ассистентов
                user_db_obj.assistant_thread_id = user_data_dict["assistant_thread_id"]
                user_db_obj.assistant_thread_id_2 = user_data_dict[
                    "assistant_thread_id_2"
                ]
                user_db_obj.assistant_thread_id_3 = user_data_dict[
                    "assistant_thread_id_3"
                ]
                user_db_obj.current_assistant = user_data_dict["current_assistant"]

                # ID ассистентов
                user_db_obj.assistant_id_1 = user_data_dict["assistant_id_1"]
                user_db_obj.assistant_id_2 = user_data_dict["assistant_id_2"]
                user_db_obj.assistant_id_3 = user_data_dict["assistant_id_3"]

                await session.commit()
            else:
                # Если записи нет - создаём
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
                    # Поля для ассистентов
                    assistant_thread_id=user_data_dict["assistant_thread_id"],
                    assistant_thread_id_2=user_data_dict["assistant_thread_id_2"],
                    assistant_thread_id_3=user_data_dict["assistant_thread_id_3"],
                    current_assistant=user_data_dict["current_assistant"],
                    # ID ассистентов
                    assistant_id_1=user_data_dict["assistant_id_1"],
                    assistant_id_2=user_data_dict["assistant_id_2"],
                    assistant_id_3=user_data_dict["assistant_id_3"],
                )
                session.add(new_obj)
                await session.commit()

    except Exception as e:
        logging.error(f"Ошибка при сохранении данных пользователя {user_id}: {e}")
        raise
