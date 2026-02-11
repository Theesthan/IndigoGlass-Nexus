# =============================================================================
# IndigoGlass Nexus - Ingestion Tasks Package
# =============================================================================
"""
Celery tasks for data ingestion and processing.
"""

from tasks.raw_to_curated import (
    ingest_sales,
    ingest_inventory,
    ingest_shipments,
)
from tasks.data_quality import (
    run_quality_checks,
    validate_dimension,
)
from tasks.aggregations import (
    aggregate_daily_sales,
    snapshot_inventory,
    compute_kpi_trends,
    refresh_materialized_views,
)

__all__ = [
    # Raw to curated
    "ingest_sales",
    "ingest_inventory",
    "ingest_shipments",
    # Data quality
    "run_quality_checks",
    "validate_dimension",
    # Aggregations
    "aggregate_daily_sales",
    "snapshot_inventory",
    "compute_kpi_trends",
    "refresh_materialized_views",
]
