# IndigoGlass Nexus

A production-grade Data & AI platform for forecasting demand, optimizing pharma distribution, and reporting sustainability KPIs with modern glassmorphism dashboards.

## Quick Start

```bash
# Start all services
docker-compose up -d

# Generate synthetic data
cd data/synthetic && python generate.py --days 90

# Run database migrations
docker-compose exec api alembic upgrade head

# Access the application
open http://localhost:3000
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Next.js Frontend                         │
│                    (Glassmorphism Dashboard)                     │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Gateway                           │
│              (Auth, Rate Limiting, Routing)                      │
└─────────────────────────────────────────────────────────────────┘
           │                    │                    │
           ▼                    ▼                    ▼
┌─────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   MySQL 8       │  │  Java Optimizer  │  │  Celery Workers  │
│  (Star Schema)  │  │   (OR-Tools)     │  │  (Ingestion/ML)  │
└─────────────────┘  └──────────────────┘  └──────────────────┘
           │                    │                    │
           ▼                    ▼                    ▼
┌─────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   MongoDB 7     │  │     Redis 7      │  │     MinIO        │
│  (Raw Events)   │  │  (Cache/Broker)  │  │  (S3 Storage)    │
└─────────────────┘  └──────────────────┘  └──────────────────┘
           │
           ▼
┌─────────────────┐
│    Neo4j 5      │
│ (Supply Graph)  │
└─────────────────┘
```

## Project Structure

```
IndigoGlass Nexus/
├── apps/
│   └── frontend/           # Next.js 14 with glassmorphism UI
├── services/
│   ├── api/               # FastAPI backend
│   │   ├── app/
│   │   │   ├── api/v1/    # REST endpoints
│   │   │   ├── core/      # Config, security, middleware
│   │   │   ├── db/        # Database connections
│   │   │   ├── models/    # SQLAlchemy models
│   │   │   └── schemas/   # Pydantic schemas
│   │   └── alembic/       # Database migrations
│   └── optimizer/         # Java Spring Boot + OR-Tools
├── jobs/
│   ├── ingestion/         # Celery data ingestion workers
│   └── ml/               # XGBoost training pipeline
├── data/
│   └── synthetic/        # Data generation scripts
├── .github/
│   └── workflows/        # CI/CD pipelines
└── docker-compose.yml    # Local development setup
```

## Key Technologies

### Backend
- **Python 3.12** with FastAPI, SQLAlchemy 2.x async
- **MySQL 8** - Star schema for OLAP analytics
- **MongoDB 7** - Raw event storage
- **Neo4j 5** - Supply chain graph
- **Redis 7** - Caching and Celery broker
- **MinIO** - S3-compatible object storage

### ML/Optimization
- **XGBoost** - Demand forecasting with feature engineering
- **OR-Tools 9.8** - Vehicle routing optimization
- **Celery** - Distributed task execution

### Frontend
- **Next.js 14** - React framework with App Router
- **TypeScript** - Type safety
- **Tailwind CSS** - Utility-first styling
- **React Query** - Server state management
- **Recharts** - Data visualization
- **Glassmorphism** - Modern UI design with blur effects

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/login` | POST | JWT authentication |
| `/api/v1/auth/refresh` | POST | Refresh access token |
| `/api/v1/kpis/snapshot` | GET | Dashboard KPI summary |
| `/api/v1/kpis/trend` | GET | Time-series KPI trends |
| `/api/v1/forecast/demand` | GET | Demand forecast by SKU |
| `/api/v1/forecast/accuracy` | GET | Model accuracy metrics |
| `/api/v1/inventory/status` | GET | Current stock levels |
| `/api/v1/inventory/risk` | GET | Stockout risk analysis |
| `/api/v1/optimizer/routes` | POST | Run route optimization |
| `/api/v1/graph/lineage` | GET | Supply chain graph data |
| `/api/v1/sustainability/emissions` | GET | CO2 emissions metrics |
| `/api/v1/exports/{format}` | POST | Data export (Excel/PDF) |
| `/api/v1/admin/users` | CRUD | User management |

## Development

### Prerequisites
- Docker & Docker Compose
- Python 3.12+ (for local development)
- Node.js 20+ (for frontend)
- Java 21+ (for optimizer service)

### Environment Variables
Copy `.env.example` to `.env` and configure:

```bash
# Database
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=indigoglass
MYSQL_PASSWORD=your-secure-password
MYSQL_DATABASE=indigoglass

# Redis
REDIS_URL=redis://localhost:6379/0

# MongoDB
MONGODB_URL=mongodb://localhost:27017/indigoglass

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-neo4j-password

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# JWT
JWT_SECRET_KEY=your-256-bit-secret-key
JWT_ALGORITHM=HS256

# Optimizer
OPTIMIZER_URL=http://localhost:8081
```

### Running Tests

```bash
# API tests
cd services/api && pytest

# Frontend tests
cd apps/frontend && npm test

# Java optimizer tests
cd services/optimizer && mvn test
```

## Security

- JWT authentication with 15-min access tokens
- RBAC with Admin, Analyst, Viewer roles
- bcrypt password hashing (12 rounds)
- Rate limiting on all endpoints
- Request ID tracing for audit logs

## License

Proprietary - © 2024 IndigoGlass Inc.
