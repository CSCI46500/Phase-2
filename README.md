# Phase 2 Model Registry

A comprehensive model and dataset registry with advanced metrics evaluation and observability features.

## Overview

This project implements a model registry system that provides:
- Model and dataset package management with S3 storage
- Advanced metrics evaluation (11 metrics including license, quality, reproducibility)
- Component-based downloads (weights, datasets, code)
- License compatibility checking
- Package lineage tracking with TreeScore metric
- Comprehensive observability and monitoring
- User authentication and authorization

## Quick Start with Docker

### Prerequisites
- Docker Desktop (with Docker Compose V2)
- 4GB+ RAM available
- 10GB+ disk space

### Starting the Application

1. Clone the repository and navigate to the project directory:
```bash
cd /path/to/Phase-2
```

2. Start all services using the provided script:
```bash
./docker-start.sh
```

Or manually with docker compose:
```bash
docker compose up -d
```

3. Wait for all services to be healthy (30-60 seconds):
```bash
docker compose ps
```

4. Access the application:
- **API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **MinIO Console**: http://localhost:9001 (minioadmin / minioadmin123)

### Default Admin Credentials

```
Username: ece30861defaultadminuser
Password: correcthorsebatterystaple123(!__+@**(A;DROP TABLE packages
```

### Stopping the Application

```bash
docker compose down
```

To also remove volumes (database data, S3 objects):
```bash
docker compose down -v
```

## Architecture

### Services

**API (FastAPI)**
- Port: 8000
- Handles all REST API requests
- Automatic database initialization
- Default admin user creation on startup

**PostgreSQL Database**
- Port: 5432 (internal)
- Stores packages, users, metrics, lineage
- Automatic schema creation via init scripts

**MinIO (S3-Compatible Storage)**
- API Port: 9000
- Console Port: 9001
- Stores model/dataset package files
- Automatic bucket creation

**Frontend (Nginx)**
- Port: 80
- Serves web interface for package browsing

## Environment Configuration

Environment variables are configured in `.env.docker` for local development:

```bash
# PostgreSQL
POSTGRES_USER=phase2user
POSTGRES_PASSWORD=phase2password
POSTGRES_DB=phase2db

# MinIO (S3)
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin123
S3_BUCKET_NAME=phase2-models

# API
API_HOST=0.0.0.0
API_PORT=8000
ENVIRONMENT=local  # Use 'local' for Docker, 'aws' for AWS deployment
```

## API Usage

### Authentication

Get an API token:
```bash
curl -X POST http://localhost:8000/authenticate \
  -H "Content-Type: application/json" \
  -d '{"username":"ece30861defaultadminuser","password":"correcthorsebatterystaple123(!__+@**(A;DROP TABLE packages"}'
```

Response:
```json
{
  "token": "your-token-here",
  "calls_remaining": 1000
}
```

Use the token in subsequent requests:
```bash
curl -H "X-Authorization: your-token-here" http://localhost:8000/packages
```

### Key Endpoints

See [docs/API_README.md](docs/API_README.md) for complete API documentation.

**Package Management:**
- `POST /package` - Upload package
- `GET /package/{id}` - Download package (supports component downloads)
- `GET /packages` - Search packages
- `DELETE /package/{id}` - Delete package (admin)

**Metrics & Evaluation:**
- `GET /package/{id}/rate` - Get package metrics
- `POST /package/license-check` - Check license compatibility

**Observability (Sprint 3):**
- `GET /health` - Health check (add `?detailed=true` for metrics)
- `GET /logs` - Application logs with filtering (admin)

**User Management:**
- `POST /authenticate` - Login
- `POST /register` - Create user (admin)
- `PUT /user/{id}/permissions` - Update permissions (admin)

### Component Downloads

Download specific components of a package:

```bash
# Download only model weights
curl -H "X-Authorization: token" \
  "http://localhost:8000/package/{id}?weights=true" -o weights.zip

# Download weights and code (no datasets)
curl -H "X-Authorization: token" \
  "http://localhost:8000/package/{id}?weights=true&code=true" -o package.zip

# Download full package
curl -H "X-Authorization: token" \
  "http://localhost:8000/package/{id}?full=true" -o full_package.zip
```

## Observability Features

### Enhanced Health Check

Get detailed system metrics:
```bash
curl "http://localhost:8000/health?detailed=true" | jq .
```

Returns:
- Request counts (total, successful, failed)
- Error rate percentage
- Response times (avg, p95, p99)
- System resources (CPU, memory, disk)
- Top endpoints by request count

### Logs Endpoint

View application logs (admin only):
```bash
curl -H "X-Authorization: admin-token" \
  "http://localhost:8000/logs?level=ERROR&limit=50" | jq .
```

Query parameters:
- `level`: Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `start_time`: ISO format datetime
- `end_time`: ISO format datetime
- `offset`: Pagination offset
- `limit`: Max logs to return (max: 1000)

## Metrics Evaluation

The system evaluates packages using 11 metrics:

1. **License** (15%) - Legal compliance
2. **Code Quality** (11%) - Maintainability
3. **Dataset Quality** (11%) - Data quality
4. **Reproducibility** (10%) - Can the model run?
5. **Ramp-up Time** (9%) - Ease of getting started
6. **Bus Factor** (9%) - Team maintainability risk
7. **Reviewedness** (9%) - Code review quality
8. **Dataset & Code Score** (9%) - Availability
9. **Size Score** (7%) - Storage considerations
10. **Performance Claims** (7%) - Validity of claims
11. **TreeScore** (3%) - Lineage quality

Net score is calculated as a weighted sum of all metrics.

## Development

### Project Structure

```
Phase-2/
├── src/
│   ├── api/          # FastAPI application
│   ├── core/         # Database models, config, auth
│   ├── services/     # Business logic (S3, metrics, monitoring)
│   ├── utils/        # Utilities (calculators, logger)
│   └── crud.py       # Database operations
├── frontend/         # Web interface
├── docs/            # Documentation
├── docker/          # Docker configuration
│   └── init/        # Database init scripts
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

### Running Tests

```bash
docker compose exec api pytest
```

With coverage:
```bash
docker compose exec api pytest --cov=src tests/
```

### Viewing Logs

```bash
# API logs
docker compose logs -f api

# Database logs
docker compose logs -f db

# MinIO logs
docker compose logs -f minio
```

### Database Access

Connect to PostgreSQL:
```bash
docker compose exec db psql -U phase2user -d phase2db
```

Common queries:
```sql
-- View all packages
SELECT id, name, version, upload_date FROM packages;

-- View metrics for a package
SELECT * FROM metrics WHERE package_id = 'uuid-here';

-- View system metrics
SELECT * FROM system_metrics ORDER BY timestamp DESC LIMIT 10;
```

## Troubleshooting

### Services won't start
```bash
# Check service status
docker compose ps

# View logs
docker compose logs api

# Restart services
docker compose restart
```

### Database connection errors
```bash
# Ensure database is healthy
docker compose ps db

# Recreate database
docker compose down -v
docker compose up -d
```

### MinIO connection errors
```bash
# Check MinIO is running
docker compose ps minio

# Access MinIO console
open http://localhost:9001
```

### Port conflicts
If ports 8000, 5432, or 9000-9001 are in use, modify `docker-compose.yml` to use different ports.

## Additional Documentation

- [API Reference](docs/API_README.md) - Complete API documentation
- [Local Setup Guide](docs/LOCAL_SETUP.md) - Detailed local development guide
- [CRUD Implementation Plan](docs/CRUD_IMPLEMENTATION_PLAN.md) - Database schema and API design

## License

ECE 30861 - Software Engineering Course Project
