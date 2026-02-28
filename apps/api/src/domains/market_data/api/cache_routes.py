"""
Cache management routes - Advanced cache invalidation and monitoring endpoints
Task: FC-P2-019 - Advanced Cache Invalidation
"""
from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any, List
from pydantic import BaseModel

# Import cache management functionality
from services.cache_service import get_advanced_cache_freshness_info, force_invalidate_cache
from jobs.cache_manager import run_cache_manager_job, CacheInvalidationTracker

router = APIRouter(prefix="/api", tags=["cache"])


class CacheStatus(BaseModel):
    """Model for individual cache status"""
    key: str
    last_update: str
    age_seconds: float
    is_stale: bool
    marked_for_refresh: bool


class CacheManagerResponse(BaseModel):
    """Response model for cache management endpoints"""
    ok: bool
    data: Any
    timestamp: str


class CacheInvalidationRequest(BaseModel):
    """Request model for manual cache invalidation"""
    cache_key: str
    reason: str = "Manual invalidation"


class CacheInfoResponse(BaseModel):
    """Response model for cache information"""
    ok: bool
    data: Dict[str, CacheStatus]
    timestamp: str


@router.get(
    "/cache/status",
    response_model=CacheInfoResponse,
    summary="Get cache freshness status for all tracked caches"
)
async def get_cache_status():
    """
    Get comprehensive freshness information for all tracked caches.
    Returns:
    - Last update timestamp
    - Age in seconds
    - Whether cache is stale
    - Whether cache is marked for refresh
    """
    try:
        cache_info = get_advanced_cache_freshness_info()
        
        # Convert to CacheStatus models
        status_dict = {}
        for key, info in cache_info.items():
            status_dict[key] = CacheStatus(
                key=key,
                last_update=info.get("last_update", ""),
                age_seconds=info.get("age_seconds", -1),
                is_stale=info.get("is_stale", True),
                marked_for_refresh=info.get("marked_for_refresh", False)
            )
        
        return CacheInfoResponse(
            ok=True,
            data=status_dict,
            timestamp=str(__import__('datetime').datetime.utcnow())
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cache status: {str(e)}"
        )


@router.post(
    "/cache/invalidate",
    response_model=CacheManagerResponse,
    summary="Manually invalidate a specific cache"
)
async def manual_cache_invalidation(request: CacheInvalidationRequest):
    """
    Manually invalidate a specific cache key.
    This forces the cache to be recomputed on next access.
    """
    try:
        success = force_invalidate_cache(request.cache_key, request.reason)
        
        if success:
            return CacheManagerResponse(
                ok=True,
                data={
                    "cache_key": request.cache_key,
                    "reason": request.reason,
                    "result": "Cache marked for refresh"
                },
                timestamp=str(__import__('datetime').datetime.utcnow())
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to invalidate cache {request.cache_key}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to invalidate cache: {str(e)}"
        )


@router.get(
    "/cache/dependencies",
    response_model=CacheManagerResponse,
    summary="Get cache dependency graph"
)
async def get_cache_dependencies():
    """
    Get the cache dependency graph showing which caches depend on others.
    This helps understand the invalidation cascade pattern.
    """
    try:
        tracker = CacheInvalidationTracker()
        
        return CacheManagerResponse(
            ok=True,
            data={
                "dependencies": tracker.dependencies,
                "tracked_caches": list(tracker.state.get("last_updates", {}).keys()),
                "marked_for_refresh": list(tracker.state.get("invalidations", {}).keys())
            },
            timestamp=str(__import__('datetime').datetime.utcnow())
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cache dependencies: {str(e)}"
        )


@router.get(
    "/cache/refresh-job",
    response_model=CacheManagerResponse,
    summary="Run cache management job"
)
async def run_cache_refresh_job():
    """
    Run the cache management job to scan for stale caches and dependencies.
    """
    try:
        result = run_cache_manager_job()
        
        return CacheManagerResponse(
            ok=True,
            data=result,
            timestamp=str(__import__('datetime').datetime.utcnow())
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run cache job: {str(e)}"
        )


# For backward compatibility, also add some direct endpoints to the main router
@router.get(
    "/cache/freshness",
    response_model=CacheInfoResponse,
    summary="Alias for cache status"
)
async def get_cache_freshness():
    """
    Alias endpoint for getting cache freshness information.
    """
    try:
        cache_info = get_advanced_cache_freshness_info()
        
        # Convert to CacheStatus models
        status_dict = {}
        for key, info in cache_info.items():
            status_dict[key] = CacheStatus(
                key=key,
                last_update=info.get("last_update", ""),
                age_seconds=info.get("age_seconds", -1),
                is_stale=info.get("is_stale", True),
                marked_for_refresh=info.get("marked_for_refresh", False)
            )
        
        return CacheInfoResponse(
            ok=True,
            data=status_dict,
            timestamp=str(__import__('datetime').datetime.utcnow())
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cache freshness: {str(e)}"
        )