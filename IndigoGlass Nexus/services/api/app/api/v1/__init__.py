# =============================================================================
# IndigoGlass Nexus - API v1 Router
# =============================================================================
"""
Main API router that aggregates all v1 endpoints.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    kpis,
    forecast,
    optimizer,
    graph,
    exports,
    admin,
    inventory,
    sustainability,
)

router = APIRouter()

# Include all endpoint routers
router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(kpis.router, prefix="/kpis", tags=["KPIs"])
router.include_router(forecast.router, prefix="/forecast", tags=["Forecast"])
router.include_router(inventory.router, prefix="/inventory", tags=["Inventory"])
router.include_router(optimizer.router, prefix="/optimizer", tags=["Optimizer"])
router.include_router(graph.router, prefix="/graph", tags=["Graph"])
router.include_router(sustainability.router, prefix="/sustainability", tags=["Sustainability"])
router.include_router(exports.router, prefix="/exports", tags=["Exports"])
router.include_router(admin.router, prefix="/admin", tags=["Admin"])
