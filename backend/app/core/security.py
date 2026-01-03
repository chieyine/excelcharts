"""
Security middleware and utilities.

Implements:
- Content-Security-Policy headers
- Production encryption key enforcement
"""
import os
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


# CSP Directives - configurable via environment
DEFAULT_CSP = {
    "default-src": "'self'",
    "script-src": "'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net",  # Vega needs eval
    "style-src": "'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src": "'self' https://fonts.gstatic.com",
    "img-src": "'self' data: blob:",
    "connect-src": "'self'",
    "frame-ancestors": "'none'",
    "base-uri": "'self'",
    "form-action": "'self'",
}


def build_csp_header(csp_dict: dict) -> str:
    """Build CSP header string from dictionary."""
    return "; ".join(f"{key} {value}" for key, value in csp_dict.items())


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    
    Adds:
    - Content-Security-Policy
    - X-Content-Type-Options
    - X-Frame-Options
    - X-XSS-Protection
    - Referrer-Policy
    - Permissions-Policy
    """
    
    def __init__(self, app, csp_overrides: dict = None):
        super().__init__(app)
        csp = DEFAULT_CSP.copy()
        if csp_overrides:
            csp.update(csp_overrides)
        self.csp_header = build_csp_header(csp)
    
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        # Content Security Policy
        response.headers["Content-Security-Policy"] = self.csp_header
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Clickjacking protection
        response.headers["X-Frame-Options"] = "DENY"
        
        # XSS protection (legacy, but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions policy (restrict browser features)
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), "
            "gyroscope=(), magnetometer=(), microphone=(), "
            "payment=(), usb=()"
        )
        
        return response


def validate_production_security():
    """
    Validate security configuration for production.
    
    Raises RuntimeError if critical security settings are missing.
    """
    env = os.getenv('ENVIRONMENT', 'development').lower()
    
    if env in ('production', 'prod'):
        # Check for encryption key
        encryption_key = os.getenv('SHARE_ENCRYPTION_KEY')
        if not encryption_key:
            raise RuntimeError(
                "SHARE_ENCRYPTION_KEY environment variable is required in production. "
                "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        
        # Validate key format (Fernet keys are base64-encoded 32-byte keys)
        if len(encryption_key) != 44:
            raise RuntimeError(
                "SHARE_ENCRYPTION_KEY must be a valid Fernet key. "
                "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        
        # Check allowed origins
        allowed_origins = os.getenv('ALLOWED_ORIGINS', '')
        if 'localhost' in allowed_origins:
            logger.warning(
                "ALLOWED_ORIGINS contains 'localhost' in production. "
                "Consider removing for security."
            )
        
        logger.info("Production security validation passed")
    else:
        logger.info(f"Running in {env} mode - security validation skipped")


def get_encryption_cipher():
    """
    Get Fernet cipher for encryption.
    
    Returns None in development if key not set.
    Raises in production if key not set.
    """
    from cryptography.fernet import Fernet
    
    key = os.getenv('SHARE_ENCRYPTION_KEY')
    
    if not key:
        env = os.getenv('ENVIRONMENT', 'development').lower()
        if env in ('production', 'prod'):
            raise RuntimeError("SHARE_ENCRYPTION_KEY required in production")
        logger.warning("SHARE_ENCRYPTION_KEY not set - encryption disabled")
        return None
    
    return Fernet(key.encode() if isinstance(key, str) else key)
