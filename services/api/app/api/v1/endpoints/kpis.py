# =============================================================================
# IndigoGlass Nexus - KPI Endpoints
# =============================================================================
"""
Top-line KPI endpoints for executive dashboard.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Optional

import structlog
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TokenPayload, require_viewer
from app.db.mysql import get_session
from app.db.redis import cache_get, cache_set, kpi_cache_key
from app.models import (
    DimDate,
    DimProduct,
    FactSales,
    FactInventorySnapshot,
    FactShipment,
    FactForecast,
)

logger = structlog.get_logger()

router = APIRouter()


# =============================================================================
# Response Schemas
# =============================================================================

class KPIValue(BaseModel):
    """Single KPI with trend."""
    value: float
    previous_value: float | None = None
    change_percent: float | None = None
    trend: str = "neutral"  # up, down, neutral


class OverviewKPIs(BaseModel):
    """Top-line KPI overview."""
    fill_rate: KPIValue
    stockout_risk_skus: KPIValue
    co2_per_shipment_kg: KPIValue
    on_time_delivery_pct: KPIValue
    forecast_accuracy_mape: KPIValue
    total_revenue: KPIValue
    active_shipments: KPIValue
    at_risk_inventory_value: KPIValue
    as_of_date: str


class TrendDataPoint(BaseModel):
    """Data point for trend charts."""
    date: str
    value: float
    label: str | None = None


class TrendResponse(BaseModel):
    """Trend chart data response."""
    metric: str
    data: list[TrendDataPoint]
    period: str


# =============================================================================
# Helper Functions
# =============================================================================

def calculate_kpi_value(current: float, previous: float | None) -> KPIValue:
    """Calculate KPI with trend."""
    if previous is None or previous == 0:
        return KPIValue(value=current)
    
    change = ((current - previous) / previous) * 100
    trend = "up" if change > 0 else "down" if change < 0 else "neutral"
    
    return KPIValue(
        value=current,
        previous_value=previous,
        change_percent=round(change, 2),
        trend=trend,
    )


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/overview", response_model=OverviewKPIs)
async def get_kpi_overview(
    current_user: Annotated[TokenPayload, Depends(require_viewer)],
    session: Annotated[AsyncSession, Depends(get_session)],
    as_of_date: Optional[date] = Query(None, description="KPI as-of date (default: today)"),
) -> OverviewKPIs:
    """
    Get top-line KPIs for executive dashboard.
    
    Returns fill rate, stockout risk, CO2 metrics, on-time delivery,
    forecast accuracy, and other key metrics with trends vs. previous period.
    """
    target_date = as_of_date or date.today()
    target_date_str = target_date.isoformat()
    
    # Check cache
    cache_key = kpi_cache_key(target_date_str)
    cached = await cache_get(cache_key)
    if cached:
        logger.debug("kpi_cache_hit", date=target_date_str)
        return OverviewKPIs(**cached)
    
    # Get date keys
    date_key = int(target_date.strftime("%Y%m%d"))
    prev_date = target_date - timedelta(days=7)
    prev_date_key = int(prev_date.strftime("%Y%m%d"))
    
    # Calculate fill rate (units shipped / units ordered)
    fill_rate_result = await session.execute(
        select(
            func.sum(FactShipment.units).label("shipped"),
        ).where(FactShipment.date_key == date_key)
    )
    shipped = fill_rate_result.scalar() or 0
    
    # Get sales for same period
    sales_result = await session.execute(
        select(func.sum(FactSales.units_sold)).where(FactSales.date_key == date_key)
    )
    sold = sales_result.scalar() or 1
    fill_rate = min((shipped / sold) * 100, 100) if sold > 0 else 100
    
    # Previous fill rate
    prev_shipped_result = await session.execute(
        select(func.sum(FactShipment.units)).where(FactShipment.date_key == prev_date_key)
    )
    prev_shipped = prev_shipped_result.scalar() or 0
    prev_sales_result = await session.execute(
        select(func.sum(FactSales.units_sold)).where(FactSales.date_key == prev_date_key)
    )
    prev_sold = prev_sales_result.scalar() or 1
    prev_fill_rate = min((prev_shipped / prev_sold) * 100, 100) if prev_sold > 0 else None
    
    # Stockout risk SKUs (products with < 7 days of supply)
    stockout_result = await session.execute(
        select(func.count(FactInventorySnapshot.product_id.distinct())).where(
            FactInventorySnapshot.date_key == date_key,
            FactInventorySnapshot.days_of_supply < 7,
        )
    )
    stockout_skus = stockout_result.scalar() or 0
    
    prev_stockout_result = await session.execute(
        select(func.count(FactInventorySnapshot.product_id.distinct())).where(
            FactInventorySnapshot.date_key == prev_date_key,
            FactInventorySnapshot.days_of_supply < 7,
        )
    )
    prev_stockout_skus = prev_stockout_result.scalar()
    
    # CO2 per shipment
    co2_result = await session.execute(
        select(
            func.avg(FactShipment.co2_kg).label("avg_co2"),
        ).where(FactShipment.date_key == date_key)
    )
    co2_per_shipment = float(co2_result.scalar() or 0)
    
    prev_co2_result = await session.execute(
        select(func.avg(FactShipment.co2_kg)).where(FactShipment.date_key == prev_date_key)
    )
    prev_co2 = prev_co2_result.scalar()
    prev_co2 = float(prev_co2) if prev_co2 else None
    
    # On-time delivery percentage
    otd_result = await session.execute(
        select(
            func.count(case((FactShipment.delay_minutes <= 0, 1))).label("on_time"),
            func.count(FactShipment.id).label("total"),
        ).where(
            FactShipment.date_key == date_key,
            FactShipment.status == "delivered",
        )
    )
    otd_row = otd_result.one()
    otd_pct = (otd_row.on_time / otd_row.total * 100) if otd_row.total > 0 else 100
    
    # Previous OTD
    prev_otd_result = await session.execute(
        select(
            func.count(case((FactShipment.delay_minutes <= 0, 1))).label("on_time"),
            func.count(FactShipment.id).label("total"),
        ).where(
            FactShipment.date_key == prev_date_key,
            FactShipment.status == "delivered",
        )
    )
    prev_otd_row = prev_otd_result.one()
    prev_otd_pct = (prev_otd_row.on_time / prev_otd_row.total * 100) if prev_otd_row.total > 0 else None
    
    # Forecast accuracy (MAPE)
    mape_result = await session.execute(
        select(
            func.avg(
                func.abs(FactForecast.forecast_units - FactSales.units_sold) / 
                func.nullif(FactSales.units_sold, 0) * 100
            ).label("mape")
        ).select_from(FactForecast).join(
            FactSales,
            (FactForecast.date_key == FactSales.date_key) &
            (FactForecast.product_id == FactSales.product_id) &
            (FactForecast.location_id == FactSales.location_id)
        ).where(FactForecast.date_key == date_key)
    )
    mape = float(mape_result.scalar() or 0)
    
    # Total revenue
    revenue_result = await session.execute(
        select(func.sum(FactSales.revenue)).where(FactSales.date_key == date_key)
    )
    revenue = float(revenue_result.scalar() or 0)
    
    prev_revenue_result = await session.execute(
        select(func.sum(FactSales.revenue)).where(FactSales.date_key == prev_date_key)
    )
    prev_revenue = prev_revenue_result.scalar()
    prev_revenue = float(prev_revenue) if prev_revenue else None
    
    # Active shipments
    active_result = await session.execute(
        select(func.count(FactShipment.id)).where(
            FactShipment.status.in_(["pending", "in_transit"])
        )
    )
    active_shipments = active_result.scalar() or 0
    
    # At-risk inventory value
    risk_result = await session.execute(
        select(func.sum(FactInventorySnapshot.at_risk_units * 10)).where(  # Approx unit value
            FactInventorySnapshot.date_key == date_key,
            FactInventorySnapshot.at_risk_units > 0,
        )
    )
    at_risk_value = float(risk_result.scalar() or 0)
    
    kpis = OverviewKPIs(
        fill_rate=calculate_kpi_value(fill_rate, prev_fill_rate),
        stockout_risk_skus=calculate_kpi_value(stockout_skus, prev_stockout_skus),
        co2_per_shipment_kg=calculate_kpi_value(co2_per_shipment, prev_co2),
        on_time_delivery_pct=calculate_kpi_value(otd_pct, prev_otd_pct),
        forecast_accuracy_mape=KPIValue(value=mape),
        total_revenue=calculate_kpi_value(revenue, prev_revenue),
        active_shipments=KPIValue(value=active_shipments),
        at_risk_inventory_value=KPIValue(value=at_risk_value),
        as_of_date=target_date_str,
    )
    
    # Cache for 5 minutes
    await cache_set(cache_key, kpis.model_dump(), ttl_seconds=300)
    
    return kpis


@router.get("/trends/{metric}", response_model=TrendResponse)
async def get_kpi_trend(
    metric: str,
    current_user: Annotated[TokenPayload, Depends(require_viewer)],
    session: Annotated[AsyncSession, Depends(get_session)],
    days: int = Query(30, ge=7, le=365, description="Number of days of history"),
) -> TrendResponse:
    """
    Get trend data for a specific KPI metric.
    
    Supported metrics: revenue, sales, co2, shipments, inventory
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    start_key = int(start_date.strftime("%Y%m%d"))
    end_key = int(end_date.strftime("%Y%m%d"))
    
    data_points: list[TrendDataPoint] = []
    
    if metric == "revenue":
        result = await session.execute(
            select(
                DimDate.date,
                func.sum(FactSales.revenue).label("value"),
            ).join(DimDate, FactSales.date_key == DimDate.date_key)
            .where(FactSales.date_key.between(start_key, end_key))
            .group_by(DimDate.date)
            .order_by(DimDate.date)
        )
        for row in result.all():
            data_points.append(TrendDataPoint(
                date=row.date.isoformat(),
                value=float(row.value or 0),
            ))
    
    elif metric == "sales":
        result = await session.execute(
            select(
                DimDate.date,
                func.sum(FactSales.units_sold).label("value"),
            ).join(DimDate, FactSales.date_key == DimDate.date_key)
            .where(FactSales.date_key.between(start_key, end_key))
            .group_by(DimDate.date)
            .order_by(DimDate.date)
        )
        for row in result.all():
            data_points.append(TrendDataPoint(
                date=row.date.isoformat(),
                value=float(row.value or 0),
            ))
    
    elif metric == "co2":
        result = await session.execute(
            select(
                DimDate.date,
                func.sum(FactShipment.co2_kg).label("value"),
            ).join(DimDate, FactShipment.date_key == DimDate.date_key)
            .where(FactShipment.date_key.between(start_key, end_key))
            .group_by(DimDate.date)
            .order_by(DimDate.date)
        )
        for row in result.all():
            data_points.append(TrendDataPoint(
                date=row.date.isoformat(),
                value=float(row.value or 0),
            ))
    
    elif metric == "shipments":
        result = await session.execute(
            select(
                DimDate.date,
                func.count(FactShipment.id).label("value"),
            ).join(DimDate, FactShipment.date_key == DimDate.date_key)
            .where(FactShipment.date_key.between(start_key, end_key))
            .group_by(DimDate.date)
            .order_by(DimDate.date)
        )
        for row in result.all():
            data_points.append(TrendDataPoint(
                date=row.date.isoformat(),
                value=float(row.value or 0),
            ))
    
    elif metric == "inventory":
        result = await session.execute(
            select(
                DimDate.date,
                func.sum(FactInventorySnapshot.on_hand_value).label("value"),
            ).join(DimDate, FactInventorySnapshot.date_key == DimDate.date_key)
            .where(FactInventorySnapshot.date_key.between(start_key, end_key))
            .group_by(DimDate.date)
            .order_by(DimDate.date)
        )
        for row in result.all():
            data_points.append(TrendDataPoint(
                date=row.date.isoformat(),
                value=float(row.value or 0),
            ))
    
    return TrendResponse(
        metric=metric,
        data=data_points,
        period=f"{days} days",
    )
