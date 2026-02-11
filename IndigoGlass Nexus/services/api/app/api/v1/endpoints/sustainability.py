# =============================================================================
# IndigoGlass Nexus - Sustainability Endpoints
# =============================================================================
"""
Sustainability and ESG KPI endpoints for emissions tracking.
"""

from datetime import date, timedelta
from typing import Annotated, Optional

import structlog
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TokenPayload, require_viewer
from app.db.mysql import get_session
from app.models import (
    DimDate,
    DimLocation,
    DimCarrier,
    FactShipment,
)

logger = structlog.get_logger()

router = APIRouter()


# =============================================================================
# Response Schemas
# =============================================================================

class EmissionsKPIs(BaseModel):
    """Top-line emissions KPIs."""
    total_co2_kg: float
    co2_per_shipment_kg: float
    co2_per_unit_kg: float
    co2_per_km_kg: float
    total_shipments: int
    total_distance_km: float
    period: str


class EmissionsByMode(BaseModel):
    """Emissions breakdown by transport mode."""
    mode: str
    total_co2_kg: float
    percentage: float
    shipments: int
    distance_km: float


class EmissionsByRegion(BaseModel):
    """Emissions by region."""
    region: str
    total_co2_kg: float
    shipments: int
    co2_per_shipment_kg: float


class EmissionsHotspot(BaseModel):
    """Emissions hotspot (high emission routes)."""
    from_location: str
    to_location: str
    total_co2_kg: float
    shipments: int
    avg_co2_per_shipment: float
    distance_km: float


class EmissionsTrendPoint(BaseModel):
    """Emissions trend data point."""
    date: str
    co2_kg: float
    shipments: int


class ScorecardItem(BaseModel):
    """Sustainability scorecard item."""
    metric: str
    current_value: float
    target_value: float
    unit: str
    status: str  # on_track, at_risk, off_track
    trend: str  # improving, stable, worsening


class SustainabilityScorecard(BaseModel):
    """Weekly sustainability scorecard."""
    week_start: str
    week_end: str
    items: list[ScorecardItem]
    overall_score: float


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/kpis", response_model=EmissionsKPIs)
async def get_emissions_kpis(
    current_user: Annotated[TokenPayload, Depends(require_viewer)],
    session: Annotated[AsyncSession, Depends(get_session)],
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
) -> EmissionsKPIs:
    """
    Get top-line emissions KPIs for the selected period.
    """
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    start_key = int(start_date.strftime("%Y%m%d"))
    end_key = int(end_date.strftime("%Y%m%d"))
    
    result = await session.execute(
        select(
            func.sum(FactShipment.co2_kg).label("total_co2"),
            func.count(FactShipment.id).label("shipments"),
            func.sum(FactShipment.units).label("total_units"),
            func.sum(FactShipment.distance_km).label("total_distance"),
        )
        .where(FactShipment.date_key.between(start_key, end_key))
    )
    
    row = result.one()
    total_co2 = float(row.total_co2 or 0)
    shipments = row.shipments or 1
    total_units = row.total_units or 1
    total_distance = float(row.total_distance or 1)
    
    return EmissionsKPIs(
        total_co2_kg=round(total_co2, 2),
        co2_per_shipment_kg=round(total_co2 / shipments, 4),
        co2_per_unit_kg=round(total_co2 / total_units, 6),
        co2_per_km_kg=round(total_co2 / total_distance, 6),
        total_shipments=shipments,
        total_distance_km=round(total_distance, 2),
        period=f"{start_date.isoformat()} to {end_date.isoformat()}",
    )


