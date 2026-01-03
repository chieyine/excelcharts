"""
Centralized configuration management.

All application configuration is loaded and validated here.
"""
import os
import logging
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class Settings(BaseModel):
    """Application settings with validation."""
    
    # File upload settings
    max_file_size_mb: int = Field(default=50, ge=1, le=1000, description="Maximum file size in MB")
    max_dataset_rows: int = Field(default=5000, ge=100, le=100000, description="Maximum rows in response")
    
    # Rate limiting
    rate_limit_per_minute: int = Field(default=10, ge=1, le=1000, description="Rate limit per minute per IP")
    
    # Request timeout
    request_timeout_seconds: int = Field(default=300, ge=1, le=3600, description="Request timeout in seconds")
    
    # CORS
    allowed_origins: str = Field(
        default="http://localhost:3000,http://localhost:3001",
        description="Comma-separated list of allowed CORS origins"
    )
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    
    # File validation limits
    max_file_rows: int = Field(default=1000000, ge=1000, description="Maximum rows in uploaded file")
    max_file_columns: int = Field(default=1000, ge=10, description="Maximum columns in uploaded file")
    max_cell_size_bytes: int = Field(default=100000, ge=1000, description="Maximum cell value size in bytes")
    
    # AI model configuration
    groq_model: str = Field(default="llama-3.2-1b-preview", description="Groq model to use")
    gemini_model: str = Field(default="gemini-1.5-flash", description="Gemini model to use")
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}, got '{v}'")
        return v.upper()
    
    @property
    def max_file_size_bytes(self) -> int:
        """Get max file size in bytes."""
        return self.max_file_size_mb * 1024 * 1024
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Get allowed origins as a list."""
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]
    
    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables."""
        return cls(
            max_file_size_mb=int(os.getenv("MAX_FILE_SIZE_MB", "50")),
            max_dataset_rows=int(os.getenv("MAX_DATASET_ROWS", "5000")),
            rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "10")),
            request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "300")),
            allowed_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            max_file_rows=int(os.getenv("MAX_FILE_ROWS", "1000000")),
            max_file_columns=int(os.getenv("MAX_FILE_COLUMNS", "1000")),
            max_cell_size_bytes=int(os.getenv("MAX_CELL_SIZE_BYTES", "100000")),
            groq_model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
        )


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings (singleton pattern)."""
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
        logger.info("Configuration loaded and validated successfully")
    return _settings


def reload_settings() -> Settings:
    """Reload settings (useful for testing)."""
    global _settings
    _settings = None
    return get_settings()

