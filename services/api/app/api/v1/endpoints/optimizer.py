# =============================================================================
# IndigoGlass Nexus - Optimizer Endpoints
# =============================================================================
"""
Route optimization endpoints for truck+drone delivery planning.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Optional

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import TokenPayload, require_analyst
from app.db.mysql import get_session
from app.db.redis import cache_get, cache_set, route_plan_cache_key
from app.models import DimLocation, DimCarrier, FactRoutePlan

logger = structlog.get_logger()

router = APIRouter()


# =============================================================================
# Request/Response Schemas
# =============================================================================

class StopRequest(BaseModel):
    """Individual stop in the route."""
    location_id: int
    demand_units: int
    service_time_minutes: int = 15
    time_window_start: str | None = None
    time_window_end: str | None = None
    priority: int = 1
    drone_eligible: bool = True


class OptimizationRequest(BaseModel):
    """Route optimization request."""
    depot_location_id: int
    stops: list[StopRequest]
    plan_date: date
    truck_capacity_units: int = 500
    truck_cost_per_km: float = 1.5
    drone_capacity_units: int = 5
    drone_max_range_km: float = 15.0
    drone_cost_per_km: float = 0.5
    max_runtime_seconds: int = 10
    optimization_goal: str = "minimize_cost"  # minimize_cost, minimize_distance, minimize_co2


class RouteStop(BaseModel):
    """Stop in the optimized route."""
    sequence: int
    location_id: int
    location_name: str
    arrival_eta: str
    departure_eta: str
    demand_units: int
    delivered_by: str  # truck or drone
    cumulative_distance_km: float
    cumulative_cost: float


class DroneSortie(BaseModel):
    """Drone sortie details."""
    sortie_id: int
    launch_stop: int
    land_stop: int
    target_location_id: int
    distance_km: float
    flight_time_minutes: float
    units_delivered: int


class OptimizationResult(BaseModel):
    """Route optimization result."""
    plan_id: str
    status: str
    feasible: bool
    violations: list[str]
    route: list[RouteStop]
    drone_sorties: list[DroneSortie]
    summary: dict


class PlanHistoryItem(BaseModel):
    """Route plan history item."""
    plan_id: str
    date: str
    depot: str
    total_stops: int
    total_distance_km: float
    total_cost: float
    total_co2_kg: float
    feasible: bool
    created_at: str


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/plan", response_model=OptimizationResult)
async def create_route_plan(
    request: OptimizationRequest,
    current_user: Annotated[TokenPayload, Depends(require_analyst)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OptimizationResult:
    """
    Generate optimized truck+drone delivery route.
    
    Uses TSP-D heuristics to compute an efficient route that minimizes
    the selected objective (cost, distance, or CO2).
    
    Requires Analyst or Admin role.
    """
    plan_id = f"PLAN-{uuid.uuid4().hex[:8].upper()}"
    
    # Get depot location
    depot_result = await session.execute(
        select(DimLocation).where(DimLocation.location_id == request.depot_location_id)
    )
    depot = depot_result.scalar_one_or_none()
    if not depot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Depot location {request.depot_location_id} not found",
        )
    
    # Get all stop locations
    stop_ids = [s.location_id for s in request.stops]
    locations_result = await session.execute(
        select(DimLocation).where(DimLocation.location_id.in_(stop_ids))
    )
    locations = {loc.location_id: loc for loc in locations_result.scalars().all()}
    
    # Validate all stops exist
    missing = set(stop_ids) - set(locations.keys())
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Location IDs not found: {missing}",
        )
    
    # Call optimizer service
    try:
        optimizer_request = {
            "plan_id": plan_id,
            "depot": {
                "id": depot.location_id,
                "lat": float(depot.latitude),
                "lon": float(depot.longitude),
            },
            "stops": [
                {
                    "id": s.location_id,
                    "lat": float(locations[s.location_id].latitude),
                    "lon": float(locations[s.location_id].longitude),
                    "demand": s.demand_units,
                    "service_time": s.service_time_minutes,
                    "drone_eligible": s.drone_eligible,
                    "priority": s.priority,
                }
                for s in request.stops
            ],
            "truck": {
                "capacity": request.truck_capacity_units,
                "cost_per_km": request.truck_cost_per_km,
            },
            "drone": {
                "capacity": request.drone_capacity_units,
                "max_range_km": request.drone_max_range_km,
                "cost_per_km": request.drone_cost_per_km,
            },
            "max_runtime_seconds": request.max_runtime_seconds,
            "objective": request.optimization_goal,
        }
        
        async with httpx.AsyncClient(timeout=settings.OPTIMIZER_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{settings.OPTIMIZER_URL}/api/v1/optimize",
                json=optimizer_request,
            )
            response.raise_for_status()
            optimizer_result = response.json()
        
    except httpx.TimeoutException:
        logger.error("optimizer_timeout", plan_id=plan_id)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Optimizer service timed out",
        )
    except httpx.HTTPError as e:
        logger.error("optimizer_error", plan_id=plan_id, error=str(e))
        # Return a fallback simple route
        optimizer_result = _generate_fallback_route(
            plan_id, depot, locations, request.stops
        )
    
    # Build response
    route_stops = []
    for i, stop in enumerate(optimizer_result.get("route", [])):
        loc = locations.get(stop["location_id"]) or depot
        route_stops.append(RouteStop(
            sequence=i + 1,
            location_id=stop["location_id"],
            location_name=loc.name,
            arrival_eta=stop["arrival_eta"],
            departure_eta=stop["departure_eta"],
            demand_units=stop["demand"],
            delivered_by=stop["mode"],
            cumulative_distance_km=stop["cumulative_distance"],
            cumulative_cost=stop["cumulative_cost"],
        ))
    
    drone_sorties = [
        DroneSortie(
            sortie_id=s["id"],
            launch_stop=s["launch"],
            land_stop=s["land"],
            target_location_id=s["target"],
            distance_km=s["distance"],
            flight_time_minutes=s["time"],
            units_delivered=s["units"],
        )
        for s in optimizer_result.get("drone_sorties", [])
    ]
    
    summary = optimizer_result.get("summary", {
        "total_distance_km": 0,
        "truck_distance_km": 0,
        "drone_distance_km": 0,
        "total_cost": 0,
        "total_co2_kg": 0,
        "runtime_ms": 0,
    })
    
    result = OptimizationResult(
        plan_id=plan_id,
        status="completed",
        feasible=optimizer_result.get("feasible", True),
        violations=optimizer_result.get("violations", []),
        route=route_stops,
        drone_sorties=drone_sorties,
        summary=summary,
    )
    
    # Persist route plan
    date_key = int(request.plan_date.strftime("%Y%m%d"))
    route_plan = FactRoutePlan(
        plan_id=plan_id,
        date_key=date_key,
        from_location_id=depot.location_id,
        stops_json={"stops": [s.model_dump() for s in route_stops]},
        total_stops=len(route_stops),
        total_distance_km=Decimal(str(summary.get("total_distance_km", 0))),
        total_cost=Decimal(str(summary.get("total_cost", 0))),
        total_co2_kg=Decimal(str(summary.get("total_co2_kg", 0))),
        truck_distance_km=Decimal(str(summary.get("truck_distance_km", 0))),
        drone_distance_km=Decimal(str(summary.get("drone_distance_km", 0))),
        drone_sorties=len(drone_sorties),
        feasibility_flag=result.feasible,
        violations_json={"violations": result.violations} if result.violations else None,
        optimizer_runtime_ms=summary.get("runtime_ms", 0),
    )
    session.add(route_plan)
    
    # Cache result
    await cache_set(route_plan_cache_key(plan_id), result.model_dump(), ttl_seconds=3600)
    
    logger.info(
        "route_plan_created",
        plan_id=plan_id,
        stops=len(route_stops),
        feasible=result.feasible,
        distance_km=summary.get("total_distance_km"),
        user=current_user.sub,
    )
    
    return result


def _generate_fallback_route(
    plan_id: str,
    depot,
    locations: dict,
    stops: list[StopRequest],
) -> dict:
    """Generate a simple sequential fallback route when optimizer is unavailable."""
    from datetime import datetime, timedelta
    import math
    
    route = []
    current_time = datetime.now().replace(hour=8, minute=0)
    cumulative_dist = 0.0
    cumulative_cost = 0.0
    
    prev_lat, prev_lon = float(depot.latitude), float(depot.longitude)
    
    for i, stop in enumerate(stops):
        loc = locations[stop.location_id]
        lat, lon = float(loc.latitude), float(loc.longitude)
        
        # Simple distance calculation (haversine approximation)
        dlat = lat - prev_lat
        dlon = lon - prev_lon
        dist = math.sqrt(dlat**2 + dlon**2) * 111  # Rough km conversion
        
        cumulative_dist += dist
        cumulative_cost += dist * 1.5
        
        travel_time = int(dist / 40 * 60)  # 40 km/h average
        arrival = current_time + timedelta(minutes=travel_time)
        departure = arrival + timedelta(minutes=stop.service_time_minutes)
        
        route.append({
            "location_id": stop.location_id,
            "arrival_eta": arrival.isoformat(),
            "departure_eta": departure.isoformat(),
            "demand": stop.demand_units,
            "mode": "truck",
            "cumulative_distance": round(cumulative_dist, 2),
            "cumulative_cost": round(cumulative_cost, 2),
        })
        
        current_time = departure
        prev_lat, prev_lon = lat, lon
    
    return {
        "plan_id": plan_id,
        "feasible": True,
        "violations": [],
        "route": route,
        "drone_sorties": [],
        "summary": {
            "total_distance_km": round(cumulative_dist, 2),
            "truck_distance_km": round(cumulative_dist, 2),
            "drone_distance_km": 0,
            "total_cost": round(cumulative_cost, 2),
            "total_co2_kg": round(cumulative_dist * 0.21, 4),  # ~0.21 kg CO2/km for truck
            "runtime_ms": 50,
        },
    }


@router.get("/plan/{plan_id}", response_model=OptimizationResult)
async def get_route_plan(
    plan_id: str,
    current_user: Annotated[TokenPayload, Depends(require_analyst)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> OptimizationResult:
    """
    Get a previously generated route plan by ID.
    """
    # Check cache
    cached = await cache_get(route_plan_cache_key(plan_id))
    if cached:
        return OptimizationResult(**cached)
    
    # Query database
    result = await session.execute(
        select(FactRoutePlan).where(FactRoutePlan.plan_id == plan_id)
    )
    plan = result.scalar_one_or_none()
    
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Route plan {plan_id} not found",
        )
    
    # Reconstruct response from stored data
    stops_data = plan.stops_json.get("stops", [])
    
    return OptimizationResult(
        plan_id=plan.plan_id,
        status="retrieved",
        feasible=plan.feasibility_flag,
        violations=plan.violations_json.get("violations", []) if plan.violations_json else [],
        route=[RouteStop(**s) for s in stops_data],
        drone_sorties=[],
        summary={
            "total_distance_km": float(plan.total_distance_km),
            "truck_distance_km": float(plan.truck_distance_km),
            "drone_distance_km": float(plan.drone_distance_km),
            "total_cost": float(plan.total_cost),
            "total_co2_kg": float(plan.total_co2_kg),
            "runtime_ms": plan.optimizer_runtime_ms,
        },
    )


@router.get("/history", response_model=list[PlanHistoryItem])
async def get_plan_history(
    current_user: Annotated[TokenPayload, Depends(require_analyst)],
    session: Annotated[AsyncSession, Depends(get_session)],
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(50, ge=1, le=200),
) -> list[PlanHistoryItem]:
    """
    Get route plan history.
    """
    result = await session.execute(
        select(FactRoutePlan, DimLocation)
        .join(DimLocation, FactRoutePlan.from_location_id == DimLocation.location_id)
        .order_by(FactRoutePlan.created_at.desc())
        .limit(limit)
    )
    
    items = []
    for plan, location in result.all():
        items.append(PlanHistoryItem(
            plan_id=plan.plan_id,
            date=str(plan.date_key),
            depot=location.name,
            total_stops=plan.total_stops,
            total_distance_km=float(plan.total_distance_km),
            total_cost=float(plan.total_cost),
            total_co2_kg=float(plan.total_co2_kg),
            feasible=plan.feasibility_flag,
            created_at=plan.created_at.isoformat(),
        ))
    
    return items
