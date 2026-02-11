# =============================================================================
# IndigoGlass Nexus - Forecast Endpoints
# =============================================================================
"""
Demand forecasting endpoints for predictions and batch scoring.
"""

from datetime import date, timedelta
from typing import Annotated, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TokenPayload, require_viewer, require_analyst
from app.db.mysql import get_session
from app.db.redis import cache_get, cache_set, forecast_cache_key
from app.models import (
    DimDate,
    DimProduct,
    DimLocation,
    FactForecast,
    FactSales,
    MLModel,
    MLModelAssignment,
)

logger = structlog.get_logger()

router = APIRouter()


# =============================================================================
# Response Schemas
# =============================================================================

class ForecastPoint(BaseModel):
    """Single forecast data point."""
    date: str
    forecast_units: int
    interval_low: int
    interval_high: int
    actual_units: int | None = None


class ForecastResponse(BaseModel):
    """Forecast response with model info."""
    sku: str
    region: str
    model_version: str
    model_name: str
    metrics: dict
    forecasts: list[ForecastPoint]


class ForecastAccuracy(BaseModel):
    """Forecast accuracy metrics."""
    sku: str
    region: str
    mae: float
    rmse: float
    mape: float
    bias: float
    coverage: float  # % of actuals within prediction interval


class BatchScoreRequest(BaseModel):
    """Batch scoring request."""
    horizon_days: int = 14
    sku_filter: list[str] | None = None
    region_filter: list[str] | None = None


class BatchScoreResponse(BaseModel):
    """Batch scoring response."""
    job_id: str
    status: str
    message: str


class ModelInfo(BaseModel):
    """Model information response."""
    model_name: str
    version: str
    status: str
    metrics: dict
    train_start: str
    train_end: str
    created_at: str


# =============================================================================
# Endpoints
# =============================================================================

@router.get("", response_model=ForecastResponse)
async def get_forecast(
    current_user: Annotated[TokenPayload, Depends(require_viewer)],
    session: Annotated[AsyncSession, Depends(get_session)],
    sku: str = Query(..., description="Product SKU"),
    region: str = Query(..., description="Location region"),
    start_date: Optional[date] = Query(None, description="Start date"),
    end_date: Optional[date] = Query(None, description="End date"),
    include_actuals: bool = Query(True, description="Include actual sales"),
) -> ForecastResponse:
    """
    Get demand forecasts for a specific SKU and region.
    
    Returns forecasted units with prediction intervals and optionally
    compares with actual sales for historical dates.
    """
    # Default date range
    if not end_date:
        end_date = date.today() + timedelta(days=14)
    if not start_date:
        start_date = date.today() - timedelta(days=30)
    
    # Check cache for recent forecasts
    cache_key = forecast_cache_key(sku, region, end_date.isoformat())
    cached = await cache_get(cache_key)
    if cached:
        logger.debug("forecast_cache_hit", sku=sku, region=region)
        return ForecastResponse(**cached)
    
    # Get product and location
    product_result = await session.execute(
        select(DimProduct).where(DimProduct.sku == sku)
    )
    product = product_result.scalar_one_or_none()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with SKU '{sku}' not found",
        )
    
    location_result = await session.execute(
        select(DimLocation).where(DimLocation.region == region).limit(1)
    )
    location = location_result.scalar_one_or_none()
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No locations found in region '{region}'",
        )
    
    # Get model assignment
    assignment_result = await session.execute(
        select(MLModelAssignment, MLModel)
        .join(MLModel, MLModelAssignment.model_id == MLModel.id)
        .where(
            MLModelAssignment.product_id == product.product_id,
            MLModelAssignment.location_id == location.location_id,
            MLModel.status == "prod",
        )
    )
    assignment_row = assignment_result.first()
    
    if not assignment_row:
        # Return empty forecast with message
        return ForecastResponse(
            sku=sku,
            region=region,
            model_version="none",
            model_name="No model assigned",
            metrics={},
            forecasts=[],
        )
    
    assignment, model = assignment_row
    
    # Get forecast data
    start_key = int(start_date.strftime("%Y%m%d"))
    end_key = int(end_date.strftime("%Y%m%d"))
    
    forecast_result = await session.execute(
        select(
            DimDate.date,
            FactForecast.forecast_units,
            FactForecast.prediction_interval_low,
            FactForecast.prediction_interval_high,
        )
        .join(DimDate, FactForecast.date_key == DimDate.date_key)
        .where(
            FactForecast.product_id == product.product_id,
            FactForecast.location_id == location.location_id,
            FactForecast.model_version == model.version,
            FactForecast.date_key.between(start_key, end_key),
        )
        .order_by(DimDate.date)
    )
    
    forecasts: list[ForecastPoint] = []
    forecast_dates = {}
    
    for row in forecast_result.all():
        forecast_dates[row.date] = ForecastPoint(
            date=row.date.isoformat(),
            forecast_units=row.forecast_units,
            interval_low=row.prediction_interval_low,
            interval_high=row.prediction_interval_high,
        )
    
    # Get actuals if requested
    if include_actuals:
        actuals_result = await session.execute(
            select(DimDate.date, FactSales.units_sold)
            .join(DimDate, FactSales.date_key == DimDate.date_key)
            .where(
                FactSales.product_id == product.product_id,
                FactSales.location_id == location.location_id,
                FactSales.date_key.between(start_key, end_key),
            )
        )
        
        for row in actuals_result.all():
            if row.date in forecast_dates:
                forecast_dates[row.date].actual_units = row.units_sold
    
    forecasts = list(forecast_dates.values())
    
    response = ForecastResponse(
        sku=sku,
        region=region,
        model_version=model.version,
        model_name=model.model_name,
        metrics=model.metrics_json,
        forecasts=forecasts,
    )
    
    # Cache for 1 hour
    await cache_set(cache_key, response.model_dump(), ttl_seconds=3600)
    
    return response


