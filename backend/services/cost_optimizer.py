"""Cost optimization layer for DeepSeek API and expensive computations.

Wraps the existing cache layer to provide:
- Automatic result caching with configurable TTL (default: 24h)
- Cache hit/miss tracking for cost reporting
- Content-addressed caching via MD5 key hashing
- Graceful fallback when Redis is unavailable

Target: < $20/month API spend via aggressive caching.
"""

import hashlib
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional

from services.cache import (
    _get_redis,
    _memory_cache,
    _MEMORY_CACHE_MAX,
)

logger = logging.getLogger(__name__)

# Default cache TTL: 24 hours (aggressive caching for cost optimisation)
DEFAULT_CACHE_TTL = 86400


class CostOptimizer:
    """Cache-first wrapper that minimises API and compute costs.

    Usage::

        optimizer = CostOptimizer()
        result = optimizer.get_cached_or_compute(
            key="risk_tensor:provider:42",
            compute_func=lambda: expensive_calculation(),
        )
    """

    def __init__(self, cache_ttl: int = DEFAULT_CACHE_TTL):
        self.cache_ttl = cache_ttl
        self.hits = 0
        self.misses = 0
        self.last_report = datetime.now()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def get_cached_or_compute(
        self,
        key: str,
        compute_func: Callable[[], Any],
        ttl: Optional[int] = None,
    ) -> Any:
        """Return a cached result or compute, cache, and return.

        Args:
            key: Human-readable cache key (will be hashed internally).
            compute_func: Zero-argument callable that produces the result.
            ttl: Override for cache TTL in seconds.

        Returns:
            The cached or freshly-computed result.
        """
        cache_key = self._make_key(key)
        effective_ttl = ttl if ttl is not None else self.cache_ttl

        # --- Try Redis first ---
        client = _get_redis()
        if client:
            try:
                cached = client.get(cache_key)
                if cached:
                    self.hits += 1
                    self._maybe_report()
                    return json.loads(cached)
            except Exception as exc:
                logger.warning("Redis get error in CostOptimizer: %s", exc)

        # --- Try in-memory fallback ---
        entry = _memory_cache.get(cache_key)
        if entry and entry.get("expires_at", 0) > time.time():
            self.hits += 1
            self._maybe_report()
            return entry.get("data")

        # --- Cache miss: compute ---
        self.misses += 1
        result = compute_func()

        # --- Store result ---
        self._store(cache_key, result, effective_ttl, client)
        self._maybe_report()
        return result

    def invalidate(self, key: str) -> None:
        """Remove a cached entry."""
        cache_key = self._make_key(key)
        client = _get_redis()
        if client:
            try:
                client.delete(cache_key)
            except Exception:
                pass
        _memory_cache.pop(cache_key, None)

    def get_stats(self) -> Dict[str, Any]:
        """Return cache hit/miss statistics."""
        total = self.hits + self.misses
        return {
            "hits": self.hits,
            "misses": self.misses,
            "total": total,
            "hit_rate": round(self.hits / total, 4) if total else 0.0,
            "estimated_savings_usd": round(self.hits * 0.001, 2),
        }

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _make_key(key: str) -> str:
        digest = hashlib.sha256(key.encode()).hexdigest()[:32]
        return f"medifraudy:cost:v1:{digest}"

    def _store(
        self,
        cache_key: str,
        data: Any,
        ttl: int,
        redis_client: Any,
    ) -> None:
        if redis_client:
            try:
                redis_client.setex(cache_key, ttl, json.dumps(data, default=str))
                return
            except Exception as exc:
                logger.warning("Redis set error in CostOptimizer: %s", exc)

        # In-memory fallback
        now = time.time()
        if len(_memory_cache) >= _MEMORY_CACHE_MAX:
            expired = [
                k for k, v in _memory_cache.items()
                if v.get("expires_at", 0) <= now
            ]
            for k in expired:
                del _memory_cache[k]
            if len(_memory_cache) >= _MEMORY_CACHE_MAX:
                oldest = min(
                    _memory_cache,
                    key=lambda k: _memory_cache[k].get("expires_at", 0),
                )
                del _memory_cache[oldest]

        _memory_cache[cache_key] = {
            "data": data,
            "expires_at": now + ttl,
        }

    def _maybe_report(self) -> None:
        if datetime.now() - self.last_report > timedelta(hours=1):
            stats = self.get_stats()
            logger.info(
                "CostOptimizer — hits: %d, misses: %d, savings: $%.2f",
                stats["hits"],
                stats["misses"],
                stats["estimated_savings_usd"],
            )
            self.last_report = datetime.now()


# Module-level singleton
optimizer = CostOptimizer()
