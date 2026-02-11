# =============================================================================
# IndigoGlass Nexus - Export Endpoints
# =============================================================================
"""
Report generation and data export endpoints.
"""

import csv
import io
import json
import uuid
from datetime import date, datetime, timedelta
from typing import Annotated, Optional

import structlog
from fastapi import APIRouter, Depends, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TokenPayload, require_analyst, require_viewer
from app.db.mysql import get_session
from app.models import (
    DimDate,
    DimProduct,
    DimLocation,
    FactSales,
    FactForecast,
    FactShipment,
    FactInventorySnapshot,
)

logger = structlog.get_logger()

router = APIRouter()


# =============================================================================
# Response Schemas
# =============================================================================

class ExportRequest(BaseModel):
    """Export request parameters."""
    export_type: str  # sales, forecast, inventory, shipments, sustainability
    start_date: date
    end_date: date
    format: str = "csv"  # csv, json
    filters: dict = {}


class ExportJobResponse(BaseModel):
    """Export job response."""
    job_id: str
    status: str
    download_url: str | None = None
    message: str


class ReportRequest(BaseModel):
    """Executive report request."""
    report_type: str  # weekly_summary, sustainability_scorecard, forecast_accuracy
    start_date: date
    end_date: date
    format: str = "json"  # json, pdf (pdf would need additional library)


class ReportSection(BaseModel):
    """Report section."""
    title: str
    content: dict


class ExecutiveReport(BaseModel):
    """Executive report response."""
    report_id: str
    title: str
    generated_at: str
    period: str
    sections: list[ReportSection]


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/sales")
async def export_sales(
    current_user: Annotated[TokenPayload, Depends(require_viewer)],
    session: Annotated[AsyncSession, Depends(get_session)],
    start_date: date = Query(...),
    end_date: date = Query(...),
    format: str = Query("csv", description="csv or json"),
    region: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
):
    """
    Export sales data as CSV or JSON.
    """
    start_key = int(start_date.strftime("%Y%m%d"))
    end_key = int(end_date.strftime("%Y%m%d"))
    
    query = (
        select(
            DimDate.date,
            DimProduct.sku,
            DimProduct.name.label("product_name"),
            DimProduct.category,
            DimLocation.name.label("location_name"),
            DimLocation.region,
            FactSales.units_sold,
            FactSales.units_returned,
            FactSales.revenue,
            FactSales.cost,
        )
        .join(DimDate, FactSales.date_key == DimDate.date_key)
        .join(DimProduct, FactSales.product_id == DimProduct.product_id)
        .join(DimLocation, FactSales.location_id == DimLocation.location_id)
        .where(FactSales.date_key.between(start_key, end_key))
        .order_by(DimDate.date, DimProduct.sku)
    )
    
    if region:
        query = query.where(DimLocation.region == region)
    if category:
        query = query.where(DimProduct.category == category)
    
    result = await session.execute(query)
    rows = result.all()
    
    if format == "json":
        data = [
            {
                "date": row.date.isoformat(),
                "sku": row.sku,
                "product_name": row.product_name,
                "category": row.category,
                "location": row.location_name,
                "region": row.region,
                "units_sold": row.units_sold,
                "units_returned": row.units_returned,
                "revenue": float(row.revenue),
                "cost": float(row.cost),
            }
            for row in rows
        ]
        return {"data": data, "count": len(data)}
    
    # CSV export
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "date", "sku", "product_name", "category", "location", 
        "region", "units_sold", "units_returned", "revenue", "cost"
    ])
    
    for row in rows:
        writer.writerow([
            row.date.isoformat(),
            row.sku,
            row.product_name,
            row.category,
            row.location_name,
            row.region,
            row.units_sold,
            row.units_returned,
            float(row.revenue),
            float(row.cost),
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=sales_{start_date}_{end_date}.csv"
        }
    )


