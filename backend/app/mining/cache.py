"""Simple in-process TTL cache for expensive mining computations."""
from __future__ import annotations

import time
from typing import Any, Callable

_STORE: dict[str, tuple[float, Any]] = {}


def cached(key: str, ttl_seconds: float, builder: Callable[[], Any]) -> Any:
    hit = _STORE.get(key)
    if hit is not None and (time.time() - hit[0]) < ttl_seconds:
        return hit[1]
    value = builder()
    _STORE[key] = (time.time(), value)
    return value


def clear_cache() -> None:
    _STORE.clear()


def cache_size() -> int:
    return len(_STORE)