@router.get("/accuracy", response_model=list[ForecastAccuracy])
async def get_forecast_accuracy(
    current_user: Annotated[TokenPayload, Depends(require_viewer)],
    session: Annotated[AsyncSession, Depends(get_session)],
    days: int = Query(30, ge=7, le=90, description="Days to evaluate"),
    limit: int = Query(20, ge=1, le=100, description="Max results"),
) -> list[ForecastAccuracy]:
    """
    Get forecast accuracy metrics by SKU-region.
    
    Returns MAE, RMSE, MAPE, bias, and prediction interval coverage.
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    start_key = int(start_date.strftime("%Y%m%d"))
    end_key = int(end_date.strftime("%Y%m%d"))
    
    # This would be a complex query in production
    # Simplified version here
    accuracy_list: list[ForecastAccuracy] = []
    
    # Get products with forecasts
    products_result = await session.execute(
        select(
            DimProduct.sku,
            DimLocation.region,
            FactForecast.product_id,
            FactForecast.location_id,
        )
        .join(DimProduct, FactForecast.product_id == DimProduct.product_id)
        .join(DimLocation, FactForecast.location_id == DimLocation.location_id)
        .where(FactForecast.date_key.between(start_key, end_key))
        .group_by(DimProduct.sku, DimLocation.region, FactForecast.product_id, FactForecast.location_id)
        .limit(limit)
    )
    
    for row in products_result.all():
        # Calculate metrics for each SKU-region pair
        # In production, this would be a single aggregated query
        accuracy_list.append(ForecastAccuracy(
            sku=row.sku,
            region=row.region,
            mae=0.0,
            rmse=0.0,
            mape=0.0,
            bias=0.0,
            coverage=0.0,
        ))
    
    return accuracy_list


@router.post("/score-batch", response_model=BatchScoreResponse)
async def trigger_batch_scoring(
    request: BatchScoreRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[TokenPayload, Depends(require_analyst)],
) -> BatchScoreResponse:
    """
    Trigger batch scoring job for all or filtered SKU-region pairs.
    
    Requires Analyst or Admin role.
    """
    import uuid
    
    job_id = str(uuid.uuid4())[:8]
    
    # In production, this would queue a Celery task
    logger.info(
        "batch_scoring_triggered",
        job_id=job_id,
        user=current_user.sub,
        horizon_days=request.horizon_days,
        sku_filter=request.sku_filter,
        region_filter=request.region_filter,
    )
    
    return BatchScoreResponse(
        job_id=job_id,
        status="queued",
        message=f"Batch scoring job {job_id} queued for {request.horizon_days} day horizon",
    )


@router.get("/models", response_model=list[ModelInfo])
async def list_models(
    current_user: Annotated[TokenPayload, Depends(require_viewer)],
    session: Annotated[AsyncSession, Depends(get_session)],
    status_filter: Optional[str] = Query(None, description="Filter by status"),
) -> list[ModelInfo]:
    """
    List all registered ML models.
    """
    query = select(MLModel).order_by(MLModel.created_at.desc())
    
    if status_filter:
        query = query.where(MLModel.status == status_filter)
    
    result = await session.execute(query.limit(50))
    models = result.scalars().all()
    
    return [
        ModelInfo(
            model_name=m.model_name,
            version=m.version,
            status=m.status,
            metrics=m.metrics_json,
            train_start=m.train_start_date.isoformat(),
            train_end=m.train_end_date.isoformat(),
            created_at=m.created_at.isoformat(),
        )
        for m in models
    ]
