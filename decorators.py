from functools import wraps
from typing import Union

from aiogram.types import Message, CallbackQuery

from config_manager import get_owner_ids


def owner_only(func):
    """
    Декоратор для проверки доступа к боту.
    Разрешает выполнение функции только владельцам бота.
    """

    @wraps(func)
    async def wrapper(event: Union[Message, CallbackQuery], *args, **kwargs):
        user_id = event.from_user.id
        owner_ids = get_owner_ids()

        if user_id not in owner_ids:
            if isinstance(event, Message):
                await event.answer("Извините, у вас нет доступа к этому боту.")
            else:  # CallbackQuery
                await event.answer("Извините, у вас нет доступа к этому боту.")
            return

        return await func(event, *args, **kwargs)

    return wrapper


def owner_only_with_user_id_display(func):
    """
    Декоратор для проверки доступа к боту с отображением User ID.
    Используется для команды /start.
    """

    @wraps(func)
    async def wrapper(event: Union[Message, CallbackQuery], *args, **kwargs):
        user_id = event.from_user.id
        owner_ids = get_owner_ids()

        if user_id not in owner_ids:
            if isinstance(event, Message):
                await event.answer(
                    f"<i>Извините, у вас нет доступа к этому боту.\n"
                    f"Ваш User ID:</i> <b>{user_id}</b>"
                )
            else:  # CallbackQuery
                await event.answer("Извините, у вас нет доступа к этому боту.")
            return

        return await func(event, *args, **kwargs)

    return wrapper
