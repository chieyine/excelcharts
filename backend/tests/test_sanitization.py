"""
Tests for input sanitization utilities.
"""
import pytest
from app.core.sanitization import (
    sanitize_filename,
    sanitize_string,
    sanitize_for_logging,
    validate_column_name
)


def test_sanitize_filename():
    """Test filename sanitization."""
    # Normal filename
    assert sanitize_filename("test.csv") == "test.csv"
    
    # Path traversal attempt
    assert sanitize_filename("../../../etc/passwd") == "passwd"
    
    # Newlines
    assert sanitize_filename("test\nfile.csv") == "testfile.csv"
    
    # Control characters
    assert "\x00" not in sanitize_filename("test\x00file.csv")
    
    # Long filename
    long_name = "a" * 300
    assert len(sanitize_filename(long_name)) == 255
    
    # Empty filename
    assert sanitize_filename("") == "unknown"
    assert sanitize_filename(None) == "unknown"


def test_sanitize_string():
    """Test string sanitization."""
    # HTML escaping
    assert "&lt;" in sanitize_string("<script>")
    assert "&gt;" in sanitize_string(">")
    
    # Control characters removed
    assert "\x00" not in sanitize_string("test\x00string")
    
    # Length limit
    long_string = "a" * 20000
    assert len(sanitize_string(long_string)) == 10000


def test_sanitize_for_logging():
    """Test logging sanitization."""
    # Newlines removed
    assert "\n" not in sanitize_for_logging("test\nlog")
    assert "\r" not in sanitize_for_logging("test\rlog")
    
    # Control characters removed
    assert "\x00" not in sanitize_for_logging("test\x00log")
    
    # Length limit with ellipsis
    long_string = "a" * 600
    sanitized = sanitize_for_logging(long_string)
    assert len(sanitized) <= 503  # 500 + "..."
    assert sanitized.endswith("...")


def test_validate_column_name():
    """Test column name validation."""
    # Valid names
    assert validate_column_name("valid_column") is True
    assert validate_column_name("column_123") is True
    
    # Invalid names
    assert validate_column_name("") is False
    assert validate_column_name("../../../etc/passwd") is False
    assert validate_column_name("col<name>") is False
    assert validate_column_name("col:name") is False
    
    # Too long
    assert validate_column_name("a" * 300) is False
    
    # Reserved names (Windows)
    assert validate_column_name("CON") is False
    assert validate_column_name("PRN") is False

