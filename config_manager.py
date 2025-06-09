import configparser
from pathlib import Path
from typing import Set

# Инициализируем конфигурацию
_config = configparser.ConfigParser()
_config.read(Path(__file__).parent / "config.ini")


def get_config() -> configparser.ConfigParser:
    """Возвращает объект конфигурации"""
    return _config


def get_telegram_token() -> str:
    """Возвращает токен Telegram бота"""
    return _config.get("Telegram", "token")


def get_owner_ids() -> Set[int]:
    """Возвращает множество ID владельцев бота"""
    return {
        int(owner_id) for owner_id in _config.get("Telegram", "owner_id").split(",")
    }


def get_openai_api_key() -> str:
    """Возвращает API ключ OpenAI"""
    return _config.get("OpenAI", "api_key")


def get_openai_assistant_id(assistant_number: int = 1) -> str:
    """Возвращает ID ассистента OpenAI"""
    if assistant_number == 1:
        return _config.get("OpenAI", "assistant_id", fallback="")
    else:
        return _config.get("OpenAI", f"assistant_id_{assistant_number}", fallback="")
