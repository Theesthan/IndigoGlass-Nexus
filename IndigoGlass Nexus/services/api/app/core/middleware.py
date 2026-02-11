# =============================================================================
# IndigoGlass Nexus - Custom Middlewares
# =============================================================================
"""
Request ID, timing, and rate limiting middlewares.
"""

import time
import uuid
from typing import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram

from app.core.config import settings

logger = structlog.get_logger()

# Prometheus metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to each request for tracing."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        # Add to structlog context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        
        # Store in request state
        request.state.request_id = request_id
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        return response


class TimingMiddleware(BaseHTTPMiddleware):
    """Track request timing and log structured request info."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()
        
        response = await call_next(request)
        
        duration = time.perf_counter() - start_time
        duration_ms = round(duration * 1000, 2)
        
        # Update Prometheus metrics
        endpoint = request.url.path
        method = request.method
        status = response.status_code
        
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)
        
        # Add timing header
        response.headers["X-Response-Time"] = f"{duration_ms}ms"
        
        # Log request (skip health checks)
        if not endpoint.startswith("/health"):
            logger.info(
                "http_request",
                method=method,
                path=endpoint,
                status=status,
                latency_ms=duration_ms,
                user_agent=request.headers.get("User-Agent", "unknown"),
            )
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple rate limiting using Redis.
    Rate limits are tracked per IP address.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks
        if request.url.path.startswith("/health"):
            return await call_next(request)
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        
        try:
            from app.db.redis import get_redis
            
            redis = await get_redis()
            if redis:
                key = f"ratelimit:{client_ip}"
                current = await redis.incr(key)
                
                if current == 1:
                    await redis.expire(key, 60)  # 1 minute window
                
                if current > settings.RATE_LIMIT_PER_MINUTE:
                    logger.warning(
                        "rate_limit_exceeded",
                        client_ip=client_ip,
                        requests=current,
                    )
                    return Response(
                        content='{"error": "Rate limit exceeded"}',
                        status_code=429,
                        media_type="application/json",
                        headers={"Retry-After": "60"},
                    )
        except Exception as e:
            # Log but don't block on rate limit errors
            logger.warning("rate_limit_error", error=str(e))
        
        return await call_next(request)
