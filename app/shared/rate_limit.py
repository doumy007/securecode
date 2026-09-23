"""Rate limiter ligero en memoria (single-instance).
Protege el login contra fuerza bruta sin añadir dependencias.
"""
import time
import threading
from typing import Dict, List

_LOCK = threading.Lock()
_ATTEMPTS: Dict[str, List[float]] = {}


class LoginRateLimiter:
    def __init__(self, max_attempts: int = 5, window_seconds: float = 900):
        self.max_attempts = max_attempts
        self.window = window_seconds

    def _key(self, username: str, ip: str) -> str:
        return f"{ip}:{username.lower()}"

    def check(self, username: str, ip: str) -> bool:
        """True si el intento debe permitirse; False si está bloqueado temporalmente."""
        now = time.time()
        key = self._key(username, ip)
        with _LOCK:
            attempts = [t for t in _ATTEMPTS.get(key, []) if now - t < self.window]
            _ATTEMPTS[key] = attempts
            return len(attempts) < self.max_attempts

    def record_failure(self, username: str, ip: str) -> int:
        now = time.time()
        key = self._key(username, ip)
        with _LOCK:
            attempts = [t for t in _ATTEMPTS.get(key, []) if now - t < self.window]
            attempts.append(now)
            _ATTEMPTS[key] = attempts
            return len(attempts)

    def reset(self, username: str, ip: str) -> None:
        with _LOCK:
            _ATTEMPTS.pop(self._key(username, ip), None)

    def remaining(self, username: str, ip: str) -> int:
        now = time.time()
        key = self._key(username, ip)
        with _LOCK:
            attempts = [t for t in _ATTEMPTS.get(key, []) if now - t < self.window]
            return max(0, self.max_attempts - len(attempts))