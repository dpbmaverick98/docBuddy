"""
Intelligent caching system for DocsBuddy
Provides multi-level caching with TTL, size limits, and smart invalidation
"""
import hashlib
import json
import time
import threading
from typing import Any, Dict, Optional, Callable, Union
from dataclasses import dataclass
from collections import OrderedDict
import os


def _make_hashable(obj):
    """
    Convert unhashable objects to hashable representations
    """
    try:
        # First try to hash directly (fast path for basic types)
        hash(obj)
        return obj
    except TypeError:
        pass
    
    if obj is None:
        return None
    elif isinstance(obj, (str, int, float, bool)):
        return obj
    elif isinstance(obj, dict):
        # Convert dict to sorted tuple of key-value pairs
        return tuple(sorted((str(k), _make_hashable(v)) for k, v in obj.items()))
    elif isinstance(obj, (list, tuple)):
        # Convert list/tuple to tuple of hashable items
        return tuple(_make_hashable(item) for item in obj)
    elif isinstance(obj, set):
        # Convert set to sorted tuple
        return tuple(sorted(_make_hashable(item) for item in obj))
    elif hasattr(obj, '__dict__'):
        # For custom objects, use their dict representation
        return _make_hashable(obj.__dict__)
    else:
        # Fallback: convert to string representation
        return str(obj)


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    value: Any
    created_at: float
    ttl: Optional[float] = None
    hit_count: int = 0
    
    @property
    def is_expired(self) -> bool:
        """Check if entry is expired"""
        if self.ttl is None:
            return False
        return time.time() > (self.created_at + self.ttl)


class LRUCache:
    """Thread-safe LRU cache with size limits and TTL"""
    
    def __init__(self, max_size: int = 1000, default_ttl: Optional[float] = None):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.lock = threading.RLock()
        self.hits = 0
        self.misses = 0
        
    def _make_key(self, key: Union[str, tuple]) -> str:
        """Generate a consistent cache key"""
        if isinstance(key, str):
            return key
        elif isinstance(key, tuple):
            # Hash tuple keys to ensure consistency
            key_str = json.dumps(key, sort_keys=True, default=str)
            return hashlib.md5(key_str.encode()).hexdigest()
        else:
            # Convert other objects to JSON string
            key_str = json.dumps(key, sort_keys=True, default=str)
            return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, key: Union[str, tuple]) -> Optional[Any]:
        """Get value from cache"""
        cache_key = self._make_key(key)
        
        with self.lock:
            entry = self.cache.get(cache_key)
            
            if entry is None:
                self.misses += 1
                return None
            
            if entry.is_expired:
                # Remove expired entry
                del self.cache[cache_key]
                self.misses += 1
                return None
            
            # Move to end (most recently used)
            self.cache.move_to_end(cache_key)
            entry.hit_count += 1
            self.hits += 1
            return entry.value
    
    def set(self, key: Union[str, tuple], value: Any, ttl: Optional[float] = None) -> None:
        """Set value in cache"""
        cache_key = self._make_key(key)
        ttl = ttl or self.default_ttl
        
        with self.lock:
            # Remove existing entry if present
            if cache_key in self.cache:
                del self.cache[cache_key]
            
            # Add new entry
            entry = CacheEntry(
                value=value,
                created_at=time.time(),
                ttl=ttl
            )
            self.cache[cache_key] = entry
            
            # Enforce size limit
            while len(self.cache) > self.max_size:
                # Remove oldest (least recently used)
                self.cache.popitem(last=False)
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            total_requests = self.hits + self.misses
            hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': round(hit_rate, 2),
                'entries': [
                    {
                        'key': key[:50] + '...' if len(key) > 50 else key,
                        'age': time.time() - entry.created_at,
                        'hit_count': entry.hit_count,
                        'ttl': entry.ttl
                    }
                    for key, entry in list(self.cache.items())[:10]  # Show first 10
                ]
            }
    
    def cleanup_expired(self) -> int:
        """Remove expired entries, return count removed"""
        with self.lock:
            expired_keys = [
                key for key, entry in self.cache.items()
                if entry.is_expired
            ]
            
            for key in expired_keys:
                del self.cache[key]
            
            return len(expired_keys)


