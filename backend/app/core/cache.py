"""
Simple in-memory caching layer for parsed files and profiles.
"""
import hashlib
import logging
import time
from typing import Optional, Dict, Any, TYPE_CHECKING
from dataclasses import dataclass
from threading import Lock

if TYPE_CHECKING:
    from app.core.schemas import DatasetProfile

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with expiration."""
    data: Any
    timestamp: float
    ttl: float  # Time to live in seconds


class SimpleCache:
    """Thread-safe in-memory cache with TTL."""
    
    def __init__(self, default_ttl: float = 3600):  # 1 hour default
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = Lock()
        self.default_ttl = default_ttl
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        # Create a hash of the arguments
        key_data = str(args) + str(sorted(kwargs.items()))
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            
            # Check if expired
            if time.time() - entry.timestamp > entry.ttl:
                del self._cache[key]
                logger.debug(f"Cache entry expired: {key[:16]}...")
                return None
            
            logger.debug(f"Cache hit: {key[:16]}...")
            return entry.data
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None):
        """Set value in cache with optional TTL."""
        with self._lock:
            self._cache[key] = CacheEntry(
                data=value,
                timestamp=time.time(),
                ttl=ttl or self.default_ttl
            )
            logger.debug(f"Cache set: {key[:16]}... (TTL: {ttl or self.default_ttl}s)")
    
    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            logger.info("Cache cleared")
    
    def cleanup_expired(self):
        """Remove expired entries."""
        with self._lock:
            now = time.time()
            expired_keys = [
                key for key, entry in self._cache.items()
                if now - entry.timestamp > entry.ttl
            ]
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            self.cleanup_expired()
            return {
                'size': len(self._cache),
                'default_ttl': self.default_ttl
            }


# Global cache instances
_file_cache = SimpleCache(default_ttl=1800)  # 30 minutes for parsed files
_profile_cache = SimpleCache(default_ttl=3600)  # 1 hour for profiles


def get_file_cache() -> SimpleCache:
    """Get file cache instance."""
    return _file_cache


def get_profile_cache() -> SimpleCache:
    """Get profile cache instance."""
    return _profile_cache


def generate_file_cache_key(file_content: bytes, filename: str) -> str:
    """Generate cache key for file based on content hash."""
    content_hash = hashlib.sha256(file_content).hexdigest()
    filename_hash = hashlib.sha256(filename.encode()).hexdigest()
    return f"file:{content_hash}:{filename_hash}"


def generate_profile_cache_key(profile: "DatasetProfile") -> str:
    """Generate cache key for profile."""
    # Use row count, col count, and column names as key
    key_data = f"{profile.row_count}:{profile.col_count}:{','.join(c.name for c in profile.columns)}"
    return hashlib.sha256(key_data.encode()).hexdigest()

