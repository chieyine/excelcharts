"""
Tests for caching layer.
"""
import pytest
import time
from app.core.cache import SimpleCache, get_file_cache, get_profile_cache, generate_file_cache_key


def test_simple_cache_set_get():
    """Test basic cache set and get operations."""
    cache = SimpleCache(default_ttl=1.0)
    
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"
    
    cache.set("key2", "value2", ttl=0.1)
    assert cache.get("key2") == "value2"
    
    # Wait for expiration
    time.sleep(0.2)
    assert cache.get("key2") is None


def test_simple_cache_expiration():
    """Test cache entry expiration."""
    cache = SimpleCache(default_ttl=0.1)
    
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"
    
    time.sleep(0.15)
    assert cache.get("key1") is None


def test_simple_cache_cleanup():
    """Test cache cleanup of expired entries."""
    cache = SimpleCache(default_ttl=0.1)
    
    cache.set("key1", "value1")
    cache.set("key2", "value2", ttl=1.0)
    
    time.sleep(0.15)
    cache.cleanup_expired()
    
    assert cache.get("key1") is None
    assert cache.get("key2") == "value2"


def test_simple_cache_stats():
    """Test cache statistics."""
    cache = SimpleCache(default_ttl=1.0)
    
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    
    stats = cache.get_stats()
    assert stats["size"] == 2
    assert stats["default_ttl"] == 1.0


def test_generate_file_cache_key():
    """Test file cache key generation."""
    content1 = b"test content"
    content2 = b"test content"
    content3 = b"different content"
    
    key1 = generate_file_cache_key(content1, "file.csv")
    key2 = generate_file_cache_key(content2, "file.csv")
    key3 = generate_file_cache_key(content3, "file.csv")
    
    # Same content should generate same key
    assert key1 == key2
    
    # Different content should generate different key
    assert key1 != key3


def test_cache_instances():
    """Test that cache instances are singletons."""
    cache1 = get_file_cache()
    cache2 = get_file_cache()
    
    assert cache1 is cache2
    
    profile_cache1 = get_profile_cache()
    profile_cache2 = get_profile_cache()
    
    assert profile_cache1 is profile_cache2
    assert profile_cache1 is not cache1

