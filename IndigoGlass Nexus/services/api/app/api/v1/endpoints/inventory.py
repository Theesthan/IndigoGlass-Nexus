# =============================================================================
# IndigoGlass Nexus - Inventory Endpoints
# =============================================================================
"""
Inventory risk and stock analysis endpoints.
"""

from datetime import date, timedelta
from typing import Annotated, Optional

import structlog
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TokenPayload, require_viewer
from app.db.mysql import get_session
from app.models import (
    DimDate,
    DimProduct,
    DimLocation,
    FactInventorySnapshot,
    FactSales,
)

logger = structlog.get_logger()

router = APIRouter()


# =============================================================================
# Response Schemas
# =============================================================================

class InventoryRiskItem(BaseModel):
    """Single inventory risk item."""
    sku: str
    product_name: str
    category: str
    location: str
    region: str
    on_hand_units: int
    at_risk_units: int
    days_of_supply: float
    stockout_probability: float
    risk_level: str  # low, medium, high, critical


class InventoryRiskResponse(BaseModel):
    """Inventory risk response."""
    items: list[InventoryRiskItem]
    summary: dict
    as_of_date: str


class WarehouseInventory(BaseModel):
    """Warehouse inventory summary."""
    location_id: int
    location_name: str
    region: str
    total_sku_count: int
    total_units: int
    total_value: float
    at_risk_units: int
    at_risk_value: float
    utilization_pct: float


class HeatmapCell(BaseModel):
    """Heatmap data cell."""
    x: str  # e.g., region
    y: str  # e.g., category
    value: float
    label: str


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/risk", response_model=InventoryRiskResponse)
async def get_inventory_risk(
    current_user: Annotated[TokenPayload, Depends(require_viewer)],
    session: Annotated[AsyncSession, Depends(get_session)],
    as_of_date: Optional[date] = Query(None),
    region: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    min_risk: str = Query("low", description="Minimum risk level to include"),
    limit: int = Query(50, ge=1, le=500),
) -> InventoryRiskResponse:
    """
    Get inventory at-risk items sorted by risk level.
    
    Returns products with low days of supply or high stockout probability.
    """
    target_date = as_of_date or date.today()
    date_key = int(target_date.strftime("%Y%m%d"))
    
    # Risk thresholds
    risk_thresholds = {
        "critical": (0, 3),    # 0-3 days
        "high": (3, 7),        # 3-7 days
        "medium": (7, 14),     # 7-14 days
        "low": (14, 30),       # 14-30 days
    }
    
    # Build query
    query = (
        select(
            DimProduct.sku,
            DimProduct.name,
            DimProduct.category,
            DimLocation.name.label("location_name"),
            DimLocation.region,
            FactInventorySnapshot.on_hand_units,
            FactInventorySnapshot.at_risk_units,
            FactInventorySnapshot.days_of_supply,
            FactInventorySnapshot.stockout_probability,
        )
        .join(DimProduct, FactInventorySnapshot.product_id == DimProduct.product_id)
        .join(DimLocation, FactInventorySnapshot.location_id == DimLocation.location_id)
        .where(FactInventorySnapshot.date_key == date_key)
    )
    
    if region:
        query = query.where(DimLocation.region == region)
    if category:
        query = query.where(DimProduct.category == category)
    
    # Filter by minimum risk level
    if min_risk == "critical":
        query = query.where(FactInventorySnapshot.days_of_supply <= 3)
    elif min_risk == "high":
        query = query.where(FactInventorySnapshot.days_of_supply <= 7)
    elif min_risk == "medium":
        query = query.where(FactInventorySnapshot.days_of_supply <= 14)
    
    query = query.order_by(FactInventorySnapshot.days_of_supply.asc()).limit(limit)
    
    result = await session.execute(query)
    
    items = []
    risk_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    
    for row in result.all():
        dos = float(row.days_of_supply or 0)
        
        if dos <= 3:
            risk_level = "critical"
        elif dos <= 7:
            risk_level = "high"
        elif dos <= 14:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        risk_counts[risk_level] += 1
        
        items.append(InventoryRiskItem(
            sku=row.sku,
            product_name=row.name,
            category=row.category,
            location=row.location_name,
            region=row.region,
            on_hand_units=row.on_hand_units,
            at_risk_units=row.at_risk_units,
            days_of_supply=dos,
            stockout_probability=float(row.stockout_probability or 0),
            risk_level=risk_level,
        ))
    
    return InventoryRiskResponse(
        items=items,
        summary={
            "total_items": len(items),
            "risk_distribution": risk_counts,
            "avg_days_of_supply": sum(i.days_of_supply for i in items) / len(items) if items else 0,
        },
        as_of_date=target_date.isoformat(),
    )


