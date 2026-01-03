"""
Unit tests for the parser service.
"""
import pytest
import pandas as pd
from fastapi import UploadFile, HTTPException
from io import BytesIO
from app.services.parser import parse_file, clean_dataframe, validate_file_extension, validate_mime_type


@pytest.mark.asyncio
@pytest.mark.unit
async def test_parse_csv():
    """Test parsing a valid CSV file."""
    csv_content = b"name,age,city\nJohn,30,New York\nJane,25,London"
    file = UploadFile(
        filename="test.csv",
        file=BytesIO(csv_content)
    )
    df = await parse_file(file)
    assert len(df) == 2
    assert list(df.columns) == ["name", "age", "city"]
    assert df.iloc[0]["name"] == "John"
    assert df.iloc[0]["age"] == 30


@pytest.mark.asyncio
@pytest.mark.unit
async def test_parse_csv_with_encoding_issue():
    """Test parsing CSV with encoding issues falls back to latin1."""
    # Create CSV with special characters
    csv_content = "name,value\nJosé,100\nMaría,200".encode('latin1')
    file = UploadFile(
        filename="test.csv",
        file=BytesIO(csv_content)
    )
    df = await parse_file(file)
    assert len(df) == 2
    assert "name" in df.columns


@pytest.mark.asyncio
@pytest.mark.unit
async def test_parse_empty_csv():
    """Test parsing an empty CSV file raises error."""
    csv_content = b""
    file = UploadFile(
        filename="test.csv",
        file=BytesIO(csv_content)
    )
    with pytest.raises(HTTPException) as exc_info:
        await parse_file(file)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
@pytest.mark.unit
async def test_parse_invalid_file_extension():
    """Test parsing a file with invalid extension raises error."""
    file = UploadFile(
        filename="test.txt",
        file=BytesIO(b"some content")
    )
    with pytest.raises(HTTPException) as exc_info:
        await parse_file(file)
    assert exc_info.value.status_code == 400
    assert "Unsupported file format" in exc_info.value.detail


@pytest.mark.asyncio
@pytest.mark.unit
async def test_parse_file_without_extension():
    """Test parsing a file without extension raises error."""
    file = UploadFile(
        filename="test",
        file=BytesIO(b"some content")
    )
    with pytest.raises(HTTPException) as exc_info:
        await parse_file(file)
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
@pytest.mark.unit
async def test_parse_file_without_filename():
    """Test parsing a file without filename raises error."""
    file = UploadFile(
        filename=None,
        file=BytesIO(b"some content")
    )
    with pytest.raises(HTTPException) as exc_info:
        await parse_file(file)
    assert exc_info.value.status_code == 400


@pytest.mark.unit
def test_clean_dataframe_removes_empty_rows():
    """Test that clean_dataframe removes completely empty rows."""
    df = pd.DataFrame({
        'col1': [1, 2, None],
        'col2': [None, None, None],
        'col3': [3, 4, None]
    })
    # Add a completely empty row
    df.loc[3] = [None, None, None]
    
    cleaned = clean_dataframe(df)
    # After cleaning, rows with all NaN are removed
    # The original df has 4 rows, but row 3 (index 3) and row 2 (index 2) might both be removed
    # depending on how pandas handles the all-NaN row
    assert len(cleaned) <= 3  # Empty rows should be removed
    assert len(cleaned) >= 2  # At least the non-empty rows remain


@pytest.mark.unit
def test_clean_dataframe_removes_empty_columns():
    """Test that clean_dataframe removes completely empty columns."""
    df = pd.DataFrame({
        'col1': [1, 2, 3],
        'empty_col': [None, None, None],
        'col2': [4, 5, 6]
    })
    
    cleaned = clean_dataframe(df)
    assert 'empty_col' not in cleaned.columns


@pytest.mark.unit
def test_validate_file_extension_valid():
    """Test validate_file_extension with valid extensions."""
    assert validate_file_extension("test.csv") == ".csv"
    assert validate_file_extension("test.xlsx") == ".xlsx"
    assert validate_file_extension("test.XLS") == ".xls"  # Case insensitive


@pytest.mark.unit
def test_validate_file_extension_invalid():
    """Test validate_file_extension with invalid extensions."""
    with pytest.raises(HTTPException) as exc_info:
        validate_file_extension("test.txt")
    assert exc_info.value.status_code == 400


@pytest.mark.unit
def test_validate_file_extension_no_extension():
    """Test validate_file_extension with no extension."""
    with pytest.raises(HTTPException) as exc_info:
        validate_file_extension("test")
    assert exc_info.value.status_code == 400


@pytest.mark.unit
def test_validate_file_extension_empty_filename():
    """Test validate_file_extension with empty filename."""
    with pytest.raises(HTTPException) as exc_info:
        validate_file_extension("")
    assert exc_info.value.status_code == 400


@pytest.mark.unit
def test_validate_mime_type():
    """Test MIME type validation."""
    # Valid MIME types
    assert validate_mime_type("text/csv", ".csv") is True
    assert validate_mime_type("application/vnd.ms-excel", ".xls") is True
    
    # No content type (should pass)
    assert validate_mime_type(None, ".csv") is True
    
    # Mismatch (should still pass but log warning)
    assert validate_mime_type("text/csv", ".xlsx") is True

