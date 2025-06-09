"""
Менеджер OpenAI клиентов
Предоставляет единый асинхронный клиент для всего проекта
"""

from openai import AsyncOpenAI

from config_manager import get_openai_api_key

# Единственный экземпляр асинхронного OpenAI клиента
_client_async = None


def get_async_openai_client() -> AsyncOpenAI:
    """Возвращает единственный экземпляр асинхронного OpenAI клиента"""
    global _client_async
    if _client_async is None:
        api_key = get_openai_api_key()
        _client_async = AsyncOpenAI(api_key=api_key)
    return _client_async


async def close_openai_client():
    """Асинхронно закрывает OpenAI клиент"""
    global _client_async
    if _client_async is not None:
        await _client_async.close()
        _client_async = None
