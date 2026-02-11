# =============================================================================
# IndigoGlass Nexus - MongoDB Connection
# =============================================================================
"""
Async MongoDB connection using Motor driver.
"""

from typing import Optional

import structlog
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings

logger = structlog.get_logger()

# Global client and database
_client: Optional[AsyncIOMotorClient] = None
_database: Optional[AsyncIOMotorDatabase] = None


async def init_mongodb() -> None:
    """Initialize MongoDB connection."""
    global _client, _database
    
    _client = AsyncIOMotorClient(
        settings.MONGODB_URL,
        maxPoolSize=50,
        minPoolSize=10,
        serverSelectionTimeoutMS=5000,
    )
    
    _database = _client[settings.MONGODB_DATABASE]
    
    # Create indexes
    await _create_indexes()
    
    logger.info("mongodb_initialized", database=settings.MONGODB_DATABASE)


async def _create_indexes() -> None:
    """Create required indexes for MongoDB collections."""
    if not _database:
        return
    
    # Raw sales events - unique on event_id + source
    await _database.raw_sales_events.create_index(
        [("event_id", 1), ("source", 1)],
        unique=True,
        background=True,
    )
    
    # Raw shipment events - unique on ingestion_hash
    await _database.raw_shipment_events.create_index(
        "ingestion_hash",
        unique=True,
        background=True,
    )
    await _database.raw_shipment_events.create_index(
        [("shipment_id", 1), ("event_ts", -1)],
        background=True,
    )
    
    # Raw inventory events
    await _database.raw_inventory_events.create_index(
        [("event_id", 1), ("source", 1)],
        unique=True,
        background=True,
    )
    
    # Raw emissions events
    await _database.raw_emissions_events.create_index(
        [("event_id", 1)],
        unique=True,
        background=True,
    )
    
    logger.info("mongodb_indexes_created")


async def close_mongodb() -> None:
    """Close MongoDB connection."""
    global _client, _database
    
    if _client:
        _client.close()
        _client = None
        _database = None
        logger.info("mongodb_closed")


def get_database() -> AsyncIOMotorDatabase:
    """Get the MongoDB database instance."""
    if not _database:
        raise RuntimeError("MongoDB not initialized. Call init_mongodb() first.")
    return _database


def get_collection(name: str):
    """Get a MongoDB collection by name."""
    db = get_database()
    return db[name]


async def check_mongodb_health() -> bool:
    """Check if MongoDB is healthy."""
    try:
        if not _client:
            return False
        await _client.admin.command("ping")
        return True
    except Exception as e:
        logger.warning("mongodb_health_check_failed", error=str(e))
        return False
