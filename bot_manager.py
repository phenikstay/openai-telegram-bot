from typing import Optional

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config_manager import get_telegram_token

# Глобальная переменная для хранения единственного экземпляра bot
_bot_instance: Optional[Bot] = None


def get_bot() -> Bot:
    """
    Возвращает единственный экземпляр Bot.
    Создает bot при первом вызове.
    """
    global _bot_instance

    if _bot_instance is None:
        token = get_telegram_token()
        _bot_instance = Bot(
            token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )

    return _bot_instance


def set_bot(bot: Bot) -> None:
    """
    Устанавливает экземпляр Bot.
    Используется для инжекции bot'а из main.py.
    """
    global _bot_instance
    _bot_instance = bot


async def close_bot() -> None:
    """
    Асинхронно закрывает сессию bot'а и сбрасывает экземпляр.
    """
    global _bot_instance
    if _bot_instance is not None:
        try:
            await _bot_instance.session.close()
        except Exception as e:
            # Логируем ошибку, но не прерываем выполнение
            import logging

            logging.warning(f"Ошибка при закрытии сессии бота: {e}")
        finally:
            _bot_instance = None
