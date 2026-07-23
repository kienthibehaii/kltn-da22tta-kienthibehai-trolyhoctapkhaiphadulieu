# reliability/cache_manager.py - Multi-layer Cache with Redis
"""
Production caching:
- Redis for distributed cache
- In-memory LRU cache
- Cache warming
- Cache invalidation
- TTL management
"""

import json
import hashlib
import pickle
from typing import Any, Optional, Callable
from functools import wraps
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

# Try to import Redis, fallback to in-memory
try:
    import redis
    from redis import Redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, using in-memory cache only")


class LRUCache:
    """Simple LRU cache for in-memory caching"""
    
    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self.cache = {}
        self.access_order = []
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key in self.cache:
            # Update access order
            self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        return None
    
    def set(self, key: str, value: Any):
        """Set value in cache"""
        if key in self.cache:
            self.access_order.remove(key)
        elif len(self.cache) >= self.capacity:
            # Evict least recently used
            lru_key = self.access_order.pop(0)
            del self.cache[lru_key]
        
        self.cache[key] = value
        self.access_order.append(key)
    
    def delete(self, key: str):
        """Delete from cache"""
        if key in self.cache:
            del self.cache[key]
            self.access_order.remove(key)
    
    def clear(self):
        """Clear all cache"""
        self.cache.clear()
        self.access_order.clear()
    
    def size(self) -> int:
        """Get cache size"""
        return len(self.cache)


class CacheManager:
    """Multi-layer cache manager"""
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        memory_cache_size: int = 1000
    ):
        # In-memory cache (L1)
        self.memory_cache = LRUCache(capacity=memory_cache_size)
        
        # Redis cache (L2)
        self.redis_client = None
        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = Redis.from_url(
                    redis_url,
                    decode_responses=False,
                    socket_timeout=5,
                    socket_connect_timeout=5
                )
                self.redis_client.ping()
                logger.info("✅ Redis cache connected")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}. Using memory cache only")
                self.redis_client = None
    
    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key"""
        # Create deterministic key from args
        key_data = f"{prefix}:{args}:{sorted(kwargs.items())}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"{prefix}:{key_hash}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get from cache (L1 -> L2)"""
        # Try L1 (memory)
        value = self.memory_cache.get(key)
        if value is not None:
            return value
        
        # Try L2 (Redis)
        if self.redis_client:
            try:
                data = self.redis_client.get(key)
                if data:
                    value = pickle.loads(data)
                    # Populate L1
                    self.memory_cache.set(key, value)
                    return value
            except Exception as e:
                logger.warning(f"Redis get error: {e}")
        
        return None
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ):
        """Set in cache (L1 + L2)"""
        # Set in L1
        self.memory_cache.set(key, value)
        
        # Set in L2
        if self.redis_client:
            try:
                data = pickle.dumps(value)
                if ttl:
                    self.redis_client.setex(key, ttl, data)
                else:
                    self.redis_client.set(key, data)
            except Exception as e:
                logger.warning(f"Redis set error: {e}")
    
    def delete(self, key: str):
        """Delete from cache"""
        self.memory_cache.delete(key)
        
        if self.redis_client:
            try:
                self.redis_client.delete(key)
            except Exception as e:
                logger.warning(f"Redis delete error: {e}")
    
    def clear(self, pattern: Optional[str] = None):
        """Clear cache"""
        self.memory_cache.clear()
        
        if self.redis_client and pattern:
            try:
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
            except Exception as e:
                logger.warning(f"Redis clear error: {e}")
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        stats = {
            "memory_cache_size": self.memory_cache.size(),
            "redis_connected": self.redis_client is not None
        }
        
        if self.redis_client:
            try:
                info = self.redis_client.info("stats")
                stats["redis_keys"] = self.redis_client.dbsize()
                stats["redis_hits"] = info.get("keyspace_hits", 0)
                stats["redis_misses"] = info.get("keyspace_misses", 0)
            except Exception as e:
                logger.warning(f"Redis stats error: {e}")
        
        return stats


# Global cache manager
cache_manager = None


def init_cache(redis_url: Optional[str] = None):
    """Initialize global cache manager"""
    global cache_manager
    cache_manager = CacheManager(redis_url=redis_url)
    return cache_manager


def cached(
    prefix: str,
    ttl: int = 3600,
    use_memory: bool = True,
    use_redis: bool = True
):
    """
    Decorator for caching function results
    
    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds
        use_memory: Use in-memory cache
        use_redis: Use Redis cache
    
    Usage:
        @cached("translation", ttl=3600)
        async def translate(text: str) -> str:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            if cache_manager is None:
                return await func(*args, **kwargs)
            
            # Generate cache key
            key = cache_manager._make_key(prefix, *args, **kwargs)
            
            # Try to get from cache
            cached_value = cache_manager.get(key)
            if cached_value is not None:
                logger.debug(f"Cache HIT: {prefix}")
                return cached_value
            
            # Cache miss, execute function
            logger.debug(f"Cache MISS: {prefix}")
            result = await func(*args, **kwargs)
            
            # Store in cache
            cache_manager.set(key, result, ttl=ttl)
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            if cache_manager is None:
                return func(*args, **kwargs)
            
            key = cache_manager._make_key(prefix, *args, **kwargs)
            
            cached_value = cache_manager.get(key)
            if cached_value is not None:
                logger.debug(f"Cache HIT: {prefix}")
                return cached_value
            
            logger.debug(f"Cache MISS: {prefix}")
            result = func(*args, **kwargs)
            
            cache_manager.set(key, result, ttl=ttl)
            
            return result
        
        # Return appropriate wrapper
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class TranslationCache:
    """Specialized cache for translations"""
    
    def __init__(self, cache_mgr: CacheManager):
        self.cache = cache_mgr
        self.prefix = "translation"
    
    def get(self, text: str, target_lang: str) -> Optional[str]:
        """Get cached translation"""
        key = f"{self.prefix}:{target_lang}:{hashlib.md5(text.encode()).hexdigest()}"
        return self.cache.get(key)
    
    def set(self, text: str, target_lang: str, translation: str):
        """Cache translation"""
        key = f"{self.prefix}:{target_lang}:{hashlib.md5(text.encode()).hexdigest()}"
        self.cache.set(key, translation, ttl=86400)  # 24 hours


class EmbeddingCache:
    """Specialized cache for embeddings"""
    
    def __init__(self, cache_mgr: CacheManager):
        self.cache = cache_mgr
        self.prefix = "embedding"
    
    def get(self, text: str) -> Optional[list]:
        """Get cached embedding"""
        key = f"{self.prefix}:{hashlib.md5(text.encode()).hexdigest()}"
        return self.cache.get(key)
    
    def set(self, text: str, embedding: list):
        """Cache embedding"""
        key = f"{self.prefix}:{hashlib.md5(text.encode()).hexdigest()}"
        self.cache.set(key, embedding, ttl=604800)  # 7 days


class ResponseCache:
    """Specialized cache for RAG responses"""
    
    def __init__(self, cache_mgr: CacheManager):
        self.cache = cache_mgr
        self.prefix = "response"
    
    def get(self, question: str, context_hash: str) -> Optional[dict]:
        """Get cached response"""
        key = f"{self.prefix}:{hashlib.md5(f'{question}:{context_hash}'.encode()).hexdigest()}"
        return self.cache.get(key)
    
    def set(self, question: str, context_hash: str, response: dict):
        """Cache response"""
        key = f"{self.prefix}:{hashlib.md5(f'{question}:{context_hash}'.encode()).hexdigest()}"
        self.cache.set(key, response, ttl=3600)  # 1 hour
