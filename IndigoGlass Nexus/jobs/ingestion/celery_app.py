# =============================================================================
# IndigoGlass Nexus - Celery Application Configuration
# =============================================================================
"""
Celery application with task routing and beat schedule.
"""

import os
from celery import Celery
from kombu import Queue

# Load environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
app = Celery(
    "ingestion",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "tasks.raw_to_curated",
        "tasks.data_quality",
        "tasks.aggregations",
    ],
)

# Celery configuration
app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3300,  # 55 minutes
    
    # Result settings
    result_expires=86400,  # 24 hours
    result_extended=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    
    # Queue settings
    task_queues=(
        Queue("ingestion", routing_key="ingestion.#"),
        Queue("aggregation", routing_key="aggregation.#"),
        Queue("quality", routing_key="quality.#"),
    ),
    
    task_default_queue="ingestion",
    task_default_exchange="ingestion",
    task_default_routing_key="ingestion.default",
    
    # Task routes
    task_routes={
        "tasks.raw_to_curated.*": {"queue": "ingestion"},
        "tasks.data_quality.*": {"queue": "quality"},
        "tasks.aggregations.*": {"queue": "aggregation"},
    },
    
    # Beat schedule for periodic tasks
    beat_schedule={
        "daily-sales-aggregation": {
            "task": "tasks.aggregations.aggregate_daily_sales",
            "schedule": 3600.0,  # Every hour
            "options": {"queue": "aggregation"},
        },
        "daily-inventory-snapshot": {
            "task": "tasks.aggregations.snapshot_inventory",
            "schedule": 86400.0,  # Daily
            "options": {"queue": "aggregation"},
        },
        "hourly-data-quality-check": {
            "task": "tasks.data_quality.run_quality_checks",
            "schedule": 3600.0,  # Every hour
            "options": {"queue": "quality"},
        },
    },
)

# OpenTelemetry instrumentation
if os.getenv("OTEL_ENABLED", "false").lower() == "true":
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.instrumentation.celery import CeleryInstrumentor
    
    trace.set_tracer_provider(TracerProvider())
    CeleryInstrumentor().instrument()
