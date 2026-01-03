"""
Input sanitization utilities for user-provided data.
"""
import re
import html
from typing import Optional


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize filename to prevent path traversal and log injection.
    
    Args:
        filename: Original filename
        max_length: Maximum length of sanitized filename
        
    Returns:
        Sanitized filename safe for logging and storage
    """
    if not filename:
        return "unknown"
    
    # Remove path components
    filename = filename.split('/')[-1].split('\\')[-1]
    
    # Remove control characters and newlines
    filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)
    
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    
    # Limit length
    if len(filename) > max_length:
        filename = filename[:max_length]
    
    return filename or "unknown"


def sanitize_string(value: str, max_length: int = 10000) -> str:
    """
    Sanitize string input to prevent injection attacks.
    
    Args:
        value: String to sanitize
        max_length: Maximum length
        
    Returns:
        Sanitized string
    """
    if not value:
        return ""
    
    # HTML escape to prevent XSS
    value = html.escape(value)
    
    # Remove control characters
    value = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', value)
    
    # Limit length
    if len(value) > max_length:
        value = value[:max_length]
    
    return value


def sanitize_for_logging(value: str, max_length: int = 500) -> str:
    """
    Sanitize value for safe logging (prevents log injection).
    
    Args:
        value: Value to sanitize
        max_length: Maximum length
        
    Returns:
        Sanitized value safe for logging
    """
    if not value:
        return ""
    
    # Remove newlines and carriage returns
    value = re.sub(r'[\r\n]', ' ', value)
    
    # Remove other control characters
    value = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', value)
    
    # Limit length
    if len(value) > max_length:
        value = value[:max_length] + "..."
    
    return value


def validate_column_name(name: str) -> bool:
    """
    Validate that a column name is safe.
    
    Args:
        name: Column name to validate
        
    Returns:
        True if safe, False otherwise
    """
    if not name or len(name) > 1000:
        return False
    
    # Check for dangerous patterns
    dangerous_patterns = [
        r'\.\.',  # Path traversal
        # Allow newlines (\n, \r) and tabs (\t) which are common in headers
        # Block other control characters: \x00-\x08 (Null, Bell, Backspace), \x0b-\x0c (VT, FF), \x0e-\x1f (Shift, Esc, etc)
        r'[\x00-\x08\x0b\x0c\x0e-\x1f]', 
        r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$',  # Reserved names (Windows)
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, name, re.IGNORECASE):
            return False
    
    return True

