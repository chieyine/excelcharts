import os
import sys
import logging
from logging.config import dictConfig
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.api.routes import router
from app.api.metrics import router as metrics_router
from app.api.story import router as story_router
from app.api.share import router as share_router
from app.core.config import get_settings
from app.core.middleware import CorrelationIDMiddleware
from app.core.security import SecurityHeadersMiddleware, validate_production_security
from app.core.logging import configure_logging

# Load environment variables
load_dotenv()

# Load and validate configuration
try:
    settings = get_settings()
except Exception as e:
    # Basic logger for startup errors
    logging.basicConfig(level=logging.ERROR)
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to load configuration: {e}")
    sys.exit(1)

# Configure logging with correlation ID support
class CorrelationIdFilter(logging.Filter):
    """Filter to ensure correlation_id is present in log records."""
    def filter(self, record):
        if not hasattr(record, "correlation_id"):
            record.correlation_id = "system"
        return True

logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "correlation_id": {
            "()": CorrelationIdFilter,
        },
    },
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "filters": ["correlation_id"],
            "stream": sys.stdout,
        },
    },
    "root": {
        "level": settings.log_level,
        "handlers": ["console"],
    },
}

dictConfig(logging_config)
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Instant Charts API",
    description="Backend for Instant Charts",
    version="1.0.0"
)

# Store limiter and settings in app state for use in routes
app.state.limiter = limiter
app.state.settings = settings

# Custom rate limit exception handler with structured error response
def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded with structured error response."""
    from fastapi.responses import JSONResponse
    from app.core.errors import ErrorCodes, get_error_response
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    error_info = get_error_response(ErrorCodes.RATE_LIMIT_EXCEEDED)
    error_info['correlation_id'] = correlation_id
    return JSONResponse(
        status_code=429,
        content=error_info,
        headers={
            "Retry-After": str(exc.retry_after) if hasattr(exc, 'retry_after') else "60",
            "X-Correlation-ID": correlation_id
        }
    )

app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# Add middleware in order (last added is first executed)
# 1. Correlation ID middleware (first, to add IDs to all requests)
app.add_middleware(CorrelationIDMiddleware)

# 2. Compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 3. CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization", "X-Correlation-ID"],
    expose_headers=["X-Correlation-ID"]
)

# 4. Request timeout middleware
class TimeoutMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        import asyncio
        timeout = settings.request_timeout_seconds
        correlation_id = getattr(request.state, 'correlation_id', 'unknown')
        
        try:
            response = await asyncio.wait_for(call_next(request), timeout=timeout)
            return response
        except asyncio.TimeoutError:
            logger.error(f"Request timeout after {timeout} seconds: {request.url}", extra={"correlation_id": correlation_id})
            from fastapi.responses import JSONResponse
            from app.core.errors import ErrorCodes, get_error_response
            error_info = get_error_response(ErrorCodes.TIMEOUT)
            error_info['correlation_id'] = correlation_id
            return JSONResponse(
                status_code=504,
                content=error_info,
                headers={"X-Correlation-ID": correlation_id}
            )

app.add_middleware(TimeoutMiddleware)

# 5. Security headers middleware (CSP, X-Frame-Options, etc.)
app.add_middleware(SecurityHeadersMiddleware)

# Validate production security settings
validate_production_security()

logger.info(f"CORS allowed origins: {settings.allowed_origins_list}")

app.include_router(router, prefix="/api")
app.include_router(metrics_router, prefix="/api")
app.include_router(story_router, prefix="/api")
app.include_router(share_router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Instant Charts API is running"}

logger.info("Application started successfully")
