from __future__ import annotations

import time
from threading import Lock
from typing import Generic, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    """Simple in-memory time-to-live cache.

    Pure infrastructure concern, NOT source-stated -- exists to protect
    Twelve Data's free-tier rate limit (a real constraint found in
    practice, not a trading-methodology rule). Multiple near-simultaneous
    requests for the same (source, symbol, timeframe) -- several browser
    tabs, the chart's poll and the signal WebSocket's poll overlapping --
    would otherwise each hit the upstream API independently. A short TTL
    means only the first of a burst actually calls out; the rest share its
    result.

    Thread-safe (uvicorn can run sync route handlers in a thread pool),
    process-lifetime only -- same scoping as SignalRegistry in state.py,
    not persisted across restarts.
    """

    def __init__(self, ttl_seconds: float = 20.0) -> None:
        self.ttl_seconds = ttl_seconds
        self._store: dict[tuple, tuple[float, T]] = {}
        self._lock = Lock()

    def get(self, key: tuple) -> T | None:
        with self._lock:
            entry = self._store.get(key)
        if entry is None:
            return None
        cached_at, value = entry
        if time.monotonic() - cached_at > self.ttl_seconds:
            return None
        return value

    def set(self, key: tuple, value: T) -> None:
        with self._lock:
            self._store[key] = (time.monotonic(), value)
