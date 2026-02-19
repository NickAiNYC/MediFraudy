"""
Modern Redis caching layer for 2026 performance
"""

import json
import logging
from typing import Optional, Any, Union
import redis.asyncio as redis
from config import settings

logger = logging.getLogger(__name__)

class CacheManager:
    """Production-ready Redis cache manager"""
    
    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self.redis_client: Optional[redis.Redis] = None
        self.default_ttl = 3600  # 1 hour default
    
    async def connect(self):
        """Initialize Redis connection"""
        if not self.redis_url:
            logger.warning("Redis URL not configured, caching disabled")
            return
        
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20,
                retry_on_timeout=True
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info("✅ Redis cache connected successfully")
            
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            self.redis_client = None
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis_client:
            return None
        
        try:
            value = await self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning(f"Cache get error for {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        if not self.redis_client:
            return False
        
        try:
            ttl = ttl or self.default_ttl
            serialized = json.dumps(value, default=str)
            await self.redis_client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.warning(f"Cache set error for {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.redis_client:
            return False
        
        try:
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete error for {key}: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern"""
        if not self.redis_client:
            return 0
        
        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                return await self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Cache clear pattern error for {pattern}: {e}")
            return 0
    
    def cache_key(self, prefix: str, *args) -> str:
        """Generate consistent cache key"""
        key_parts = [prefix] + [str(arg) for arg in args]
        return ":".join(key_parts)

# Singleton instance
cache_manager = CacheManager()

# Cache decorators
def cached(prefix: str, ttl: int = 3600):
    """Decorator for caching function results"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = cache_manager.cache_key(prefix, *args, str(sorted(kwargs.items())))
            
            # Try to get from cache
            cached_result = await cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_manager.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator

# Specific cache functions for our use cases
async def cache_provider_stats(provider_id: int, stats: dict) -> bool:
    """Cache provider statistics"""
    key = cache_manager.cache_key("provider_stats", provider_id)
    return await cache_manager.set(key, stats, ttl=1800)  # 30 minutes

async def get_cached_provider_stats(provider_id: int) -> Optional[dict]:
    """Get cached provider statistics"""
    key = cache_manager.cache_key("provider_stats", provider_id)
    return await cache_manager.get(key)

async def cache_analytics_dashboard(data: dict) -> bool:
    """Cache analytics dashboard"""
    key = cache_manager.cache_key("analytics_dashboard")
    return await cache_manager.set(key, data, ttl=300)  # 5 minutes

async def get_cached_analytics_dashboard() -> Optional[dict]:
    """Get cached analytics dashboard"""
    key = cache_manager.cache_key("analytics_dashboard")
    return await cache_manager.get(key)

async def cache_search_results(query: str, results: list) -> bool:
    """Cache search results"""
    key = cache_manager.cache_key("search", query)
    return await cache_manager.set(key, results, ttl=600)  # 10 minutes

async def invalidate_provider_cache(provider_id: int) -> bool:
    """Invalidate all cache entries for a provider"""
    patterns = [
        f"provider_stats:{provider_id}",
        f"provider_details:{provider_id}",
        f"provider_claims:{provider_id}"
    ]
    
    deleted = 0
    for pattern in patterns:
        deleted += await cache_manager.clear_pattern(pattern)
    
    return deleted > 0
