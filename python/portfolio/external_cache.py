from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable, Hashable
from typing import TypeVar

T = TypeVar("T")

_LOCK = threading.RLock()
_CACHE: dict[tuple[str, Hashable], tuple[float, object]] = {}
_MAX_ENTRIES = int(os.environ.get("QPORT_EXTERNAL_CACHE_MAX", "512"))


def _evict_if_needed() -> None:
    """Bound the process-local cache to prevent unbounded RAM growth.

    Expired entries are dropped first, then the oldest inserted entries (dicts
    preserve insertion order) until there is room for one more entry.
    """
    if len(_CACHE) < _MAX_ENTRIES:
        return
    now = time.monotonic()
    for key in [k for k, (exp, _) in _CACHE.items() if exp <= now]:
        _CACHE.pop(key, None)
    while len(_CACHE) >= _MAX_ENTRIES:
        try:
            _CACHE.pop(next(iter(_CACHE)))
        except StopIteration:
            break


def ttl_from_env(name: str, default_seconds: int) -> int:
    """Return a non-negative cache TTL from environment configuration."""
    raw = os.environ.get(name)
    if raw in (None, ""):
        return max(0, int(default_seconds))
    try:
        return max(0, int(float(raw)))
    except (TypeError, ValueError):
        return max(0, int(default_seconds))


def cached_external_call(
    namespace: str,
    key: Hashable,
    loader: Callable[[], T],
    *,
    ttl_seconds: int,
    clone: Callable[[T], T] | None = None,
    bypass: bool = False,
) -> T:
    """Best-effort in-memory cache for slow external provider calls.

    This cache is intentionally process-local. On Vercel it helps warm instances
    avoid repeating identical outbound calls, while persistent/domain caches
    remain the source of truth across cold starts and instances.
    """
    ttl = max(0, int(ttl_seconds))
    cache_key = (str(namespace), key)
    now = time.monotonic()

    if not bypass and ttl > 0:
        with _LOCK:
            entry = _CACHE.get(cache_key)
            if entry is not None:
                expires_at, value = entry
                if expires_at > now:
                    return clone(value) if clone is not None else value  # type: ignore[arg-type,return-value]
                _CACHE.pop(cache_key, None)

    value = loader()
    if ttl > 0:
        stored = clone(value) if clone is not None else value
        with _LOCK:
            _evict_if_needed()
            _CACHE[cache_key] = (now + ttl, stored)
    return clone(value) if clone is not None else value


def clear_external_cache(namespace: str | None = None) -> None:
    """Clear the warm-runtime cache, primarily for tests and explicit refreshes."""
    with _LOCK:
        if namespace is None:
            _CACHE.clear()
            return
        target = str(namespace)
        for key in [key for key in _CACHE if key[0] == target]:
            _CACHE.pop(key, None)
