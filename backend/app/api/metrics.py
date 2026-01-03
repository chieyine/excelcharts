"""
Metrics endpoint for performance monitoring.
"""
from fastapi import APIRouter
from app.core.performance import PerformanceMonitor
from app.core.cache import get_file_cache, get_profile_cache

router = APIRouter()


@router.get("/metrics")
async def get_metrics():
    """
    Get performance metrics and cache statistics.
    
    Returns performance metrics for all tracked operations
    and cache statistics.
    """
    metrics = PerformanceMonitor.get_all_metrics()
    cache_stats = {
        'file_cache': get_file_cache().get_stats(),
        'profile_cache': get_profile_cache().get_stats()
    }
    
    return {
        'performance': metrics,
        'cache': cache_stats
    }

