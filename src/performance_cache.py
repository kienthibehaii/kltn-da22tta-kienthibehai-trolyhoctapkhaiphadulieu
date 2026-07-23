"""
Phase 2.4 Component 10: Performance Cache Manager
Implements multi-level caching with TTL management and cache statistics
"""

from typing import Any, Dict, Optional, Callable, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import hashlib
import json
import threading
from functools import wraps


@dataclass
class CacheEntry:
    """Single cache entry with metadata"""
    key: str
    value: Any
    created_at: datetime
    expires_at: datetime
    hit_count: int = 0
    access_count: int = 0
    
    def is_expired(self) -> bool:
        """Check if entry has expired"""
        return datetime.now() > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if entry is valid (not expired)"""
        return not self.is_expired()
    
    def touch(self) -> None:
        """Update access statistics"""
        self.access_count += 1
    
    def mark_hit(self) -> None:
        """Mark as cache hit"""
        self.hit_count += 1


@dataclass
class CacheStats:
    """Cache performance statistics"""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    evictions: int = 0
    current_size: int = 0
    max_size: int = 0
    hit_ratio: float = 0.0
    memory_usage_bytes: int = 0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "total_requests": self.total_requests,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "evictions": self.evictions,
            "current_size": self.current_size,
            "max_size": self.max_size,
            "hit_ratio": round(self.hit_ratio, 3),
            "memory_usage_mb": round(self.memory_usage_bytes / (1024*1024), 2)
        }


class PerformanceCache:
    """Multi-level cache manager with TTL and statistics"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        Initialize cache manager
        
        Args:
            max_size: Maximum number of entries in cache
            default_ttl: Default time-to-live in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, CacheEntry] = {}
        self.stats = CacheStats(max_size=max_size)
        self.lock = threading.RLock()
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = datetime.now()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        with self.lock:
            self.stats.total_requests += 1
            
            # Periodic cleanup
            self._cleanup_if_needed()
            
            if key not in self.cache:
                self.stats.cache_misses += 1
                return None
            
            entry = self.cache[key]
            
            if entry.is_expired():
                del self.cache[key]
                self.stats.cache_misses += 1
                return None
            
            entry.touch()
            entry.mark_hit()
            self.stats.cache_hits += 1
            self._update_stats()
            
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
            
        Returns:
            True if successful, False if cache full
        """
        with self.lock:
            ttl = ttl or self.default_ttl
            
            # Check if we need to evict
            if len(self.cache) >= self.max_size and key not in self.cache:
                self._evict_oldest()
            
            now = datetime.now()
            expires_at = now + timedelta(seconds=ttl)
            
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=now,
                expires_at=expires_at
            )
            
            self.cache[key] = entry
            self._update_stats()
            
            return True
    
    def delete(self, key: str) -> bool:
        """
        Delete entry from cache
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted, False if not found
        """
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                self._update_stats()
                return True
            return False
    
    def clear(self) -> int:
        """
        Clear entire cache
        
        Returns:
            Number of entries cleared
        """
        with self.lock:
            count = len(self.cache)
            self.cache.clear()
            self.stats = CacheStats(max_size=self.max_size)
            return count
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        with self.lock:
            return self.stats.to_dict()
    
    def cache_response(self, ttl: int = 300) -> Callable:
        """
        Decorator to cache function results
        
        Args:
            ttl: Cache TTL in seconds
            
        Returns:
            Decorator function
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                # Generate cache key
                cache_key = self._generate_key(func.__name__, args, kwargs)
                
                # Check cache
                cached_value = self.get(cache_key)
                if cached_value is not None:
                    return cached_value
                
                # Execute function
                result = func(*args, **kwargs)
                
                # Cache result
                self.set(cache_key, result, ttl)
                
                return result
            
            return wrapper
        return decorator
    
    # ========== Internal Methods ==========
    
    def _cleanup_if_needed(self) -> None:
        """Cleanup expired entries if needed"""
        now = datetime.now()
        
        if (now - self.last_cleanup).total_seconds() < self.cleanup_interval:
            return
        
        self._cleanup_expired()
        self.last_cleanup = now
    
    def _cleanup_expired(self) -> int:
        """
        Remove expired entries
        
        Returns:
            Number of entries removed
        """
        expired_keys = [
            key for key, entry in self.cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            self._update_stats()
        
        return len(expired_keys)
    
    def _evict_oldest(self) -> None:
        """Evict oldest entry based on access patterns"""
        if not self.cache:
            return
        
        # Sort by last access time (oldest first)
        # Use created_at as fallback
        oldest_key = min(
            self.cache.keys(),
            key=lambda k: self.cache[k].created_at
        )
        
        del self.cache[oldest_key]
        self.stats.evictions += 1
    
    def _generate_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """
        Generate cache key from function name and arguments
        
        Args:
            func_name: Function name
            args: Positional arguments
            kwargs: Keyword arguments
            
        Returns:
            Cache key string
        """
        key_data = f"{func_name}:{args}:{kwargs}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"{func_name}:{key_hash}"
    
    def _update_stats(self) -> None:
        """Update cache statistics"""
        total = self.stats.cache_hits + self.stats.cache_misses
        
        self.stats.current_size = len(self.cache)
        self.stats.hit_ratio = (
            self.stats.cache_hits / total if total > 0 else 0.0
        )
        
        # Estimate memory usage
        total_memory = 0
        for entry in self.cache.values():
            try:
                total_memory += len(json.dumps(entry.value))
            except:
                total_memory += 1000  # Estimate for non-serializable
        
        self.stats.memory_usage_bytes = total_memory
    
    def get_entries(self) -> Dict[str, Dict]:
        """Get all cache entries with metadata"""
        with self.lock:
            return {
                key: {
                    "created_at": entry.created_at.isoformat(),
                    "expires_at": entry.expires_at.isoformat(),
                    "hit_count": entry.hit_count,
                    "access_count": entry.access_count,
                    "is_expired": entry.is_expired()
                }
                for key, entry in self.cache.items()
            }


# Global cache instance
_global_cache = PerformanceCache()


def demo_cache():
    """Demo cache manager functionality"""
    print("\n" + "="*70)
    print("💾 PERFORMANCE CACHE DEMO")
    print("="*70)
    
    cache = PerformanceCache(max_size=100, default_ttl=60)
    
    # Test 1: Basic set/get
    print("\n📝 Test 1: Basic Cache Operations")
    cache.set("user_profile:STU001", {"name": "Student 1", "level": "intermediate"})
    result = cache.get("user_profile:STU001")
    print(f"   ✅ Cache set/get: {result}")
    
    # Test 2: Cache decorator
    print("\n🎯 Test 2: Cache Decorator")
    call_count = [0]
    
    @cache.cache_response(ttl=60)
    def expensive_calculation(x, y):
        call_count[0] += 1
        return x + y
    
    result1 = expensive_calculation(10, 20)
    result2 = expensive_calculation(10, 20)  # Should use cache
    print(f"   ✅ First call result: {result1}")
    print(f"   ✅ Second call result: {result2} (from cache)")
    print(f"   ✅ Function called {call_count[0]} times (should be 1)")
    
    # Test 3: Multiple cache entries
    print("\n📊 Test 3: Multiple Entries")
    for i in range(5):
        cache.set(f"quiz:CH{i}", f"Quiz for Chapter {i}")
    
    quiz = cache.get("quiz:CH2")
    print(f"   ✅ Retrieved: {quiz}")
    
    # Test 4: Cache statistics
    print("\n📈 Test 4: Cache Statistics")
    stats = cache.get_stats()
    print(f"   ✅ Total Requests: {stats['total_requests']}")
    print(f"   ✅ Cache Hits: {stats['cache_hits']}")
    print(f"   ✅ Cache Misses: {stats['cache_misses']}")
    print(f"   ✅ Hit Ratio: {stats['hit_ratio']*100:.1f}%")
    print(f"   ✅ Current Size: {stats['current_size']}")
    print(f"   ✅ Memory Usage: {stats['memory_usage_mb']:.2f} MB")
    
    # Test 5: Expiration
    print("\n⏰ Test 5: Cache Expiration")
    cache.set("temp_key", "temporary_value", ttl=1)
    print(f"   ✅ Set temp key with 1s TTL")
    print(f"   ✅ Immediate get: {cache.get('temp_key')}")
    
    import time
    time.sleep(1.1)
    print(f"   ✅ After 1.1s get: {cache.get('temp_key')} (should be None)")
    
    # Test 6: Cache invalidation
    print("\n🔄 Test 6: Cache Invalidation")
    cache.set("to_delete", "some_value")
    print(f"   ✅ Set value: {cache.get('to_delete')}")
    cache.delete("to_delete")
    print(f"   ✅ After delete: {cache.get('to_delete')} (should be None)")
    
    print("\n✅ Component 10: Performance Cache - Ready!")
    print("="*70)


if __name__ == "__main__":
    demo_cache()