class CacheManager:
    """Central cache manager for different cache types"""
    
    def __init__(self):
        # Configure cache sizes and TTLs based on use case
        
        # Embedding cache - long TTL, medium size
        self.embeddings = LRUCache(
            max_size=int(os.getenv('CACHE_EMBEDDINGS_SIZE', '500')),
            default_ttl=3600 * 24  # 24 hours
        )
        
        # RAG results cache - medium TTL, small size
        self.rag_results = LRUCache(
            max_size=int(os.getenv('CACHE_RAG_SIZE', '200')),
            default_ttl=3600 * 2  # 2 hours
        )
        
        # LLM responses cache - short TTL, small size
        self.llm_responses = LRUCache(
            max_size=int(os.getenv('CACHE_LLM_SIZE', '300')),
            default_ttl=3600  # 1 hour
        )
        
        # Intent cache - medium TTL, small size
        self.intents = LRUCache(
            max_size=int(os.getenv('CACHE_INTENT_SIZE', '200')),
            default_ttl=3600 * 4  # 4 hours
        )
        
        # Document summaries cache - long TTL, medium size
        self.summaries = LRUCache(
            max_size=int(os.getenv('CACHE_SUMMARY_SIZE', '400')),
            default_ttl=3600 * 12  # 12 hours
        )
        
        # Start cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self.cleanup_thread.start()
    
    def _cleanup_worker(self):
        """Background thread to clean up expired entries"""
        while True:
            try:
                # Clean up expired entries every 5 minutes
                time.sleep(300)
                
                total_removed = 0
                for cache in [self.embeddings, self.rag_results, self.llm_responses, 
                             self.intents, self.summaries]:
                    removed = cache.cleanup_expired()
                    total_removed += removed
                
                if total_removed > 0:
                    print(f"🧹 Cache cleanup: removed {total_removed} expired entries")
                    
            except Exception as e:
                print(f"⚠️ Cache cleanup error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for all caches"""
        return {
            'embeddings': self.embeddings.get_stats(),
            'rag_results': self.rag_results.get_stats(),
            'llm_responses': self.llm_responses.get_stats(),
            'intents': self.intents.get_stats(),
            'summaries': self.summaries.get_stats()
        }
    
    def clear_all(self):
        """Clear all caches"""
        for cache in [self.embeddings, self.rag_results, self.llm_responses, 
                     self.intents, self.summaries]:
            cache.clear()


def cache_result(cache_type: str = 'llm_responses', ttl: Optional[float] = None, 
                key_func: Optional[Callable] = None):
    """
    Decorator for caching function results
    
    Args:
        cache_type: Type of cache ('embeddings', 'rag_results', 'llm_responses', 'intents', 'summaries')
        ttl: Override default TTL
        key_func: Custom function to generate cache key from arguments
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Get cache manager instance
            cache_manager = get_cache_manager()
            cache = getattr(cache_manager, cache_type)
            
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default: use function name and arguments with safe hashing
                cache_key = (func.__name__, _make_hashable(args), _make_hashable(kwargs))
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None
_cache_lock = threading.Lock()


def get_cache_manager() -> CacheManager:
    """Get or create global cache manager instance"""
    global _cache_manager
    
    if _cache_manager is None:
        with _cache_lock:
            if _cache_manager is None:
                _cache_manager = CacheManager()
    
    return _cache_manager


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics for monitoring"""
    manager = get_cache_manager()
    return manager.get_stats()


def clear_all_caches():
    """Clear all caches"""
    manager = get_cache_manager()
    manager.clear_all()


# Utility functions for specific cache types
def cache_embedding(query: str):
    """Cache embedding lookup decorator"""
    return cache_result('embeddings', ttl=3600 * 24)


def cache_rag_result(key_func: Optional[Callable] = None):
    """Cache RAG query result decorator"""
    return cache_result('rag_results', ttl=3600 * 2, key_func=key_func)


def cache_llm_response(ttl: float = 3600):
    """Cache LLM response decorator"""
    return cache_result('llm_responses', ttl=ttl)


def cache_intent():
    """Cache intent extraction decorator"""
    return cache_result('intents', ttl=3600 * 4)


def cache_summary():
    """Cache document summary decorator"""
    return cache_result('summaries', ttl=3600 * 12)