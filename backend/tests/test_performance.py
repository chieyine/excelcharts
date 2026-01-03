"""
Tests for performance monitoring.
"""
import pytest
import time
from app.core.performance import PerformanceMonitor, track_performance


def test_performance_monitor_record():
    """Test recording performance metrics."""
    PerformanceMonitor.clear_metrics()
    
    PerformanceMonitor.record_metric("test_metric", 1.5, {"test": "data"})
    PerformanceMonitor.record_metric("test_metric", 2.0)
    PerformanceMonitor.record_metric("test_metric", 0.5)
    
    stats = PerformanceMonitor.get_stats("test_metric")
    
    assert stats is not None
    assert stats["count"] == 3
    assert stats["min"] == 0.5
    assert stats["max"] == 2.0
    assert stats["mean"] == pytest.approx(1.333, rel=0.01)


def test_performance_decorator_sync():
    """Test performance tracking decorator on sync function."""
    PerformanceMonitor.clear_metrics()
    
    @track_performance("test_function")
    def test_func(x: int) -> int:
        time.sleep(0.01)  # Small delay to measure
        return x * 2
    
    result = test_func(5)
    
    assert result == 10
    
    stats = PerformanceMonitor.get_stats("test_function")
    assert stats is not None
    assert stats["count"] == 1
    assert stats["mean"] > 0


@pytest.mark.asyncio
async def test_performance_decorator_async():
    """Test performance tracking decorator on async function."""
    PerformanceMonitor.clear_metrics()
    
    @track_performance("test_async_function")
    async def test_async_func(x: int) -> int:
        import asyncio
        await asyncio.sleep(0.01)
        return x * 2
    
    result = await test_async_func(5)
    
    assert result == 10
    
    stats = PerformanceMonitor.get_stats("test_async_function")
    assert stats is not None
    assert stats["count"] == 1
    assert stats["mean"] > 0


def test_performance_monitor_clear():
    """Test clearing metrics."""
    PerformanceMonitor.record_metric("test", 1.0)
    assert PerformanceMonitor.get_stats("test") is not None
    
    PerformanceMonitor.clear_metrics()
    assert PerformanceMonitor.get_stats("test") is None