@router.get("/warehouses", response_model=list[WarehouseInventory])
async def get_warehouse_inventory(
    current_user: Annotated[TokenPayload, Depends(require_viewer)],
    session: Annotated[AsyncSession, Depends(get_session)],
    as_of_date: Optional[date] = Query(None),
) -> list[WarehouseInventory]:
    """
    Get inventory summary by warehouse.
    """
    target_date = as_of_date or date.today()
    date_key = int(target_date.strftime("%Y%m%d"))
    
    result = await session.execute(
        select(
            DimLocation.location_id,
            DimLocation.name,
            DimLocation.region,
            DimLocation.capacity_units,
            func.count(FactInventorySnapshot.product_id.distinct()).label("sku_count"),
            func.sum(FactInventorySnapshot.on_hand_units).label("total_units"),
            func.sum(FactInventorySnapshot.on_hand_value).label("total_value"),
            func.sum(FactInventorySnapshot.at_risk_units).label("at_risk_units"),
        )
        .join(DimLocation, FactInventorySnapshot.location_id == DimLocation.location_id)
        .where(
            FactInventorySnapshot.date_key == date_key,
            DimLocation.type.in_(["warehouse", "distribution_center"]),
        )
        .group_by(
            DimLocation.location_id,
            DimLocation.name,
            DimLocation.region,
            DimLocation.capacity_units,
        )
        .order_by(func.sum(FactInventorySnapshot.on_hand_value).desc())
    )
    
    warehouses = []
    for row in result.all():
        total_units = row.total_units or 0
        capacity = row.capacity_units or total_units or 1
        utilization = (total_units / capacity * 100) if capacity > 0 else 0
        
        warehouses.append(WarehouseInventory(
            location_id=row.location_id,
            location_name=row.name,
            region=row.region,
            total_sku_count=row.sku_count,
            total_units=total_units,
            total_value=float(row.total_value or 0),
            at_risk_units=row.at_risk_units or 0,
            at_risk_value=float(row.at_risk_units or 0) * 10,  # Approx
            utilization_pct=round(utilization, 1),
        ))
    
    return warehouses


@router.get("/heatmap", response_model=list[HeatmapCell])
async def get_risk_heatmap(
    current_user: Annotated[TokenPayload, Depends(require_viewer)],
    session: Annotated[AsyncSession, Depends(get_session)],
    x_axis: str = Query("region", description="X-axis: region or category"),
    y_axis: str = Query("category", description="Y-axis: region or category"),
    metric: str = Query("at_risk_units", description="Metric: at_risk_units or days_of_supply"),
    as_of_date: Optional[date] = Query(None),
) -> list[HeatmapCell]:
    """
    Get heatmap data for inventory risk visualization.
    """
    target_date = as_of_date or date.today()
    date_key = int(target_date.strftime("%Y%m%d"))
    
    # Determine grouping columns
    x_col = DimLocation.region if x_axis == "region" else DimProduct.category
    y_col = DimProduct.category if y_axis == "category" else DimLocation.region
    
    if metric == "at_risk_units":
        agg_col = func.sum(FactInventorySnapshot.at_risk_units)
    else:
        agg_col = func.avg(FactInventorySnapshot.days_of_supply)
    
    result = await session.execute(
        select(
            x_col.label("x"),
            y_col.label("y"),
            agg_col.label("value"),
        )
        .join(DimProduct, FactInventorySnapshot.product_id == DimProduct.product_id)
        .join(DimLocation, FactInventorySnapshot.location_id == DimLocation.location_id)
        .where(FactInventorySnapshot.date_key == date_key)
        .group_by(x_col, y_col)
    )
    
    cells = []
    for row in result.all():
        cells.append(HeatmapCell(
            x=row.x,
            y=row.y,
            value=float(row.value or 0),
            label=f"{row.value:.1f}",
        ))
    
    return cells
