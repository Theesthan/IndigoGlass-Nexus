# IndigoGlass Nexus

> A production-grade Data & AI platform for forecasting demand, optimizing pharma distribution, and reporting sustainability KPIs with modern glassmorphism dashboards.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           IndigoGlass Nexus                               │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │   Frontend   │───▶│  API Service │───▶│   Optimizer  │              │
│  │   (Next.js)  │    │   (FastAPI)  │    │    (Java)    │              │
│  └──────────────┘    └──────┬───────┘    └──────────────┘              │
│                             │                                            │
│  ┌──────────────────────────┴────────────────────────────────┐         │
│  │                      Data Layer                            │         │
│  │  ┌────────┐  ┌─────────┐  ┌────────┐  ┌──────┐  ┌──────┐ │         │
│  │  │ MySQL  │  │ MongoDB │  │ Neo4j  │  │Redis │  │MinIO │ │         │
│  │  │(OLAP)  │  │ (Raw)   │  │(Graph) │  │Cache │  │ (S3) │ │         │
│  │  └────────┘  └─────────┘  └────────┘  └──────┘  └──────┘ │         │
│  └───────────────────────────────────────────────────────────┘         │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────┐          │
│  │                    Background Jobs                        │          │
│  │  ┌─────────────────┐    ┌─────────────────┐              │          │
│  │  │ Ingestion Worker│    │  ML Train Job   │              │          │
│  │  │    (Celery)     │    │   (Scheduled)   │              │          │
│  │  └─────────────────┘    └─────────────────┘              │          │
│  └──────────────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# Clone and navigate
cd IndigoGlass\ Nexus

# Copy environment file
cp .env.example .env

# Start all services
docker compose up --build -d

# Run database migrations
docker compose exec api alembic upgrade head

# Seed synthetic data
docker compose exec api python -m scripts.seed_data

# Access the application
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs
# Neo4j Browser: http://localhost:7474
```

## Project Structure

```
IndigoGlass Nexus/
├── apps/
│   └── frontend/          # Next.js dashboard with glassmorphism UI
├── services/
│   ├── api/               # FastAPI REST API
│   └── optimizer/         # Java-based route optimizer
├── jobs/
│   ├── ingestion/         # Celery workers for data ingestion
│   └── ml/                # ML training and scoring jobs
├── infra/
│   ├── docker/            # Dockerfiles for all services
│   └── aws/               # Terraform IaC for AWS deployment
├── data/
│   └── synthetic/         # Synthetic data generator
├── docs/                  # API documentation and guides
└── scripts/               # Utility scripts
```

## Key Features

### Supply Chain Analytics
- **Demand Forecasting**: XGBoost-based predictions per SKU-region
- **Inventory Risk**: Real-time stockout probability and at-risk alerts
- **Route Optimization**: TSP-D truck+drone delivery planning

### Sustainability
- CO2 per shipment and per unit tracking
- Emissions hotspot identification
- Weekly sustainability scorecard exports

### Enterprise Ready
- RBAC with JWT authentication
- Audit logging and compliance
- Full observability (OpenTelemetry + Prometheus)

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, shadcn/ui |
| API | FastAPI, SQLAlchemy 2.x, Pydantic v2 |
| ML | XGBoost, scikit-learn, pandas |
| Optimizer | Java 21, OR-Tools |
| Databases | MySQL 8, MongoDB 7, Neo4j 5, Redis 7 |
| Infrastructure | Docker, GitHub Actions, AWS (Terraform) |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/login` | Authenticate user |
| GET | `/api/v1/kpis/overview` | Top-line KPIs |
| GET | `/api/v1/forecast` | Get forecasts by SKU/region |
| POST | `/api/v1/optimizer/plan` | Generate route plan |
| GET | `/api/v1/graph/impact` | Supply chain impact analysis |
| POST | `/api/v1/exports/report` | Generate executive report |

## Configuration

See [.env.example](.env.example) for all configuration options.

## Development

```bash
# Run backend tests
docker compose exec api pytest -v

# Run frontend tests
cd apps/frontend && npm test

# Run linting
docker compose exec api ruff check .
cd apps/frontend && npm run lint
```
