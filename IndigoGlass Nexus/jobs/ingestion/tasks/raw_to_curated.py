# =============================================================================
# IndigoGlass Nexus - Raw to Curated Transform Tasks
# =============================================================================
"""
Celery tasks for transforming raw events from MongoDB to curated MySQL warehouse.
"""

import hashlib
from datetime import datetime, timezone
from typing import Any

import structlog
from celery import Task
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
from tenacity import retry, stop_after_attempt, wait_exponential

from celery_app import app
from config import get_settings

logger = structlog.get_logger()
settings = get_settings()


def get_mongo_client() -> MongoClient:
    """Get synchronous MongoDB client for Celery tasks."""
    return MongoClient(settings.MONGO_URI)


def get_mysql_engine():
    """Get SQLAlchemy engine for MySQL."""
    # Use sync driver for Celery
    dsn = settings.MYSQL_DSN.replace("asyncmy", "pymysql")
    return create_engine(dsn, pool_pre_ping=True)


def compute_idempotency_key(data: dict, keys: list[str]) -> str:
    """Compute SHA256 hash for idempotency check."""
    key_data = "".join(str(data.get(k, "")) for k in keys)
    return hashlib.sha256(key_data.encode()).hexdigest()


class BaseIngestionTask(Task):
    """Base task with error handling and logging."""
    
    autoretry_for = (Exception,)
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True
    max_retries = 5
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(
            "task_failed",
            task=self.name,
            task_id=task_id,
            error=str(exc),
        )
    
    def on_success(self, retval, task_id, args, kwargs):
        logger.info(
            "task_succeeded",
            task=self.name,
            task_id=task_id,
        )


@app.task(bind=True, base=BaseIngestionTask, name="tasks.raw_to_curated.ingest_sales")
def ingest_sales(
    self,
    start_date: str,
    end_date: str,
    batch_size: int = 1000,
) -> dict[str, Any]:
    """
    Transform raw sales events to fact_sales table.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        batch_size: Batch size for processing
    
    Returns:
        Processing statistics
    """
    logger.info(
        "ingest_sales_started",
        start_date=start_date,
        end_date=end_date,
    )
    
    mongo = get_mongo_client()
    engine = get_mysql_engine()
    
    try:
        db = mongo[settings.MONGO_DB]
        collection = db["raw_sales"]
        
        # Query raw events
        query = {
            "event_date": {
                "$gte": start_date,
                "$lte": end_date,
            },
            "processed": {"$ne": True},
        }
        
        cursor = collection.find(query).batch_size(batch_size)
        
        processed = 0
        skipped = 0
        errors = 0
        
        with engine.connect() as conn:
            for doc in cursor:
                try:
                    # Compute idempotency key
                    idem_key = compute_idempotency_key(
                        doc,
                        ["order_id", "product_id", "location_id", "event_date"],
                    )
                    
                    # Check if already processed
                    existing = conn.execute(
                        text("SELECT 1 FROM fact_sales WHERE order_id = :order_id LIMIT 1"),
                        {"order_id": doc.get("order_id")},
                    ).fetchone()
                    
                    if existing:
                        skipped += 1
                        continue
                    
                    # Get dimension keys
                    date_key = _get_date_key(conn, doc.get("event_date"))
                    product_sk = _get_product_sk(conn, doc.get("product_id"))
                    location_sk = _get_location_sk(conn, doc.get("location_id"))
                    
                    if not all([date_key, product_sk, location_sk]):
                        logger.warning(
                            "missing_dimension",
                            doc_id=str(doc.get("_id")),
                        )
                        errors += 1
                        continue
                    
                    # Insert into fact table
                    conn.execute(
                        text("""
                            INSERT INTO fact_sales (
                                date_key, product_sk, location_sk,
                                quantity, unit_price, discount_pct, total_amount,
                                order_id, channel
                            ) VALUES (
                                :date_key, :product_sk, :location_sk,
                                :quantity, :unit_price, :discount_pct, :total_amount,
                                :order_id, :channel
                            )
                        """),
                        {
                            "date_key": date_key,
                            "product_sk": product_sk,
                            "location_sk": location_sk,
                            "quantity": doc.get("quantity", 0),
                            "unit_price": doc.get("unit_price", 0),
                            "discount_pct": doc.get("discount_pct", 0),
                            "total_amount": doc.get("total_amount", 0),
                            "order_id": doc.get("order_id"),
                            "channel": doc.get("channel"),
                        },
                    )
                    
                    # Mark as processed in MongoDB
                    collection.update_one(
                        {"_id": doc["_id"]},
                        {
                            "$set": {
                                "processed": True,
                                "processed_at": datetime.now(timezone.utc),
                            }
                        },
                    )
                    
                    processed += 1
                    
                    # Commit periodically
                    if processed % batch_size == 0:
                        conn.commit()
                        logger.info("batch_committed", processed=processed)
                
                except Exception as e:
                    logger.error("record_error", error=str(e))
                    errors += 1
                    continue
            
            conn.commit()
        
        stats = {
            "processed": processed,
            "skipped": skipped,
            "errors": errors,
            "start_date": start_date,
            "end_date": end_date,
        }
        
        logger.info("ingest_sales_completed", **stats)
        return stats
    
    finally:
        mongo.close()
        engine.dispose()


