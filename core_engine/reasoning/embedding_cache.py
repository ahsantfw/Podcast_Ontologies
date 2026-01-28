"""
Semantic Embedding Cache

Caches embeddings to avoid redundant API calls for identical or similar queries.
Uses LRU (Least Recently Used) eviction policy.

Features:
- Exact match caching: Identical queries return cached embeddings
- TTL (Time To Live): Embeddings expire after configurable time
- Memory-efficient: Uses LRU eviction for memory management
"""

from typing import Optional, Dict, Any, List
from collections import OrderedDict
import time
import hashlib
from core_engine.logging import get_logger

logger = get_logger(__name__)


class EmbeddingCache:
    """
    LRU cache for OpenAI embeddings.
    
    Avoids redundant API calls by caching embeddings for identical queries.
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        ttl_seconds: int = 3600,  # 1 hour default
    ):
        """
        Initialize embedding cache.
        
        Args:
            max_size: Maximum number of cached embeddings
            ttl_seconds: Time-to-live for cached entries (seconds)
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._hits = 0
        self._misses = 0
        
        logger.info(
            "embedding_cache_initialized",
            extra={"context": {"max_size": max_size, "ttl_seconds": ttl_seconds}}
        )
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key from text."""
        # Normalize text: lowercase, strip whitespace
        normalized = text.lower().strip()
        # Hash for consistent key length
        return hashlib.sha256(normalized.encode()).hexdigest()[:32]
    
    def get(self, text: str) -> Optional[List[float]]:
        """
        Get cached embedding for text.
        
        Args:
            text: Query text
            
        Returns:
            Cached embedding or None if not found/expired
        """
        key = self._get_cache_key(text)
        
        if key not in self._cache:
            self._misses += 1
            return None
        
        entry = self._cache[key]
        
        # Check TTL
        if time.time() - entry["timestamp"] > self.ttl_seconds:
            # Expired - remove and return None
            del self._cache[key]
            self._misses += 1
            return None
        
        # Move to end (most recently used)
        self._cache.move_to_end(key)
        self._hits += 1
        
        logger.debug(
            "embedding_cache_hit",
            extra={"context": {"key": key[:8], "hits": self._hits}}
        )
        
        return entry["embedding"]
    
    def set(self, text: str, embedding: List[float]) -> None:
        """
        Cache embedding for text.
        
        Args:
            text: Query text
            embedding: Embedding vector
        """
        key = self._get_cache_key(text)
        
        # Evict oldest if at capacity
        while len(self._cache) >= self.max_size:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            logger.debug(
                "embedding_cache_eviction",
                extra={"context": {"evicted_key": oldest_key[:8]}}
            )
        
        # Store with timestamp
        self._cache[key] = {
            "embedding": embedding,
            "timestamp": time.time(),
            "text_preview": text[:50],
        }
        
        # Move to end
        self._cache.move_to_end(key)
    
    def clear(self) -> None:
        """Clear all cached embeddings."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        logger.info("embedding_cache_cleared")
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0
        
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "ttl_seconds": self.ttl_seconds,
        }


# Global cache instance (singleton)
_embedding_cache: Optional[EmbeddingCache] = None


def get_embedding_cache(max_size: int = 1000, ttl_seconds: int = 3600) -> EmbeddingCache:
    """
    Get or create global embedding cache instance.
    
    Args:
        max_size: Maximum cache size
        ttl_seconds: Time-to-live for entries
        
    Returns:
        EmbeddingCache instance
    """
    global _embedding_cache
    
    if _embedding_cache is None:
        _embedding_cache = EmbeddingCache(max_size=max_size, ttl_seconds=ttl_seconds)
    
    return _embedding_cache
