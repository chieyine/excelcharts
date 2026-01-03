"""
Custom middleware for request processing and performance monitoring.
"""
import uuid
import logging
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi import status
from fastapi.responses import JSONResponse
from app.core.performance import PerformanceMonitor

logger = logging.getLogger(__name__)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add correlation IDs to requests for tracing."""
    
    async def dispatch(self, request: Request, call_next):
        # Generate or extract correlation ID
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        
        # Add to request state for use in handlers
        request.state.correlation_id = correlation_id
        
        # Store original factory for restoration
        old_factory = logging.getLogRecordFactory()
        
        # Create new factory that adds correlation ID
        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.correlation_id = correlation_id
            return record
        
        logging.setLogRecordFactory(record_factory)
        
        # Log request start
        start_time = time.time()
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={"method": request.method, "path": request.url.path}
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Record performance metric
            PerformanceMonitor.record_metric(
                "request_duration",
                duration,
                {
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code
                }
            )
            
            # Add performance headers
            response.headers["X-Response-Time"] = f"{duration:.3f}"
            
            # Log request completion with structured data
            logger.info(
                f"Request completed: {request.method} {request.url.path} - {response.status_code} ({duration:.3f}s)",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration": duration,
                    "response_time_ms": duration * 1000
                }
            )
            
            return response
            
        except Exception as e:
            # Log request error
            duration = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url.path} - {str(e)} ({duration:.3f}s)",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                    "duration": duration
                },
                exc_info=True
            )
            
            # Restore original factory
            logging.setLogRecordFactory(old_factory)
            
            # Return error response with correlation ID
            error_response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "code": "INTERNAL_ERROR",
                    "message": "An internal error occurred",
                    "detail": "An unexpected error occurred while processing your request.",
                    "correlation_id": correlation_id
                }
            )
            error_response.headers["X-Correlation-ID"] = correlation_id
            return error_response
        
        finally:
            # Restore original factory
            logging.setLogRecordFactory(old_factory)

