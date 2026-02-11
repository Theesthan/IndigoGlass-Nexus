# =============================================================================
# IndigoGlass Nexus - SQLAlchemy Models
# =============================================================================
"""
Star schema models for the curated data warehouse.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Index,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.mysql import Base


# =============================================================================
# Dimension Tables
# =============================================================================

class DimDate(Base):
    """Date dimension for time-series analytics."""
    __tablename__ = "dim_date"
    
    date_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    date: Mapped[date] = mapped_column(Date, unique=True, nullable=False, index=True)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    day_name: Mapped[str] = mapped_column(String(10), nullable=False)
    week: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    month_name: Mapped[str] = mapped_column(String(10), nullable=False)
    quarter: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    is_weekend: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_holiday: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class DimProduct(Base):
    """Product dimension for SKU master data."""
    __tablename__ = "dim_product"
    
    product_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    subcategory: Mapped[Optional[str]] = mapped_column(String(100))
    unit_weight_kg: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    unit_volume_m3: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    shelf_life_days: Mapped[int] = mapped_column(Integer, nullable=False)
    is_controlled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_temperature_sensitive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class DimLocation(Base):
    """Location dimension for warehouses, factories, and customers."""
    __tablename__ = "dim_location"
    
    location_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    location_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(
        Enum("factory", "warehouse", "distribution_center", "customer", "pharmacy", "hospital", name="location_type"),
        nullable=False,
        index=True,
    )
    region: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[Optional[str]] = mapped_column(String(100))
    address: Mapped[Optional[str]] = mapped_column(String(500))
    latitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    capacity_units: Mapped[Optional[int]] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DimCarrier(Base):
    """Carrier dimension for transport modes."""
    __tablename__ = "dim_carrier"
    
    carrier_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    carrier_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    mode: Mapped[str] = mapped_column(
        Enum("truck", "drone", "rail", "air", "sea", name="carrier_mode"),
        nullable=False,
        index=True,
    )
    capacity_units: Mapped[int] = mapped_column(Integer, nullable=False)
    capacity_weight_kg: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    cost_per_km: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    co2_per_km_kg: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    max_range_km: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


# =============================================================================
# Fact Tables
# =============================================================================

class FactSales(Base):
    """Daily sales fact table."""
    __tablename__ = "fact_sales"
    __table_args__ = (
        UniqueConstraint("date_key", "product_id", "location_id", name="uq_sales_date_product_location"),
        Index("idx_sales_date", "date_key"),
        Index("idx_sales_product", "product_id"),
        Index("idx_sales_location", "location_id"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date_key: Mapped[int] = mapped_column(Integer, ForeignKey("dim_date.date_key"), nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("dim_product.product_id"), nullable=False)
    location_id: Mapped[int] = mapped_column(Integer, ForeignKey("dim_location.location_id"), nullable=False)
    units_sold: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    units_returned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revenue: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    cost: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    promotion_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class FactInventorySnapshot(Base):
    """Daily inventory snapshot fact table."""
    __tablename__ = "fact_inventory_snapshot"
    __table_args__ = (
        UniqueConstraint("date_key", "product_id", "location_id", name="uq_inventory_date_product_location"),
        Index("idx_inventory_date", "date_key"),
        Index("idx_inventory_product", "product_id"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date_key: Mapped[int] = mapped_column(Integer, ForeignKey("dim_date.date_key"), nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("dim_product.product_id"), nullable=False)
    location_id: Mapped[int] = mapped_column(Integer, ForeignKey("dim_location.location_id"), nullable=False)
    on_hand_units: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    on_hand_value: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    reserved_units: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    at_risk_units: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    days_of_supply: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    stockout_probability: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4))


class FactShipment(Base):
    """Shipment fact table for logistics tracking."""
    __tablename__ = "fact_shipment"
    __table_args__ = (
        Index("idx_shipment_date", "date_key"),
        Index("idx_shipment_status", "status"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    shipment_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    date_key: Mapped[int] = mapped_column(Integer, ForeignKey("dim_date.date_key"), nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("dim_product.product_id"), nullable=False)
    from_location_id: Mapped[int] = mapped_column(Integer, ForeignKey("dim_location.location_id"), nullable=False)
    to_location_id: Mapped[int] = mapped_column(Integer, ForeignKey("dim_location.location_id"), nullable=False)
    carrier_id: Mapped[int] = mapped_column(Integer, ForeignKey("dim_carrier.carrier_id"), nullable=False)
    units: Mapped[int] = mapped_column(Integer, nullable=False)
    planned_departure: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    actual_departure: Mapped[Optional[datetime]] = mapped_column(DateTime)
    planned_eta: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    actual_eta: Mapped[Optional[datetime]] = mapped_column(DateTime)
    distance_km: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    cost: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    co2_kg: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("pending", "in_transit", "delivered", "delayed", "cancelled", name="shipment_status"),
        nullable=False,
        default="pending",
    )
    delay_minutes: Mapped[Optional[int]] = mapped_column(Integer)


class FactForecast(Base):
    """Demand forecast fact table."""
    __tablename__ = "fact_forecast"
    __table_args__ = (
        UniqueConstraint("date_key", "product_id", "location_id", "model_version", name="uq_forecast_unique"),
        Index("idx_forecast_date", "date_key"),
        Index("idx_forecast_model", "model_version"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date_key: Mapped[int] = mapped_column(Integer, ForeignKey("dim_date.date_key"), nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("dim_product.product_id"), nullable=False)
    location_id: Mapped[int] = mapped_column(Integer, ForeignKey("dim_location.location_id"), nullable=False)
    forecast_units: Mapped[int] = mapped_column(Integer, nullable=False)
    prediction_interval_low: Mapped[int] = mapped_column(Integer, nullable=False)
    prediction_interval_high: Mapped[int] = mapped_column(Integer, nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class FactRoutePlan(Base):
    """Route optimization plan fact table."""
    __tablename__ = "fact_route_plan"
    __table_args__ = (
        Index("idx_route_plan_date", "date_key"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    date_key: Mapped[int] = mapped_column(Integer, ForeignKey("dim_date.date_key"), nullable=False)
    from_location_id: Mapped[int] = mapped_column(Integer, ForeignKey("dim_location.location_id"), nullable=False)
    stops_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    total_stops: Mapped[int] = mapped_column(Integer, nullable=False)
    total_distance_km: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    total_co2_kg: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    truck_distance_km: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    drone_distance_km: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    drone_sorties: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    feasibility_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    violations_json: Mapped[Optional[dict]] = mapped_column(JSON)
    optimizer_runtime_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# =============================================================================
# ML Model Registry Tables
# =============================================================================

class MLModel(Base):
    """ML model registry."""
    __tablename__ = "ml_model"
    __table_args__ = (
        UniqueConstraint("model_name", "version", name="uq_model_name_version"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    train_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    train_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    feature_schema_version: Mapped[str] = mapped_column(String(50), nullable=False)
    dataset_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    metrics_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    hyperparameters_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    artifact_uri: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("staged", "prod", "archived", name="model_status"),
        nullable=False,
        default="staged",
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    promoted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    promoted_by: Mapped[Optional[str]] = mapped_column(String(100))


class MLModelAssignment(Base):
    """Assignment of models to SKU-region pairs."""
    __tablename__ = "ml_model_assignment"
    __table_args__ = (
        UniqueConstraint("product_id", "location_id", name="uq_assignment_product_location"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("dim_product.product_id"), nullable=False)
    location_id: Mapped[int] = mapped_column(Integer, ForeignKey("dim_location.location_id"), nullable=False)
    model_id: Mapped[int] = mapped_column(Integer, ForeignKey("ml_model.id"), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    assigned_by: Mapped[str] = mapped_column(String(100), nullable=False)


# =============================================================================
# Security Tables
# =============================================================================

class AuthUser(Base):
    """User authentication table."""
    __tablename__ = "auth_user"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum("admin", "analyst", "viewer", name="user_role"),
        nullable=False,
        default="viewer",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class AuthAuditLog(Base):
    """Audit log for security-relevant actions."""
    __tablename__ = "auth_audit_log"
    __table_args__ = (
        Index("idx_audit_user", "user_id"),
        Index("idx_audit_timestamp", "timestamp"),
        Index("idx_audit_action", "action"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("auth_user.id"))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[Optional[str]] = mapped_column(String(100))
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
