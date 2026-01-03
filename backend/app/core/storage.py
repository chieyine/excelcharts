"""
Storage abstraction layer for share links.

Provides pluggable storage backends:
- In-memory (development)
- Redis (production)

Configure via STORAGE_BACKEND environment variable.
"""
import os
import json
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """Abstract base class for storage backends."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get value by key. Returns None if not found or expired."""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Dict[str, Any], ttl_seconds: int) -> bool:
        """Set value with TTL. Returns True on success."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete key. Returns True if deleted."""
        pass
    
    @abstractmethod
    def cleanup_expired(self) -> int:
        """Remove expired entries. Returns count of removed entries."""
        pass


class InMemoryStorage(StorageBackend):
    """
    In-memory storage for development.
    
    NOT suitable for production with multiple workers.
    """
    
    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}
        logger.info("Using in-memory storage backend (development only)")
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        if key not in self._store:
            return None
        
        entry = self._store[key]
        expires_at = datetime.fromisoformat(entry['_expires_at'])
        
        if datetime.utcnow() > expires_at:
            del self._store[key]
            return None
        
        # Return data without internal metadata
        return {k: v for k, v in entry.items() if not k.startswith('_')}
    
    def set(self, key: str, value: Dict[str, Any], ttl_seconds: int) -> bool:
        from datetime import timedelta
        expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        self._store[key] = {
            **value,
            '_expires_at': expires_at.isoformat(),
            '_created_at': datetime.utcnow().isoformat()
        }
        return True
    
    def delete(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]
            return True
        return False
    
    def cleanup_expired(self) -> int:
        now = datetime.utcnow()
        expired = [
            key for key, entry in self._store.items()
            if datetime.fromisoformat(entry['_expires_at']) < now
        ]
        for key in expired:
            del self._store[key]
        return len(expired)
    
    def size(self) -> int:
        """Get current store size."""
        return len(self._store)


class RedisStorage(StorageBackend):
    """
    Redis storage for production.
    
    Requires redis package and REDIS_URL environment variable.
    """
    
    def __init__(self, redis_url: str):
        try:
            import redis
            self._client = redis.from_url(redis_url, decode_responses=True)
            self._client.ping()  # Test connection
            logger.info(f"Connected to Redis storage backend")
        except ImportError:
            raise RuntimeError(
                "Redis storage requires 'redis' package. "
                "Install with: pip install redis"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to connect to Redis: {e}")
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        try:
            data = self._client.get(f"share:{key}")
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    def set(self, key: str, value: Dict[str, Any], ttl_seconds: int) -> bool:
        try:
            self._client.setex(
                f"share:{key}",
                ttl_seconds,
                json.dumps(value)
            )
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        try:
            return self._client.delete(f"share:{key}") > 0
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    def cleanup_expired(self) -> int:
        # Redis handles TTL automatically
        return 0


# Storage factory
_storage_instance: Optional[StorageBackend] = None


def get_storage() -> StorageBackend:
    """
    Get the configured storage backend (singleton).
    
    Configure via environment variables:
    - STORAGE_BACKEND: "memory" (default) or "redis"
    - REDIS_URL: Required if using redis backend
    """
    global _storage_instance
    
    if _storage_instance is None:
        backend = os.getenv('STORAGE_BACKEND', 'memory').lower()
        
        if backend == 'redis':
            redis_url = os.getenv('REDIS_URL')
            if not redis_url:
                raise RuntimeError(
                    "REDIS_URL environment variable required for redis storage"
                )
            _storage_instance = RedisStorage(redis_url)
        else:
            _storage_instance = InMemoryStorage()
    
    return _storage_instance


def reset_storage():
    """Reset storage instance (for testing)."""
    global _storage_instance
    _storage_instance = None
