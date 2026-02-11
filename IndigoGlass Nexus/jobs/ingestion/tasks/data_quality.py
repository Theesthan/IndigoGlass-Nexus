# =============================================================================
# IndigoGlass Nexus - Data Quality Check Tasks
# =============================================================================
"""
Celery tasks for data quality validation and monitoring.
"""

from datetime import datetime, timezone, timedelta
from typing import Any

import structlog
from celery import Task
from sqlalchemy import create_engine, text

from celery_app import app
from config import get_settings

logger = structlog.get_logger()
settings = get_settings()


def get_mysql_engine():
    """Get SQLAlchemy engine for MySQL."""
    dsn = settings.MYSQL_DSN.replace("asyncmy", "pymysql")
    return create_engine(dsn, pool_pre_ping=True)


class QualityCheckTask(Task):
    """Base task for quality checks."""
    
    autoretry_for = (Exception,)
    retry_backoff = True
    max_retries = 3


@app.task(bind=True, base=QualityCheckTask, name="tasks.data_quality.run_quality_checks")
def run_quality_checks(self) -> dict[str, Any]:
    """
    Run all data quality checks.
    
    Returns:
        Quality check results
    """
    logger.info("quality_checks_started")
    
    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": [],
        "passed": 0,
        "failed": 0,
        "warnings": 0,
    }
    
    checks = [
        check_orphaned_facts,
        check_duplicate_sales,
        check_negative_quantities,
        check_future_dates,
        check_stale_forecasts,
        check_inventory_anomalies,
    ]
    
    for check_fn in checks:
        try:
            result = check_fn()
            results["checks"].append(result)
            
            if result["status"] == "passed":
                results["passed"] += 1
            elif result["status"] == "failed":
                results["failed"] += 1
            else:
                results["warnings"] += 1
        
        except Exception as e:
            logger.error("check_error", check=check_fn.__name__, error=str(e))
            results["checks"].append({
                "name": check_fn.__name__,
                "status": "error",
                "message": str(e),
            })
            results["failed"] += 1
    
    logger.info(
        "quality_checks_completed",
        passed=results["passed"],
        failed=results["failed"],
        warnings=results["warnings"],
    )
    
    return results


def check_orphaned_facts() -> dict:
    """Check for fact records missing dimension relationships."""
    engine = get_mysql_engine()
    
    with engine.connect() as conn:
        # Check fact_sales for missing dimensions
        orphaned = conn.execute(
            text("""
                SELECT COUNT(*) FROM fact_sales fs
                LEFT JOIN dim_date d ON fs.date_key = d.date_key
                LEFT JOIN dim_product p ON fs.product_sk = p.product_sk
                LEFT JOIN dim_location l ON fs.location_sk = l.location_sk
                WHERE d.date_key IS NULL OR p.product_sk IS NULL OR l.location_sk IS NULL
            """)
        ).scalar()
        
        engine.dispose()
        
        if orphaned > 0:
            return {
                "name": "orphaned_facts",
                "status": "failed",
                "message": f"Found {orphaned} orphaned fact_sales records",
                "count": orphaned,
            }
        
        return {
            "name": "orphaned_facts",
            "status": "passed",
            "message": "No orphaned records found",
            "count": 0,
        }


def check_duplicate_sales() -> dict:
    """Check for duplicate sales transactions."""
    engine = get_mysql_engine()
    
    with engine.connect() as conn:
        duplicates = conn.execute(
            text("""
                SELECT order_id, COUNT(*) as cnt
                FROM fact_sales
                WHERE order_id IS NOT NULL
                GROUP BY order_id
                HAVING cnt > 1
                LIMIT 100
            """)
        ).fetchall()
        
        engine.dispose()
        
        if duplicates:
            return {
                "name": "duplicate_sales",
                "status": "failed",
                "message": f"Found {len(duplicates)} duplicate order IDs",
                "count": len(duplicates),
            }
        
        return {
            "name": "duplicate_sales",
            "status": "passed",
            "message": "No duplicate orders found",
            "count": 0,
        }


def check_negative_quantities() -> dict:
    """Check for records with negative quantities."""
    engine = get_mysql_engine()
    
    with engine.connect() as conn:
        negative_sales = conn.execute(
            text("SELECT COUNT(*) FROM fact_sales WHERE quantity < 0")
        ).scalar()
        
        negative_inventory = conn.execute(
            text("SELECT COUNT(*) FROM fact_inventory_snapshot WHERE quantity_on_hand < 0")
        ).scalar()
        
        engine.dispose()
        
        total = negative_sales + negative_inventory
        
        if total > 0:
            return {
                "name": "negative_quantities",
                "status": "warning",
                "message": f"Found {negative_sales} negative sales, {negative_inventory} negative inventory",
                "count": total,
            }
        
        return {
            "name": "negative_quantities",
            "status": "passed",
            "message": "No negative quantities found",
            "count": 0,
        }


