# =============================================================================
# IndigoGlass Nexus - FastAPI Main Application
# =============================================================================
"""
Main entry point for the IndigoGlass Nexus API service.
Provides REST endpoints for forecasting, optimization, and analytics.
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from prometheus_client import make_asgi_app

from app.api.v1 import router as api_v1_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.middleware import (
    RequestIdMiddleware,
    TimingMiddleware,
    RateLimitMiddleware,
)
from app.db.mysql import init_mysql, close_mysql
from app.db.mongodb import init_mongodb, close_mongodb
from app.db.neo4j import init_neo4j, close_neo4j
from app.db.redis import init_redis, close_redis

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan context manager.
    Initializes and cleans up database connections.
    """
    # Startup
    setup_logging()
    logger.info("starting_application", environment=settings.ENVIRONMENT)
    
    await init_mysql()
    await init_mongodb()
    await init_neo4j()
    await init_redis()
    
    logger.info("all_connections_established")
    
    yield
    
    # Shutdown
    logger.info("shutting_down_application")
    await close_redis()
    await close_neo4j()
    await close_mongodb()
    await close_mysql()
    logger.info("all_connections_closed")


def create_application() -> FastAPI:
    """Factory function to create the FastAPI application."""
    
    application = FastAPI(
        title="IndigoGlass Nexus API",
        description="Production-grade Data & AI platform for supply chain analytics",
        version="1.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )
    
    # CORS middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Custom middlewares
    application.add_middleware(RequestIdMiddleware)
    application.add_middleware(TimingMiddleware)
    application.add_middleware(RateLimitMiddleware)
    
    # Mount Prometheus metrics
    metrics_app = make_asgi_app()
    application.mount("/metrics", metrics_app)
    
    # Include API routers
    application.include_router(api_v1_router, prefix="/api/v1")
    
    return application


app = create_application()


# =============================================================================
# Health Check Endpoints
# =============================================================================

@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """Basic health check endpoint."""
    return {"status": "healthy", "service": "indigoglass-api"}


@app.get("/health/ready", tags=["Health"])
async def readiness_check() -> dict:
    """
    Readiness probe - checks all dependencies.
    Returns 503 if any dependency is unhealthy.
    """
    from app.db.mysql import check_mysql_health
    from app.db.mongodb import check_mongodb_health
    from app.db.neo4j import check_neo4j_health
    from app.db.redis import check_redis_health
    
    health_status = {
        "mysql": await check_mysql_health(),
        "mongodb": await check_mongodb_health(),
        "neo4j": await check_neo4j_health(),
        "redis": await check_redis_health(),
    }
    
    all_healthy = all(health_status.values())
    
    return {
        "status": "ready" if all_healthy else "degraded",
        "dependencies": health_status,
    }


@app.get("/health/live", tags=["Health"])
async def liveness_check() -> dict:
    """Liveness probe - basic application check."""
    return {"status": "alive"}