@router.get("/forecast")
async def export_forecast(
    current_user: Annotated[TokenPayload, Depends(require_viewer)],
    session: Annotated[AsyncSession, Depends(get_session)],
    start_date: date = Query(...),
    end_date: date = Query(...),
    sku: Optional[str] = Query(None),
    format: str = Query("csv"),
):
    """
    Export forecast data as CSV or JSON.
    """
    start_key = int(start_date.strftime("%Y%m%d"))
    end_key = int(end_date.strftime("%Y%m%d"))
    
    query = (
        select(
            DimDate.date,
            DimProduct.sku,
            DimLocation.region,
            FactForecast.forecast_units,
            FactForecast.prediction_interval_low,
            FactForecast.prediction_interval_high,
            FactForecast.model_version,
        )
        .join(DimDate, FactForecast.date_key == DimDate.date_key)
        .join(DimProduct, FactForecast.product_id == DimProduct.product_id)
        .join(DimLocation, FactForecast.location_id == DimLocation.location_id)
        .where(FactForecast.date_key.between(start_key, end_key))
        .order_by(DimDate.date, DimProduct.sku)
    )
    
    if sku:
        query = query.where(DimProduct.sku == sku)
    
    result = await session.execute(query)
    rows = result.all()
    
    if format == "json":
        data = [
            {
                "date": row.date.isoformat(),
                "sku": row.sku,
                "region": row.region,
                "forecast_units": row.forecast_units,
                "interval_low": row.prediction_interval_low,
                "interval_high": row.prediction_interval_high,
                "model_version": row.model_version,
            }
            for row in rows
        ]
        return {"data": data, "count": len(data)}
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "date", "sku", "region", "forecast_units", 
        "interval_low", "interval_high", "model_version"
    ])
    
    for row in rows:
        writer.writerow([
            row.date.isoformat(),
            row.sku,
            row.region,
            row.forecast_units,
            row.prediction_interval_low,
            row.prediction_interval_high,
            row.model_version,
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=forecast_{start_date}_{end_date}.csv"
        }
    )


@router.post("/report", response_model=ExecutiveReport)
async def generate_report(
    request: ReportRequest,
    current_user: Annotated[TokenPayload, Depends(require_analyst)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ExecutiveReport:
    """
    Generate executive report.
    
    Requires Analyst or Admin role.
    """
    report_id = f"RPT-{uuid.uuid4().hex[:8].upper()}"
    
    start_key = int(request.start_date.strftime("%Y%m%d"))
    end_key = int(request.end_date.strftime("%Y%m%d"))
    
    sections = []
    
    if request.report_type == "weekly_summary":
        # Sales summary
        sales_result = await session.execute(
            select(
                func.sum(FactSales.revenue).label("total_revenue"),
                func.sum(FactSales.units_sold).label("total_units"),
                func.count(FactSales.id).label("transactions"),
            )
            .where(FactSales.date_key.between(start_key, end_key))
        )
        sales = sales_result.one()
        
        sections.append(ReportSection(
            title="Sales Summary",
            content={
                "total_revenue": float(sales.total_revenue or 0),
                "total_units": sales.total_units or 0,
                "transactions": sales.transactions or 0,
                "avg_transaction_value": float(sales.total_revenue or 0) / max(sales.transactions or 1, 1),
            }
        ))
        
        # Shipment summary
        shipment_result = await session.execute(
            select(
                func.count(FactShipment.id).label("total_shipments"),
                func.sum(FactShipment.units).label("units_shipped"),
                func.sum(FactShipment.co2_kg).label("total_co2"),
                func.avg(FactShipment.delay_minutes).label("avg_delay"),
            )
            .where(FactShipment.date_key.between(start_key, end_key))
        )
        shipments = shipment_result.one()
        
        sections.append(ReportSection(
            title="Logistics Summary",
            content={
                "total_shipments": shipments.total_shipments or 0,
                "units_shipped": shipments.units_shipped or 0,
                "total_co2_kg": float(shipments.total_co2 or 0),
                "avg_delay_minutes": float(shipments.avg_delay or 0),
            }
        ))
        
        # Inventory summary
        inventory_result = await session.execute(
            select(
                func.sum(FactInventorySnapshot.on_hand_value).label("total_value"),
                func.sum(FactInventorySnapshot.at_risk_units).label("at_risk"),
                func.count(FactInventorySnapshot.product_id.distinct()).label("sku_count"),
            )
            .where(FactInventorySnapshot.date_key == end_key)
        )
        inventory = inventory_result.one()
        
        sections.append(ReportSection(
            title="Inventory Position",
            content={
                "total_value": float(inventory.total_value or 0),
                "at_risk_units": inventory.at_risk or 0,
                "active_skus": inventory.sku_count or 0,
            }
        ))
    
    elif request.report_type == "sustainability_scorecard":
        # Sustainability metrics
        sus_result = await session.execute(
            select(
                func.sum(FactShipment.co2_kg).label("total_co2"),
                func.count(FactShipment.id).label("shipments"),
                func.sum(FactShipment.distance_km).label("distance"),
            )
            .where(FactShipment.date_key.between(start_key, end_key))
        )
        sus = sus_result.one()
        
        sections.append(ReportSection(
            title="Emissions Overview",
            content={
                "total_co2_kg": float(sus.total_co2 or 0),
                "shipments": sus.shipments or 0,
                "total_distance_km": float(sus.distance or 0),
                "co2_per_shipment": float(sus.total_co2 or 0) / max(sus.shipments or 1, 1),
            }
        ))
    
    return ExecutiveReport(
        report_id=report_id,
        title=f"{request.report_type.replace('_', ' ').title()} Report",
        generated_at=datetime.now().isoformat(),
        period=f"{request.start_date} to {request.end_date}",
        sections=sections,
    )
