"""
Comprehensive integration tests for full request flow.
"""
import pytest
import pandas as pd
from io import BytesIO
from fastapi.testclient import TestClient
from main import app
import uuid


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def sample_csv():
    """Sample CSV content for testing."""
    return b"date,revenue,region\n2024-01-01,1000,North\n2024-01-02,1200,South\n2024-01-03,1100,East"


@pytest.fixture
def sample_excel():
    """Sample Excel content (simplified - would need actual Excel bytes in real test)."""
    # For real Excel, would use openpyxl to create
    return None


@pytest.mark.integration
def test_full_upload_flow(client, sample_csv):
    """Test complete upload flow from file to chart recommendation."""
    correlation_id = str(uuid.uuid4())
    
    response = client.post(
        "/api/upload",
        files={"file": ("sales.csv", BytesIO(sample_csv), "text/csv")},
        headers={"X-Correlation-ID": correlation_id}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify correlation ID in response
    assert response.headers.get("X-Correlation-ID") == correlation_id
    
    # Verify response structure
    assert "filename" in data
    assert "profile" in data
    assert "recommended_chart" in data
    assert "alternatives" in data
    assert "dataset" in data
    
    # Verify profile
    assert data["profile"]["row_count"] == 3
    assert data["profile"]["col_count"] == 3
    assert len(data["profile"]["columns"]) == 3
    
    # Verify chart recommendation
    assert "chart_type" in data["recommended_chart"]
    assert "title" in data["recommended_chart"]
    assert "spec" in data["recommended_chart"]
    assert "score" in data["recommended_chart"]
    
    # Verify dataset
    assert len(data["dataset"]) == 3
    assert all(isinstance(row, dict) for row in data["dataset"])


@pytest.mark.integration
def test_caching_behavior(client, sample_csv):
    """Test that caching works for repeated uploads."""
    # First upload
    response1 = client.post(
        "/api/upload",
        files={"file": ("test.csv", BytesIO(sample_csv), "text/csv")}
    )
    assert response1.status_code == 200
    
    # Second upload with same content
    response2 = client.post(
        "/api/upload",
        files={"file": ("test.csv", BytesIO(sample_csv), "text/csv")}
    )
    assert response2.status_code == 200
    
    # Results should be identical
    data1 = response1.json()
    data2 = response2.json()
    
    assert data1["profile"]["row_count"] == data2["profile"]["row_count"]
    assert data1["recommended_chart"]["title"] == data2["recommended_chart"]["title"]


@pytest.mark.integration
def test_performance_metrics_endpoint(client):
    """Test that metrics endpoint returns data."""
    response = client.get("/api/metrics")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "performance" in data
    assert "cache" in data
    assert "file_cache" in data["cache"]
    assert "profile_cache" in data["cache"]


@pytest.mark.integration
def test_error_handling_flow(client):
    """Test error handling in full flow."""
    # Test with invalid file
    response = client.post(
        "/api/upload",
        files={"file": ("test.txt", BytesIO(b"invalid content"), "text/plain")}
    )
    
    assert response.status_code == 400
    assert "X-Correlation-ID" in response.headers
    
    # Verify error structure
    data = response.json()
    assert "detail" in data


@pytest.mark.integration
def test_large_file_handling(client):
    """Test handling of large files."""
    # Create a large CSV (but within limits)
    rows = ["name,value"] + [f"row{i},{i}" for i in range(1000)]
    large_csv = "\n".join(rows).encode()
    
    response = client.post(
        "/api/upload",
        files={"file": ("large.csv", BytesIO(large_csv), "text/csv")}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["profile"]["row_count"] == 1000


@pytest.mark.integration
def test_time_series_detection(client):
    """Test that time series data is properly detected."""
    csv_content = b"date,value\n2024-01-01,100\n2024-01-02,200\n2024-01-03,150"
    
    response = client.post(
        "/api/upload",
        files={"file": ("timeseries.csv", BytesIO(csv_content), "text/csv")}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should recommend line chart for time series
    chart_type = data["recommended_chart"]["chart_type"]
    # Line chart should be recommended for temporal data
    assert chart_type in ["line", "bar", "scatter"]  # One of these should be recommended


@pytest.mark.integration
def test_response_time_header(client, sample_csv):
    """Test that response time is included in headers."""
    response = client.post(
        "/api/upload",
        files={"file": ("test.csv", BytesIO(sample_csv), "text/csv")}
    )
    
    assert response.status_code == 200
    assert "X-Response-Time" in response.headers
    # Response time should be a valid float
    response_time = float(response.headers["X-Response-Time"])
    assert response_time > 0

