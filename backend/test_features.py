#!/usr/bin/env python3
"""
Quick test script to verify features are working.
"""
import requests
import time
import sys

BASE_URL = "http://localhost:8000/api"

def test_health():
    """Test health endpoint."""
    print("Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    print("✅ Health check passed")

def test_correlation_id():
    """Test correlation ID in response headers."""
    print("\nTesting correlation ID...")
    correlation_id = "test-correlation-123"
    response = requests.get(
        f"{BASE_URL}/health",
        headers={"X-Correlation-ID": correlation_id}
    )
    
    assert "X-Correlation-ID" in response.headers
    assert response.headers["X-Correlation-ID"] == correlation_id
    print(f"✅ Correlation ID passed: {response.headers['X-Correlation-ID']}")
    
    # Test auto-generated correlation ID
    response2 = requests.get(f"{BASE_URL}/health")
    assert "X-Correlation-ID" in response.headers
    print(f"✅ Auto-generated correlation ID: {response2.headers['X-Correlation-ID']}")

def test_response_time_header():
    """Test response time header."""
    print("\nTesting response time header...")
    response = requests.get(f"{BASE_URL}/health")
    
    assert "X-Response-Time" in response.headers
    response_time = float(response.headers["X-Response-Time"])
    assert response_time > 0
    print(f"✅ Response time header: {response.headers['X-Response-Time']}s")

def test_metrics_endpoint():
    """Test metrics endpoint."""
    print("\nTesting metrics endpoint...")
    response = requests.get(f"{BASE_URL}/metrics")
    
    assert response.status_code == 200
    data = response.json()
    assert "performance" in data
    assert "cache" in data
    print("✅ Metrics endpoint working")
    print(f"   Performance metrics: {len(data['performance'])} tracked")
    print(f"   Cache stats: {data['cache']}")

def test_file_upload():
    """Test file upload with correlation ID."""
    print("\nTesting file upload...")
    csv_content = b"date,value\n2024-01-01,100\n2024-01-02,200"
    files = {"file": ("test.csv", csv_content, "text/csv")}
    correlation_id = "upload-test-456"
    
    response = requests.post(
        f"{BASE_URL}/upload",
        files=files,
        headers={"X-Correlation-ID": correlation_id}
    )
    
    assert response.status_code == 200
    assert "X-Correlation-ID" in response.headers
    assert response.headers["X-Correlation-ID"] == correlation_id
    assert "X-Response-Time" in response.headers
    
    data = response.json()
    assert "recommended_chart" in data
    print(f"✅ File upload successful")
    print(f"   Chart type: {data['recommended_chart']['chart_type']}")
    print(f"   Correlation ID: {response.headers['X-Correlation-ID']}")
    print(f"   Response time: {response.headers['X-Response-Time']}s")

if __name__ == "__main__":
    print("=" * 60)
    print("Feature Verification Tests")
    print("=" * 60)
    
    # Wait for server to be ready
    print("\nWaiting for server to be ready...")
    for i in range(10):
        try:
            requests.get(f"{BASE_URL}/health", timeout=1)
            break
        except requests.exceptions.ConnectionError:
            time.sleep(1)
            print(f"   Attempt {i+1}/10...")
    else:
        print("❌ Server not responding. Make sure it's running on port 8000")
        sys.exit(1)
    
    try:
        test_health()
        test_correlation_id()
        test_response_time_header()
        test_metrics_endpoint()
        test_file_upload()
        
        print("\n" + "=" * 60)
        print("✅ All feature tests passed!")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

