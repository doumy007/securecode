from typing import Optional, Any
import json


class CacheService:
    def __init__(self):
        self._cache = {}
        self._ttl = {}

    async def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            return self._cache[key]
        return None

    async def set(self, key: str, value: Any, ttl_seconds: int = 300):
        self._cache[key] = value

    async def delete(self, key: str):
        self._cache.pop(key, None)

    async def clear(self):
        self._cache.clear()
