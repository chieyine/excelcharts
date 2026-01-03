"""
Tests for centralized configuration.
"""
import pytest
import os
from app.core.config import Settings, get_settings, reload_settings


def test_settings_defaults():
    """Test that settings have sensible defaults."""
    settings = Settings.from_env()
    
    assert settings.max_file_size_mb == 50
    assert settings.max_dataset_rows == 5000
    assert settings.rate_limit_per_minute == 10
    assert settings.request_timeout_seconds == 300
    assert settings.log_level == "INFO"


def test_settings_from_env():
    """Test loading settings from environment variables."""
    # Save original values
    original_max_file = os.environ.get("MAX_FILE_SIZE_MB")
    original_rate = os.environ.get("RATE_LIMIT_PER_MINUTE")
    
    try:
        os.environ["MAX_FILE_SIZE_MB"] = "100"
        os.environ["RATE_LIMIT_PER_MINUTE"] = "20"
        
        # Reload to pick up new env vars
        reload_settings()
        settings = get_settings()
        
        assert settings.max_file_size_mb == 100
        assert settings.rate_limit_per_minute == 20
    finally:
        # Cleanup - restore original or remove
        if original_max_file:
            os.environ["MAX_FILE_SIZE_MB"] = original_max_file
        else:
            os.environ.pop("MAX_FILE_SIZE_MB", None)
            
        if original_rate:
            os.environ["RATE_LIMIT_PER_MINUTE"] = original_rate
        else:
            os.environ.pop("RATE_LIMIT_PER_MINUTE", None)
            
        reload_settings()


def test_settings_validation():
    """Test that settings validate input ranges."""
    with pytest.raises(ValueError):
        Settings(max_file_size_mb=0)  # Below minimum
    
    with pytest.raises(ValueError):
        Settings(max_file_size_mb=2000)  # Above maximum
    
    with pytest.raises(ValueError):
        Settings(log_level="INVALID")  # Invalid log level


def test_settings_properties():
    """Test computed properties."""
    settings = Settings(max_file_size_mb=50)
    
    assert settings.max_file_size_bytes == 50 * 1024 * 1024
    assert isinstance(settings.allowed_origins_list, list)
    assert len(settings.allowed_origins_list) > 0


def test_settings_singleton():
    """Test that get_settings returns singleton."""
    settings1 = get_settings()
    settings2 = get_settings()
    
    assert settings1 is settings2

