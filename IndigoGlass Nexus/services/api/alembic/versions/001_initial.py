"""Initial schema with star schema and auth tables

Revision ID: 001_initial
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial schema."""
    
    # =========================================================================
    # Dimension Tables
    # =========================================================================
    
    op.create_table(
        'dim_date',
        sa.Column('date_key', sa.Integer, primary_key=True, autoincrement=False),
        sa.Column('full_date', sa.Date, nullable=False, unique=True),
        sa.Column('day_of_week', sa.SmallInteger, nullable=False),
        sa.Column('day_of_month', sa.SmallInteger, nullable=False),
        sa.Column('day_of_year', sa.SmallInteger, nullable=False),
        sa.Column('week_of_year', sa.SmallInteger, nullable=False),
        sa.Column('month', sa.SmallInteger, nullable=False),
        sa.Column('quarter', sa.SmallInteger, nullable=False),
        sa.Column('year', sa.SmallInteger, nullable=False),
        sa.Column('is_weekend', sa.Boolean, nullable=False, default=False),
        sa.Column('is_holiday', sa.Boolean, nullable=False, default=False),
        sa.Column('fiscal_week', sa.SmallInteger, nullable=True),
        sa.Column('fiscal_month', sa.SmallInteger, nullable=True),
        sa.Column('fiscal_quarter', sa.SmallInteger, nullable=True),
        sa.Column('fiscal_year', sa.SmallInteger, nullable=True),
        sa.Index('ix_dim_date_full_date', 'full_date'),
        sa.Index('ix_dim_date_year_month', 'year', 'month'),
    )
    
    op.create_table(
        'dim_product',
        sa.Column('product_sk', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('product_id', sa.String(50), nullable=False, unique=True),
        sa.Column('product_name', sa.String(255), nullable=False),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('subcategory', sa.String(100), nullable=True),
        sa.Column('brand', sa.String(100), nullable=True),
        sa.Column('unit_cost', sa.Numeric(12, 4), nullable=True),
        sa.Column('unit_price', sa.Numeric(12, 4), nullable=True),
        sa.Column('weight_kg', sa.Numeric(10, 4), nullable=True),
        sa.Column('is_cold_chain', sa.Boolean, nullable=False, default=False),
        sa.Column('shelf_life_days', sa.Integer, nullable=True),
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('valid_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_current', sa.Boolean, nullable=False, default=True),
        sa.Index('ix_dim_product_product_id', 'product_id'),
        sa.Index('ix_dim_product_category', 'category'),
    )
    
    op.create_table(
        'dim_location',
        sa.Column('location_sk', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('location_id', sa.String(50), nullable=False, unique=True),
        sa.Column('location_name', sa.String(255), nullable=False),
        sa.Column('location_type', sa.String(50), nullable=False),
        sa.Column('address', sa.String(255), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state_province', sa.String(100), nullable=True),
        sa.Column('country', sa.String(100), nullable=True),
        sa.Column('postal_code', sa.String(20), nullable=True),
        sa.Column('latitude', sa.Numeric(10, 7), nullable=True),
        sa.Column('longitude', sa.Numeric(10, 7), nullable=True),
        sa.Column('timezone', sa.String(50), nullable=True),
        sa.Column('capacity_units', sa.Integer, nullable=True),
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('valid_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_current', sa.Boolean, nullable=False, default=True),
        sa.Index('ix_dim_location_location_id', 'location_id'),
        sa.Index('ix_dim_location_type', 'location_type'),
        sa.Index('ix_dim_location_country', 'country'),
    )
    
    op.create_table(
        'dim_carrier',
        sa.Column('carrier_sk', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('carrier_id', sa.String(50), nullable=False, unique=True),
        sa.Column('carrier_name', sa.String(255), nullable=False),
        sa.Column('carrier_type', sa.String(50), nullable=True),
        sa.Column('contact_email', sa.String(255), nullable=True),
        sa.Column('contact_phone', sa.String(50), nullable=True),
        sa.Column('base_rate_per_km', sa.Numeric(10, 4), nullable=True),
        sa.Column('co2_kg_per_km', sa.Numeric(10, 6), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('valid_to', sa.DateTime(timezone=True), nullable=True),
        sa.Index('ix_dim_carrier_carrier_id', 'carrier_id'),
    )
    
    # =========================================================================
    # Fact Tables
    # =========================================================================
    
    op.create_table(
        'fact_sales',
        sa.Column('sales_id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('date_key', sa.Integer, sa.ForeignKey('dim_date.date_key'), nullable=False),
        sa.Column('product_sk', sa.Integer, sa.ForeignKey('dim_product.product_sk'), nullable=False),
        sa.Column('location_sk', sa.Integer, sa.ForeignKey('dim_location.location_sk'), nullable=False),
        sa.Column('quantity', sa.Integer, nullable=False),
        sa.Column('unit_price', sa.Numeric(12, 4), nullable=False),
        sa.Column('discount_pct', sa.Numeric(5, 2), nullable=False, default=0),
        sa.Column('total_amount', sa.Numeric(14, 4), nullable=False),
        sa.Column('order_id', sa.String(50), nullable=True),
        sa.Column('channel', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Index('ix_fact_sales_date_key', 'date_key'),
        sa.Index('ix_fact_sales_product_sk', 'product_sk'),
        sa.Index('ix_fact_sales_location_sk', 'location_sk'),
        sa.Index('ix_fact_sales_date_product', 'date_key', 'product_sk'),
    )
    
    op.create_table(
        'fact_inventory_snapshot',
        sa.Column('snapshot_id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('date_key', sa.Integer, sa.ForeignKey('dim_date.date_key'), nullable=False),
        sa.Column('product_sk', sa.Integer, sa.ForeignKey('dim_product.product_sk'), nullable=False),
        sa.Column('location_sk', sa.Integer, sa.ForeignKey('dim_location.location_sk'), nullable=False),
        sa.Column('quantity_on_hand', sa.Integer, nullable=False),
        sa.Column('quantity_reserved', sa.Integer, nullable=False, default=0),
        sa.Column('quantity_available', sa.Integer, nullable=False),
        sa.Column('reorder_point', sa.Integer, nullable=True),
        sa.Column('safety_stock', sa.Integer, nullable=True),
        sa.Column('days_of_supply', sa.Numeric(6, 2), nullable=True),
        sa.Column('snapshot_time', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Index('ix_fact_inventory_date_key', 'date_key'),
        sa.Index('ix_fact_inventory_product_sk', 'product_sk'),
        sa.Index('ix_fact_inventory_location_sk', 'location_sk'),
        sa.UniqueConstraint('date_key', 'product_sk', 'location_sk', name='uq_inventory_snapshot'),
    )
    
    op.create_table(
        'fact_shipment',
        sa.Column('shipment_id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('shipment_date_key', sa.Integer, sa.ForeignKey('dim_date.date_key'), nullable=False),
        sa.Column('delivery_date_key', sa.Integer, sa.ForeignKey('dim_date.date_key'), nullable=True),
        sa.Column('origin_location_sk', sa.Integer, sa.ForeignKey('dim_location.location_sk'), nullable=False),
        sa.Column('destination_location_sk', sa.Integer, sa.ForeignKey('dim_location.location_sk'), nullable=False),
        sa.Column('carrier_sk', sa.Integer, sa.ForeignKey('dim_carrier.carrier_sk'), nullable=False),
        sa.Column('shipment_number', sa.String(50), nullable=False, unique=True),
        sa.Column('status', sa.String(30), nullable=False, default='pending'),
        sa.Column('total_weight_kg', sa.Numeric(12, 4), nullable=True),
        sa.Column('total_volume_m3', sa.Numeric(12, 6), nullable=True),
        sa.Column('distance_km', sa.Numeric(10, 2), nullable=True),
        sa.Column('transport_mode', sa.String(30), nullable=True),
        sa.Column('cost_usd', sa.Numeric(12, 4), nullable=True),
        sa.Column('co2_emission_kg', sa.Numeric(12, 4), nullable=True),
        sa.Column('estimated_delivery', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actual_delivery', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Index('ix_fact_shipment_date_key', 'shipment_date_key'),
        sa.Index('ix_fact_shipment_carrier_sk', 'carrier_sk'),
        sa.Index('ix_fact_shipment_status', 'status'),
    )
    
    op.create_table(
        'fact_forecast',
        sa.Column('forecast_id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('date_key', sa.Integer, sa.ForeignKey('dim_date.date_key'), nullable=False),
        sa.Column('product_sk', sa.Integer, sa.ForeignKey('dim_product.product_sk'), nullable=False),
        sa.Column('location_sk', sa.Integer, sa.ForeignKey('dim_location.location_sk'), nullable=False),
        sa.Column('model_id', sa.Integer, nullable=True),
        sa.Column('forecast_qty', sa.Numeric(12, 2), nullable=False),
        sa.Column('forecast_lower', sa.Numeric(12, 2), nullable=True),
        sa.Column('forecast_upper', sa.Numeric(12, 2), nullable=True),
        sa.Column('actual_qty', sa.Numeric(12, 2), nullable=True),
        sa.Column('mape', sa.Numeric(8, 4), nullable=True),
        sa.Column('bias', sa.Numeric(10, 4), nullable=True),
        sa.Column('horizon_days', sa.Integer, nullable=False, default=1),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Index('ix_fact_forecast_date_key', 'date_key'),
        sa.Index('ix_fact_forecast_product_sk', 'product_sk'),
        sa.Index('ix_fact_forecast_location_sk', 'location_sk'),
        sa.Index('ix_fact_forecast_model_id', 'model_id'),
    )
    
    op.create_table(
        'fact_route_plan',
        sa.Column('plan_id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('plan_date_key', sa.Integer, sa.ForeignKey('dim_date.date_key'), nullable=False),
        sa.Column('carrier_sk', sa.Integer, sa.ForeignKey('dim_carrier.carrier_sk'), nullable=False),
        sa.Column('origin_location_sk', sa.Integer, sa.ForeignKey('dim_location.location_sk'), nullable=False),
        sa.Column('plan_name', sa.String(100), nullable=True),
        sa.Column('status', sa.String(30), nullable=False, default='draft'),
        sa.Column('total_stops', sa.Integer, nullable=False),
        sa.Column('total_distance_km', sa.Numeric(12, 2), nullable=True),
        sa.Column('total_cost_usd', sa.Numeric(14, 4), nullable=True),
        sa.Column('total_co2_kg', sa.Numeric(12, 4), nullable=True),
        sa.Column('estimated_duration_hrs', sa.Numeric(8, 2), nullable=True),
        sa.Column('stops_json', mysql.JSON, nullable=True),
        sa.Column('route_geometry', mysql.JSON, nullable=True),
        sa.Column('solver_version', sa.String(50), nullable=True),
        sa.Column('solve_time_ms', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approved_by', sa.String(255), nullable=True),
        sa.Index('ix_fact_route_plan_date_key', 'plan_date_key'),
        sa.Index('ix_fact_route_plan_status', 'status'),
    )
    
    # =========================================================================
    # ML Registry Tables
    # =========================================================================
    
    op.create_table(
        'ml_model',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('model_name', sa.String(100), nullable=False),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('algorithm', sa.String(100), nullable=True),
        sa.Column('status', sa.String(30), nullable=False, default='staged'),
        sa.Column('metrics_json', mysql.JSON, nullable=True),
        sa.Column('hyperparams_json', mysql.JSON, nullable=True),
        sa.Column('feature_names_json', mysql.JSON, nullable=True),
        sa.Column('artifact_s3_uri', sa.String(500), nullable=True),
        sa.Column('training_data_start', sa.Date, nullable=True),
        sa.Column('training_data_end', sa.Date, nullable=True),
        sa.Column('trained_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trained_by', sa.String(255), nullable=True),
        sa.Column('promoted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('promoted_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('model_name', 'version', name='uq_model_version'),
        sa.Index('ix_ml_model_status', 'status'),
    )
    
    op.create_table(
        'ml_model_assignment',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('model_id', sa.Integer, sa.ForeignKey('ml_model.id'), nullable=False),
        sa.Column('product_sk', sa.Integer, sa.ForeignKey('dim_product.product_sk'), nullable=True),
        sa.Column('location_sk', sa.Integer, sa.ForeignKey('dim_location.location_sk'), nullable=True),
        sa.Column('is_default', sa.Boolean, nullable=False, default=False),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Index('ix_ml_model_assignment_model_id', 'model_id'),
    )
    
    # =========================================================================
    # Auth Tables
    # =========================================================================
    
    op.create_table(
        'auth_user',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('role', sa.String(50), nullable=False, default='viewer'),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, onupdate=sa.func.now()),
        sa.Index('ix_auth_user_email', 'email'),
    )
    
    op.create_table(
        'auth_audit_log',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer, nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=True),
        sa.Column('entity_id', sa.String(100), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('metadata_json', mysql.JSON, nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Index('ix_auth_audit_log_user_id', 'user_id'),
        sa.Index('ix_auth_audit_log_action', 'action'),
        sa.Index('ix_auth_audit_log_timestamp', 'timestamp'),
    )


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table('auth_audit_log')
    op.drop_table('auth_user')
    op.drop_table('ml_model_assignment')
    op.drop_table('ml_model')
    op.drop_table('fact_route_plan')
    op.drop_table('fact_forecast')
    op.drop_table('fact_shipment')
    op.drop_table('fact_inventory_snapshot')
    op.drop_table('fact_sales')
    op.drop_table('dim_carrier')
    op.drop_table('dim_location')
    op.drop_table('dim_product')
    op.drop_table('dim_date')