@app.task(bind=True, base=BaseIngestionTask, name="tasks.raw_to_curated.ingest_inventory")
def ingest_inventory(
    self,
    snapshot_date: str,
    batch_size: int = 1000,
) -> dict[str, Any]:
    """
    Transform raw inventory snapshots to fact_inventory_snapshot table.
    
    Args:
        snapshot_date: Snapshot date (YYYY-MM-DD)
        batch_size: Batch size for processing
    
    Returns:
        Processing statistics
    """
    logger.info("ingest_inventory_started", snapshot_date=snapshot_date)
    
    mongo = get_mongo_client()
    engine = get_mysql_engine()
    
    try:
        db = mongo[settings.MONGO_DB]
        collection = db["raw_inventory"]
        
        query = {
            "snapshot_date": snapshot_date,
            "processed": {"$ne": True},
        }
        
        cursor = collection.find(query).batch_size(batch_size)
        
        processed = 0
        errors = 0
        
        with engine.connect() as conn:
            for doc in cursor:
                try:
                    date_key = _get_date_key(conn, snapshot_date)
                    product_sk = _get_product_sk(conn, doc.get("product_id"))
                    location_sk = _get_location_sk(conn, doc.get("location_id"))
                    
                    if not all([date_key, product_sk, location_sk]):
                        errors += 1
                        continue
                    
                    # Upsert inventory snapshot
                    conn.execute(
                        text("""
                            INSERT INTO fact_inventory_snapshot (
                                date_key, product_sk, location_sk,
                                quantity_on_hand, quantity_reserved, quantity_available,
                                reorder_point, safety_stock, days_of_supply
                            ) VALUES (
                                :date_key, :product_sk, :location_sk,
                                :qty_on_hand, :qty_reserved, :qty_available,
                                :reorder_point, :safety_stock, :days_of_supply
                            )
                            ON DUPLICATE KEY UPDATE
                                quantity_on_hand = VALUES(quantity_on_hand),
                                quantity_reserved = VALUES(quantity_reserved),
                                quantity_available = VALUES(quantity_available),
                                days_of_supply = VALUES(days_of_supply)
                        """),
                        {
                            "date_key": date_key,
                            "product_sk": product_sk,
                            "location_sk": location_sk,
                            "qty_on_hand": doc.get("quantity_on_hand", 0),
                            "qty_reserved": doc.get("quantity_reserved", 0),
                            "qty_available": doc.get("quantity_available", 0),
                            "reorder_point": doc.get("reorder_point"),
                            "safety_stock": doc.get("safety_stock"),
                            "days_of_supply": doc.get("days_of_supply"),
                        },
                    )
                    
                    collection.update_one(
                        {"_id": doc["_id"]},
                        {"$set": {"processed": True}},
                    )
                    
                    processed += 1
                    
                except Exception as e:
                    logger.error("inventory_record_error", error=str(e))
                    errors += 1
            
            conn.commit()
        
        return {"processed": processed, "errors": errors}
    
    finally:
        mongo.close()
        engine.dispose()