def check_future_dates() -> dict:
    """Check for records with future dates."""
    engine = get_mysql_engine()
    today = datetime.now(timezone.utc).date()
    
    with engine.connect() as conn:
        future_sales = conn.execute(
            text("""
                SELECT COUNT(*) FROM fact_sales fs
                JOIN dim_date d ON fs.date_key = d.date_key
                WHERE d.full_date > :today
            """),
            {"today": today},
        ).scalar()
        
        engine.dispose()
        
        if future_sales > 0:
            return {
                "name": "future_dates",
                "status": "warning",
                "message": f"Found {future_sales} sales with future dates",
                "count": future_sales,
            }
        
        return {
            "name": "future_dates",
            "status": "passed",
            "message": "No future-dated records found",
            "count": 0,
        }


def check_stale_forecasts() -> dict:
    """Check for stale forecast models."""
    engine = get_mysql_engine()
    stale_days = 30
    
    with engine.connect() as conn:
        stale_models = conn.execute(
            text("""
                SELECT COUNT(*) FROM ml_model
                WHERE status = 'prod'
                AND trained_at < DATE_SUB(NOW(), INTERVAL :days DAY)
            """),
            {"days": stale_days},
        ).scalar()
        
        engine.dispose()
        
        if stale_models > 0:
            return {
                "name": "stale_forecasts",
                "status": "warning",
                "message": f"Found {stale_models} production models older than {stale_days} days",
                "count": stale_models,
            }
        
        return {
            "name": "stale_forecasts",
            "status": "passed",
            "message": "All production models are up to date",
            "count": 0,
        }


def check_inventory_anomalies() -> dict:
    """Check for inventory anomalies (low stock, overstock)."""
    engine = get_mysql_engine()
    
    with engine.connect() as conn:
        # Check for items below safety stock
        low_stock = conn.execute(
            text("""
                SELECT COUNT(*) FROM fact_inventory_snapshot
                WHERE quantity_available < safety_stock
                AND safety_stock IS NOT NULL
                AND date_key = (SELECT MAX(date_key) FROM fact_inventory_snapshot)
            """)
        ).scalar()
        
        # Check for items with negative days of supply
        critical = conn.execute(
            text("""
                SELECT COUNT(*) FROM fact_inventory_snapshot
                WHERE days_of_supply < 3
                AND date_key = (SELECT MAX(date_key) FROM fact_inventory_snapshot)
            """)
        ).scalar()
        
        engine.dispose()
        
        status = "passed"
        if critical > 0:
            status = "failed"
        elif low_stock > 0:
            status = "warning"
        
        return {
            "name": "inventory_anomalies",
            "status": status,
            "message": f"Low stock: {low_stock}, Critical (<3 days): {critical}",
            "low_stock": low_stock,
            "critical": critical,
        }


@app.task(name="tasks.data_quality.validate_dimension")
def validate_dimension(dimension_table: str) -> dict:
    """
    Validate dimension table data quality.
    
    Args:
        dimension_table: Name of dimension table to validate
    
    Returns:
        Validation results
    """
    engine = get_mysql_engine()
    
    allowed_tables = ["dim_date", "dim_product", "dim_location", "dim_carrier"]
    
    if dimension_table not in allowed_tables:
        return {"error": f"Invalid table: {dimension_table}"}
    
    with engine.connect() as conn:
        # Count total records
        total = conn.execute(
            text(f"SELECT COUNT(*) FROM {dimension_table}")
        ).scalar()
        
        # Count nulls in key columns
        if dimension_table == "dim_product":
            nulls = conn.execute(
                text("""
                    SELECT COUNT(*) FROM dim_product
                    WHERE product_id IS NULL OR product_name IS NULL
                """)
            ).scalar()
        elif dimension_table == "dim_location":
            nulls = conn.execute(
                text("""
                    SELECT COUNT(*) FROM dim_location
                    WHERE location_id IS NULL OR location_name IS NULL
                """)
            ).scalar()
        else:
            nulls = 0
        
        engine.dispose()
        
        return {
            "table": dimension_table,
            "total_records": total,
            "null_key_fields": nulls,
            "status": "passed" if nulls == 0 else "failed",
        }