@router.get("/by-mode", response_model=list[EmissionsByMode])
async def get_emissions_by_mode(
    current_user: Annotated[TokenPayload, Depends(require_viewer)],
    session: Annotated[AsyncSession, Depends(get_session)],
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
) -> list[EmissionsByMode]:
    """
    Get emissions breakdown by transport mode.
    """
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    start_key = int(start_date.strftime("%Y%m%d"))
    end_key = int(end_date.strftime("%Y%m%d"))
    
    result = await session.execute(
        select(
            DimCarrier.mode,
            func.sum(FactShipment.co2_kg).label("total_co2"),
            func.count(FactShipment.id).label("shipments"),
            func.sum(FactShipment.distance_km).label("distance"),
        )
        .join(DimCarrier, FactShipment.carrier_id == DimCarrier.carrier_id)
        .where(FactShipment.date_key.between(start_key, end_key))
        .group_by(DimCarrier.mode)
        .order_by(func.sum(FactShipment.co2_kg).desc())
    )
    
    modes = []
    total_co2 = 0.0
    rows = result.all()
    
    for row in rows:
        total_co2 += float(row.total_co2 or 0)
    
    for row in rows:
        co2 = float(row.total_co2 or 0)
        modes.append(EmissionsByMode(
            mode=row.mode,
            total_co2_kg=round(co2, 2),
            percentage=round(co2 / total_co2 * 100, 1) if total_co2 > 0 else 0,
            shipments=row.shipments,
            distance_km=float(row.distance or 0),
        ))
    
    return modes


@router.get("/by-region", response_model=list[EmissionsByRegion])
async def get_emissions_by_region(
    current_user: Annotated[TokenPayload, Depends(require_viewer)],
    session: Annotated[AsyncSession, Depends(get_session)],
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
) -> list[EmissionsByRegion]:
    """
    Get emissions by destination region.
    """
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    start_key = int(start_date.strftime("%Y%m%d"))
    end_key = int(end_date.strftime("%Y%m%d"))
    
    result = await session.execute(
        select(
            DimLocation.region,
            func.sum(FactShipment.co2_kg).label("total_co2"),
            func.count(FactShipment.id).label("shipments"),
        )
        .join(DimLocation, FactShipment.to_location_id == DimLocation.location_id)
        .where(FactShipment.date_key.between(start_key, end_key))
        .group_by(DimLocation.region)
        .order_by(func.sum(FactShipment.co2_kg).desc())
    )
    
    regions = []
    for row in result.all():
        co2 = float(row.total_co2 or 0)
        shipments = row.shipments or 1
        regions.append(EmissionsByRegion(
            region=row.region,
            total_co2_kg=round(co2, 2),
            shipments=shipments,
            co2_per_shipment_kg=round(co2 / shipments, 4),
        ))
    
    return regions


@router.get("/hotspots", response_model=list[EmissionsHotspot])
async def get_emissions_hotspots(
    current_user: Annotated[TokenPayload, Depends(require_viewer)],
    session: Annotated[AsyncSession, Depends(get_session)],
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    limit: int = Query(10, ge=1, le=50),
) -> list[EmissionsHotspot]:
    """
    Get top emission hotspots (highest emission routes).
    """
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    start_key = int(start_date.strftime("%Y%m%d"))
    end_key = int(end_date.strftime("%Y%m%d"))
    
    from_loc = DimLocation.__table__.alias("from_loc")
    to_loc = DimLocation.__table__.alias("to_loc")
    
    result = await session.execute(
        select(
            from_loc.c.name.label("from_name"),
            to_loc.c.name.label("to_name"),
            func.sum(FactShipment.co2_kg).label("total_co2"),
            func.count(FactShipment.id).label("shipments"),
            func.avg(FactShipment.distance_km).label("avg_distance"),
        )
        .select_from(FactShipment)
        .join(from_loc, FactShipment.from_location_id == from_loc.c.location_id)
        .join(to_loc, FactShipment.to_location_id == to_loc.c.location_id)
        .where(FactShipment.date_key.between(start_key, end_key))
        .group_by(from_loc.c.name, to_loc.c.name)
        .order_by(func.sum(FactShipment.co2_kg).desc())
        .limit(limit)
    )
    
    hotspots = []
    for row in result.all():
        co2 = float(row.total_co2 or 0)
        shipments = row.shipments or 1
        hotspots.append(EmissionsHotspot(
            from_location=row.from_name,
            to_location=row.to_name,
            total_co2_kg=round(co2, 2),
            shipments=shipments,
            avg_co2_per_shipment=round(co2 / shipments, 4),
            distance_km=float(row.avg_distance or 0),
        ))
    
    return hotspots