@app.task(bind=True, base=BaseIngestionTask, name="tasks.raw_to_curated.ingest_shipments")
def ingest_shipments(
    self,
    start_date: str,
    end_date: str,
    batch_size: int = 500,
) -> dict[str, Any]:
    """
    Transform raw shipment events to fact_shipment table.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        batch_size: Batch size for processing
    
    Returns:
        Processing statistics
    """
    logger.info(
        "ingest_shipments_started",
        start_date=start_date,
        end_date=end_date,
    )
    
    mongo = get_mongo_client()
    engine = get_mysql_engine()
    
    try:
        db = mongo[settings.MONGO_DB]
        collection = db["raw_shipments"]
        
        query = {
            "shipment_date": {"$gte": start_date, "$lte": end_date},
            "processed": {"$ne": True},
        }
        
        cursor = collection.find(query).batch_size(batch_size)
        
        processed = 0
        errors = 0
        
        with engine.connect() as conn:
            for doc in cursor:
                try:
                    # Get dimension keys
                    ship_date_key = _get_date_key(conn, doc.get("shipment_date"))
                    origin_sk = _get_location_sk(conn, doc.get("origin_id"))
                    dest_sk = _get_location_sk(conn, doc.get("destination_id"))
                    carrier_sk = _get_carrier_sk(conn, doc.get("carrier_id"))
                    
                    if not all([ship_date_key, origin_sk, dest_sk, carrier_sk]):
                        errors += 1
                        continue
                    
                    # Check duplicate by shipment number
                    existing = conn.execute(
                        text("SELECT 1 FROM fact_shipment WHERE shipment_number = :sn LIMIT 1"),
                        {"sn": doc.get("shipment_number")},
                    ).fetchone()
                    
                    if existing:
                        continue
                    
                    conn.execute(
                        text("""
                            INSERT INTO fact_shipment (
                                shipment_date_key, origin_location_sk, destination_location_sk,
                                carrier_sk, shipment_number, status,
                                total_weight_kg, distance_km, transport_mode,
                                cost_usd, co2_emission_kg
                            ) VALUES (
                                :ship_date_key, :origin_sk, :dest_sk,
                                :carrier_sk, :shipment_number, :status,
                                :weight, :distance, :mode,
                                :cost, :co2
                            )
                        """),
                        {
                            "ship_date_key": ship_date_key,
                            "origin_sk": origin_sk,
                            "dest_sk": dest_sk,
                            "carrier_sk": carrier_sk,
                            "shipment_number": doc.get("shipment_number"),
                            "status": doc.get("status", "pending"),
                            "weight": doc.get("total_weight_kg"),
                            "distance": doc.get("distance_km"),
                            "mode": doc.get("transport_mode"),
                            "cost": doc.get("cost_usd"),
                            "co2": doc.get("co2_emission_kg"),
                        },
                    )
                    
                    collection.update_one(
                        {"_id": doc["_id"]},
                        {"$set": {"processed": True}},
                    )
                    
                    processed += 1
                    
                except Exception as e:
                    logger.error("shipment_record_error", error=str(e))
                    errors += 1
            
            conn.commit()
        
        return {"processed": processed, "errors": errors}
    
    finally:
        mongo.close()
        engine.dispose()


# =============================================================================
# Helper Functions
# =============================================================================

def _get_date_key(conn, date_str: str) -> int | None:
    """Get date_key from dim_date for a given date string."""
    if not date_str:
        return None
    result = conn.execute(
        text("SELECT date_key FROM dim_date WHERE full_date = :d LIMIT 1"),
        {"d": date_str},
    ).fetchone()
    return result[0] if result else None


def _get_product_sk(conn, product_id: str) -> int | None:
    """Get product_sk from dim_product for a given product_id."""
    if not product_id:
        return None
    result = conn.execute(
        text("SELECT product_sk FROM dim_product WHERE product_id = :pid AND is_current = 1 LIMIT 1"),
        {"pid": product_id},
    ).fetchone()
    return result[0] if result else None


def _get_location_sk(conn, location_id: str) -> int | None:
    """Get location_sk from dim_location for a given location_id."""
    if not location_id:
        return None
    result = conn.execute(
        text("SELECT location_sk FROM dim_location WHERE location_id = :lid AND is_current = 1 LIMIT 1"),
        {"lid": location_id},
    ).fetchone()
    return result[0] if result else None


def _get_carrier_sk(conn, carrier_id: str) -> int | None:
    """Get carrier_sk from dim_carrier for a given carrier_id."""
    if not carrier_id:
        return None
    result = conn.execute(
        text("SELECT carrier_sk FROM dim_carrier WHERE carrier_id = :cid LIMIT 1"),
        {"cid": carrier_id},
    ).fetchone()
    return result[0] if result else None
