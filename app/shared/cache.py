import time
from typing import Any, Optional


class TTLCache:
    """Caché en memoria por proceso con expiración por TTL.

    La BD externa (hosting compartido) responde ~0.4-0.6 s por consulta;
    para el dashboard y listados que solo cambian cada varios
    segundos/minutos, el caché evita N consultas por cada página cargada.
    """

    def __init__(self):
        self._store: dict[str, tuple[float, Any]] = {}
        self._writes = 0

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() > expires_at:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any, ttl_seconds: int = 60) -> None:
        self._store[key] = (time.monotonic() + ttl_seconds, value)
        self._writes += 1
        if self._writes % 100 == 0:
            self._sweep()

    def _sweep(self) -> None:
        now = time.monotonic()
        expired = [k for k, (exp, _) in self._store.items() if now > exp]
        for k in expired:
            self._store.pop(k, None)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear_prefix(self, prefix: str) -> None:
        for k in [k for k in self._store if k.startswith(prefix)]:
            self._store.pop(k, None)

    def clear(self) -> None:
        self._store.clear()


cache = TTLCache()