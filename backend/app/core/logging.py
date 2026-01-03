"""
Structured logging configuration.

Provides JSON logging for production and readable text format for development.
"""
import os
import sys
import logging
import json
from datetime import datetime
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """
    Structured JSON log formatter for production.
    
    Outputs logs in JSON format with:
    - timestamp
    - level
    - message
    - module
    - extra fields
    """
    
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add correlation_id if present
        if hasattr(record, 'correlation_id'):
            log_data['correlation_id'] = record.correlation_id
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ('name', 'msg', 'args', 'created', 'filename', 
                          'funcName', 'levelname', 'levelno', 'lineno',
                          'module', 'msecs', 'pathname', 'process',
                          'processName', 'relativeCreated', 'stack_info',
                          'thread', 'threadName', 'exc_info', 'exc_text',
                          'message', 'correlation_id'):
                if not key.startswith('_'):
                    log_data[key] = value
        
        return json.dumps(log_data)


class TextFormatter(logging.Formatter):
    """Readable text formatter for development."""
    
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, 'correlation_id'):
            record.correlation_id = 'system'
        return super().format(record)


def configure_logging() -> None:
    """
    Configure application logging based on environment.
    
    Uses LOG_FORMAT env var:
    - 'json': Structured JSON logging (recommended for production)
    - 'text': Human-readable format (default for development)
    """
    log_format = os.getenv('LOG_FORMAT', 'text').lower()
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    
    # Set formatter based on environment
    if log_format == 'json':
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(TextFormatter())
    
    root_logger.addHandler(handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    
    if log_format == 'json':
        root_logger.info("Structured JSON logging enabled")
