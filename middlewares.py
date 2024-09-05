from typing import Any, Awaitable, Callable, Dict, MutableMapping, Optional

from aiogram import BaseMiddleware
from aiogram.dispatcher.flags import get_flag
from aiogram.types import TelegramObject, User
from cachetools import TTLCache

DEFAULT_TTL = 1.5
DEFAULT_KEY = "default"


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(
        self,
        default_key: Optional[str] = DEFAULT_KEY,
        default_ttl: float = DEFAULT_TTL,
        **ttl_map: float,
    ) -> None:
        self.default_key = default_key
        self.caches: Dict[str, MutableMapping[int, None]] = {}

        if default_key:
            ttl_map[default_key] = default_ttl

        for name, ttl in ttl_map.items():
            self.caches[name] = TTLCache(maxsize=10_000, ttl=ttl)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Optional[Any]:
        import asyncio  # Add this import at the top of the file

        user: Optional[User] = data.get("event_from_user")

        if user is None:
            return await asyncio.shield(handler(event, data))

        throttling_key = get_flag(data, "throttling_key", default=self.default_key)
        if not throttling_key or throttling_key not in self.caches:
            return await asyncio.shield(handler(event, data))

        if user.id in self.caches[throttling_key]:
            return None

        self.caches[throttling_key][user.id] = None
        return await asyncio.shield(handler(event, data))
