"""Risk score caching layer using Redis or in-memory fallback.

Caches computed risk scores to avoid expensive recalculation on every request.
Cache entries expire after a configurable TTL (default: 1 hour).
Falls back to an in-memory LRU cache if Redis is unavailable.
"""

import json
import logging
import time
from functools import lru_cache
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Default cache TTL in seconds (1 hour)
DEFAULT_TTL = 3600

_redis_client = None
_redis_available = None


def _get_redis():
    """Lazily connect to Redis, caching the client."""
    global _redis_client, _redis_available
    if _redis_available is False:
        return None
    if _redis_client is not None:
        return _redis_client
    try:
        import redis
        client = redis.Redis(
            host="redis",
            port=6379,
            db=0,
            socket_connect_timeout=2,
            socket_timeout=2,
            decode_responses=True,
        )
        client.ping()
        _redis_client = client
        _redis_available = True
        logger.info("Redis cache connected")
        return client
    except Exception:
        _redis_available = False
        logger.info("Redis unavailable — using in-memory cache fallback")
        return None


# In-memory fallback cache
_memory_cache: Dict[str, Dict[str, Any]] = {}
_MEMORY_CACHE_MAX = 500


def _cache_key(prefix: str, identifier: Any) -> str:
    return f"medifraudy:{prefix}:{identifier}"


def get_cached_risk_score(provider_id: int) -> Optional[Dict]:
    """Retrieve a cached risk score for a provider."""
    key = _cache_key("risk_score", provider_id)
    client = _get_redis()
    if client:
        try:
            data = client.get(key)
            if data:
                logger.debug(f"Cache HIT for risk_score:{provider_id}")
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Redis get error: {e}")

    # Fallback to memory cache
    entry = _memory_cache.get(key)
    if entry and entry.get("expires_at", 0) > time.time():
        logger.debug(f"Memory cache HIT for risk_score:{provider_id}")
        return entry.get("data")
    return None


def set_cached_risk_score(
    provider_id: int, data: Dict, ttl: int = DEFAULT_TTL
) -> None:
    """Cache a computed risk score for a provider."""
    key = _cache_key("risk_score", provider_id)
    client = _get_redis()
    if client:
        try:
            client.setex(key, ttl, json.dumps(data, default=str))
            logger.debug(f"Cached risk_score:{provider_id} (TTL={ttl}s)")
            return
        except Exception as e:
            logger.warning(f"Redis set error: {e}")

    # Fallback to memory cache (evict oldest if full)
    if len(_memory_cache) >= _MEMORY_CACHE_MAX:
        oldest_key = min(_memory_cache, key=lambda k: _memory_cache[k].get("expires_at", 0))
        del _memory_cache[oldest_key]

    _memory_cache[key] = {
        "data": data,
        "expires_at": time.time() + ttl,
    }


def invalidate_risk_score(provider_id: int) -> None:
    """Remove a cached risk score (e.g., after new data ingestion)."""
    key = _cache_key("risk_score", provider_id)
    client = _get_redis()
    if client:
        try:
            client.delete(key)
        except Exception:
            pass
    _memory_cache.pop(key, None)


def get_cached_network_insights() -> Optional[Dict]:
    """Retrieve cached network insights."""
    key = _cache_key("network", "insights")
    client = _get_redis()
    if client:
        try:
            data = client.get(key)
            if data:
                return json.loads(data)
        except Exception:
            pass

    entry = _memory_cache.get(key)
    if entry and entry.get("expires_at", 0) > time.time():
        return entry.get("data")
    return None


def set_cached_network_insights(data: Dict, ttl: int = 1800) -> None:
    """Cache network insights (30 min default)."""
    key = _cache_key("network", "insights")
    client = _get_redis()
    if client:
        try:
            client.setex(key, ttl, json.dumps(data, default=str))
            return
        except Exception:
            pass

    if len(_memory_cache) >= _MEMORY_CACHE_MAX:
        oldest_key = min(_memory_cache, key=lambda k: _memory_cache[k].get("expires_at", 0))
        del _memory_cache[oldest_key]

    _memory_cache[key] = {
        "data": data,
        "expires_at": time.time() + ttl,
    }


def clear_all_caches() -> None:
    """Clear all cached data."""
    client = _get_redis()
    if client:
        try:
            for key in client.scan_iter("medifraudy:*"):
                client.delete(key)
        except Exception:
            pass
    _memory_cache.clear()
    logger.info("All caches cleared")