@router.get("/trend", response_model=list[EmissionsTrendPoint])
async def get_emissions_trend(
    current_user: Annotated[TokenPayload, Depends(require_viewer)],
    session: Annotated[AsyncSession, Depends(get_session)],
    days: int = Query(30, ge=7, le=365),
) -> list[EmissionsTrendPoint]:
    """
    Get daily emissions trend.
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    start_key = int(start_date.strftime("%Y%m%d"))
    end_key = int(end_date.strftime("%Y%m%d"))
    
    result = await session.execute(
        select(
            DimDate.date,
            func.sum(FactShipment.co2_kg).label("co2"),
            func.count(FactShipment.id).label("shipments"),
        )
        .join(DimDate, FactShipment.date_key == DimDate.date_key)
        .where(FactShipment.date_key.between(start_key, end_key))
        .group_by(DimDate.date)
        .order_by(DimDate.date)
    )
    
    return [
        EmissionsTrendPoint(
            date=row.date.isoformat(),
            co2_kg=float(row.co2 or 0),
            shipments=row.shipments,
        )
        for row in result.all()
    ]


@router.get("/scorecard", response_model=SustainabilityScorecard)
async def get_sustainability_scorecard(
    current_user: Annotated[TokenPayload, Depends(require_viewer)],
    session: Annotated[AsyncSession, Depends(get_session)],
    week_offset: int = Query(0, ge=0, le=52, description="Weeks ago (0 = current week)"),
) -> SustainabilityScorecard:
    """
    Get weekly sustainability scorecard with targets and status.
    """
    today = date.today()
    week_end = today - timedelta(days=today.weekday() + 7 * week_offset)
    week_start = week_end - timedelta(days=6)
    
    start_key = int(week_start.strftime("%Y%m%d"))
    end_key = int(week_end.strftime("%Y%m%d"))
    
    # Get metrics
    result = await session.execute(
        select(
            func.sum(FactShipment.co2_kg).label("total_co2"),
            func.count(FactShipment.id).label("shipments"),
            func.sum(FactShipment.units).label("units"),
            func.sum(FactShipment.distance_km).label("distance"),
        )
        .where(FactShipment.date_key.between(start_key, end_key))
    )
    
    row = result.one()
    total_co2 = float(row.total_co2 or 0)
    shipments = row.shipments or 1
    units = row.units or 1
    distance = float(row.distance or 1)
    
    # Define targets (these would come from config in production)
    targets = {
        "co2_per_shipment": 2.5,  # kg
        "co2_per_unit": 0.1,      # kg
        "co2_per_km": 0.2,        # kg
    }
    
    items = [
        ScorecardItem(
            metric="CO2 per Shipment",
            current_value=round(total_co2 / shipments, 4),
            target_value=targets["co2_per_shipment"],
            unit="kg",
            status="on_track" if total_co2 / shipments <= targets["co2_per_shipment"] else "at_risk",
            trend="stable",
        ),
        ScorecardItem(
            metric="CO2 per Unit",
            current_value=round(total_co2 / units, 6),
            target_value=targets["co2_per_unit"],
            unit="kg",
            status="on_track" if total_co2 / units <= targets["co2_per_unit"] else "at_risk",
            trend="stable",
        ),
        ScorecardItem(
            metric="CO2 per KM",
            current_value=round(total_co2 / distance, 6),
            target_value=targets["co2_per_km"],
            unit="kg",
            status="on_track" if total_co2 / distance <= targets["co2_per_km"] else "at_risk",
            trend="stable",
        ),
        ScorecardItem(
            metric="Total Emissions",
            current_value=round(total_co2, 2),
            target_value=total_co2 * 0.9,  # 10% reduction target
            unit="kg CO2",
            status="on_track",
            trend="stable",
        ),
    ]
    
    # Calculate overall score (% of items on track)
    on_track = sum(1 for i in items if i.status == "on_track")
    overall_score = on_track / len(items) * 100
    
    return SustainabilityScorecard(
        week_start=week_start.isoformat(),
        week_end=week_end.isoformat(),
        items=items,
        overall_score=overall_score,
    )
