# =============================================================================
# IndigoGlass Nexus - Redis Connection
# =============================================================================
"""
Redis connection for caching, rate limiting, and Celery broker.
"""

import json
from typing import Any, Optional

import structlog
from redis.asyncio import Redis, from_url

from app.core.config import settings

logger = structlog.get_logger()

# Global Redis client
_redis: Optional[Redis] = None


async def init_redis() -> None:
    """Initialize Redis connection."""
    global _redis
    
    _redis = from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        max_connections=50,
    )
    
    # Test connection
    await _redis.ping()
    
    logger.info("redis_initialized", url=settings.REDIS_URL)


async def close_redis() -> None:
    """Close Redis connection."""
    global _redis
    
    if _redis:
        await _redis.close()
        _redis = None
        logger.info("redis_closed")


async def get_redis() -> Optional[Redis]:
    """Get the Redis client."""
    return _redis


async def check_redis_health() -> bool:
    """Check if Redis is healthy."""
    try:
        if not _redis:
            return False
        await _redis.ping()
        return True
    except Exception as e:
        logger.warning("redis_health_check_failed", error=str(e))
        return False


# =============================================================================
# Cache Operations
# =============================================================================

async def cache_get(key: str) -> Optional[Any]:
    """Get a value from cache, returns None if not found."""
    if not _redis:
        return None
    
    value = await _redis.get(key)
    if value:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return None


async def cache_set(
    key: str,
    value: Any,
    ttl_seconds: int = 3600,
) -> bool:
    """Set a value in cache with TTL."""
    if not _redis:
        return False
    
    try:
        serialized = json.dumps(value) if not isinstance(value, str) else value
        await _redis.set(key, serialized, ex=ttl_seconds)
        return True
    except Exception as e:
        logger.warning("cache_set_error", key=key, error=str(e))
        return False


async def cache_delete(key: str) -> bool:
    """Delete a key from cache."""
    if not _redis:
        return False
    
    try:
        await _redis.delete(key)
        return True
    except Exception as e:
        logger.warning("cache_delete_error", key=key, error=str(e))
        return False


async def cache_delete_pattern(pattern: str) -> int:
    """Delete all keys matching a pattern."""
    if not _redis:
        return 0
    
    try:
        keys = []
        async for key in _redis.scan_iter(pattern):
            keys.append(key)
        
        if keys:
            return await _redis.delete(*keys)
        return 0
    except Exception as e:
        logger.warning("cache_delete_pattern_error", pattern=pattern, error=str(e))
        return 0


# =============================================================================
# Forecast Cache Keys
# =============================================================================

def forecast_cache_key(sku: str, region: str, date: str) -> str:
    """Generate cache key for forecast data."""
    return f"forecast:{sku}:{region}:{date}"


def model_cache_key(sku: str, region: str) -> str:
    """Generate cache key for model metadata."""
    return f"model:latest:{sku}:{region}"


def kpi_cache_key(date: str) -> str:
    """Generate cache key for KPI data."""
    return f"kpi:overview:{date}"


def route_plan_cache_key(plan_id: str) -> str:
    """Generate cache key for route plan."""
    return f"route:plan:{plan_id}"


# =============================================================================
# Distributed Lock
# =============================================================================

async def acquire_lock(
    lock_name: str,
    timeout_seconds: int = 30,
) -> bool:
    """Acquire a distributed lock."""
    if not _redis:
        return False
    
    key = f"lock:{lock_name}"
    return await _redis.set(key, "1", nx=True, ex=timeout_seconds)


async def release_lock(lock_name: str) -> bool:
    """Release a distributed lock."""
    if not _redis:
        return False
    
    key = f"lock:{lock_name}"
    await _redis.delete(key)
    return True
