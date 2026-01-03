"""
Performance monitoring and metrics collection.
"""
import time
import logging
from typing import Dict, Optional, Any
from functools import wraps
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)

# Thread-safe metrics storage
_metrics_lock = threading.Lock()
_metrics: Dict[str, list] = defaultdict(list)


class PerformanceMonitor:
    """Monitor and track performance metrics."""
    
    @staticmethod
    def record_metric(name: str, value: float, metadata: Optional[Dict[str, Any]] = None):
        """
        Record a performance metric.
        
        Args:
            name: Metric name (e.g., 'parse_file', 'profile_dataset')
            value: Metric value (usually duration in seconds)
            metadata: Optional metadata (correlation_id, file_size, etc.)
        """
        with _metrics_lock:
            _metrics[name].append({
                'value': value,
                'timestamp': time.time(),
                'metadata': metadata or {}
            })
            
            # Keep only last 1000 entries per metric
            if len(_metrics[name]) > 1000:
                _metrics[name] = _metrics[name][-1000:]
    
    @staticmethod
    def get_stats(metric_name: str) -> Optional[Dict[str, float]]:
        """
        Get statistics for a metric.
        
        Returns:
            Dict with min, max, mean, count, or None if no data
        """
        with _metrics_lock:
            if metric_name not in _metrics or not _metrics[metric_name]:
                return None
            
            values = [m['value'] for m in _metrics[metric_name]]
            return {
                'count': len(values),
                'min': min(values),
                'max': max(values),
                'mean': sum(values) / len(values),
                'p50': sorted(values)[len(values) // 2] if values else 0,
                'p95': sorted(values)[int(len(values) * 0.95)] if values else 0,
                'p99': sorted(values)[int(len(values) * 0.99)] if values else 0,
            }
    
    @staticmethod
    def get_all_metrics() -> Dict[str, Dict[str, float]]:
        """Get statistics for all metrics."""
        with _metrics_lock:
            return {
                name: PerformanceMonitor.get_stats(name)
                for name in _metrics.keys()
            }
    
    @staticmethod
    def clear_metrics():
        """Clear all metrics (useful for testing)."""
        with _metrics_lock:
            _metrics.clear()


def track_performance(metric_name: str):
    """
    Decorator to track function execution time.
    
    Usage:
        @track_performance("parse_file")
        def parse_file(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            correlation_id = None
            
            # Try to extract correlation_id from request if present
            if args and hasattr(args[0], 'state'):
                correlation_id = getattr(args[0].state, 'correlation_id', None)
            elif 'request' in kwargs and hasattr(kwargs['request'], 'state'):
                correlation_id = getattr(kwargs['request'].state, 'correlation_id', None)
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                PerformanceMonitor.record_metric(
                    metric_name,
                    duration,
                    {'correlation_id': correlation_id, 'status': 'success'}
                )
                
                logger.debug(
                    f"{metric_name} completed in {duration:.3f}s",
                    extra={'metric': metric_name, 'duration': duration}
                )
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                PerformanceMonitor.record_metric(
                    metric_name,
                    duration,
                    {'correlation_id': correlation_id, 'status': 'error', 'error': str(e)}
                )
                logger.error(
                    f"{metric_name} failed after {duration:.3f}s: {e}",
                    extra={'metric': metric_name, 'duration': duration},
                    exc_info=True
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            correlation_id = None
            
            # Try to extract correlation_id from request if present
            if args and hasattr(args[0], 'state'):
                correlation_id = getattr(args[0].state, 'correlation_id', None)
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                PerformanceMonitor.record_metric(
                    metric_name,
                    duration,
                    {'correlation_id': correlation_id, 'status': 'success'}
                )
                
                logger.debug(
                    f"{metric_name} completed in {duration:.3f}s",
                    extra={'metric': metric_name, 'duration': duration}
                )
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                PerformanceMonitor.record_metric(
                    metric_name,
                    duration,
                    {'correlation_id': correlation_id, 'status': 'error', 'error': str(e)}
                )
                logger.error(
                    f"{metric_name} failed after {duration:.3f}s: {e}",
                    extra={'metric': metric_name, 'duration': duration},
                    exc_info=True
                )
                raise
        
        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator

