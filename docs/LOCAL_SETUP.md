# Local Docker Development Setup

This guide explains how to run the Phase 2 Model Registry locally using Docker Compose.

## Prerequisites

- Docker Desktop (Mac/Windows) or Docker Engine + Docker Compose (Linux)
- At least 4GB RAM available for Docker
- 10GB free disk space

## Quick Start

### 1. Clone and Navigate

```bash
cd /path/to/Phase-2
```

### 2. Configure Environment (Optional)

The `.env.docker` file contains default settings for local development. You can customize:

```bash
# Edit if needed
nano .env.docker
```

**Important**: Add your API keys for full functionality:
- `ANTHROPIC_API_KEY` - For Claude AI metrics (ramp-up time analysis)
- `GITHUB_TOKEN` - For GitHub API rate limit increases

### 3. Start All Services

```bash
./docker-start.sh
```

Or manually:

```bash
docker-compose up -d
```

### 4. Verify Services

Check that all services are running:

```bash
docker-compose ps
```

Expected output:
```
NAME                COMMAND                  SERVICE      STATUS
phase2-api          "uvicorn src.api.mai…"   api          Up (healthy)
phase2-frontend     "npm run dev -- --ho…"   frontend     Up
phase2-minio        "minio server /data …"   minio        Up (healthy)
phase2-postgres     "docker-entrypoint.s…"   postgres     Up (healthy)
```

### 5. Access the Application

- **API**: http://localhost:8000
- **API Documentation (Swagger)**: http://localhost:8000/docs
- **Frontend**: http://localhost:5173
- **MinIO Console**: http://localhost:9001
  - Username: `minioadmin`
  - Password: `minioadmin123`

## Architecture

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │
       ├──────────────┐
       │              │
       v              v
┌─────────────┐  ┌──────────┐
│  Frontend   │  │   API    │
│  (React)    │  │ (FastAPI)│
│ Port 5173   │  │ Port 8000│
└─────────────┘  └────┬─────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        v             v             v
  ┌──────────┐  ┌─────────┐  ┌──────────┐
  │PostgreSQL│  │  MinIO  │  │ External │
  │ Port 5432│  │Port 9000│  │   APIs   │
  └──────────┘  └─────────┘  └──────────┘
```

## Service Details

### PostgreSQL Database
- **Host**: `localhost:5432` (from host) or `postgres:5432` (from containers)
- **Database**: `phase2db`
- **Username**: `phase2user`
- **Password**: `phase2password`
- **Data persistence**: `postgres_data` Docker volume

### MinIO (S3-compatible storage)
- **API Endpoint**: `http://localhost:9000`
- **Console**: `http://localhost:9001`
- **Bucket**: `phase2-models`
- **Access Key**: `minioadmin`
- **Secret Key**: `minioadmin123`
- **Data persistence**: `minio_data` Docker volume

### FastAPI Backend
- **Port**: 8000
- **OpenAPI Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **Hot reload**: Enabled (changes to `src/` auto-reload)

### React Frontend
- **Port**: 5173
- **Hot reload**: Enabled (changes to `src/` auto-reload)

## Default Admin User

As per ACME requirements, the system has a default admin user:

- **Username**: `ece30861defaultadminuser`
- **Password**: `correcthorsebatterystaple123(!__+@**(A;DROP TABLE packages`

## Common Commands

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f frontend
docker-compose logs -f postgres
docker-compose logs -f minio
```

### Restart a Service

```bash
docker-compose restart api
```

### Rebuild After Code Changes

```bash
# Rebuild specific service
docker-compose up -d --build api

# Rebuild all
docker-compose up -d --build
```

### Stop Services

```bash
# Stop but keep data
docker-compose down

# Stop and remove volumes (fresh start)
docker-compose down -v
```

### Access Container Shell

```bash
# API container
docker exec -it phase2-api /bin/bash

# Database
docker exec -it phase2-postgres psql -U phase2user -d phase2db
```

### Run Tests

```bash
# From host
docker-compose exec api pytest

# With coverage
docker-compose exec api pytest --cov=src --cov-report=html
```

## Database Management

### View Tables

```bash
docker exec -it phase2-postgres psql -U phase2user -d phase2db -c "\dt"
```

### Reset Database

```bash
# Stop services
docker-compose down

# Remove database volume
docker volume rm phase2_postgres_data

# Restart (fresh database)
docker-compose up -d
```

### Manual SQL Query

```bash
docker exec -it phase2-postgres psql -U phase2user -d phase2db
```

Then run SQL:
```sql
SELECT * FROM packages LIMIT 10;
SELECT COUNT(*) FROM users;
```

## Troubleshooting

### Port Already in Use

If ports 5432, 8000, 5173, or 9000 are in use:

1. Find the conflicting process:
   ```bash
   lsof -i :8000  # Mac/Linux
   netstat -ano | findstr :8000  # Windows
   ```

2. Stop it or change ports in `docker-compose.yml`:
   ```yaml
   ports:
     - "8001:8000"  # Use 8001 instead
   ```

### Services Not Healthy

Check logs:
```bash
docker-compose logs api
```

Common issues:
- Database not ready: Wait 30 seconds and check `docker-compose ps`
- MinIO bucket creation failed: Check `docker-compose logs minio-setup`

### API Can't Connect to Database

Ensure `DATABASE_URL` in docker-compose.yml uses `postgres` hostname:
```
postgresql://phase2user:phase2password@postgres:5432/phase2db
```

### MinIO Connection Error

Check that `S3_ENDPOINT_URL=http://minio:9000` in API environment.

### Frontend Can't Reach API

Check CORS settings in `src/api/main.py`. For Docker, ensure:
```python
allow_origins=["http://localhost:5173"]
```

## Development Workflow

### 1. Make Code Changes

Edit files in `src/` or `front-end/` - changes auto-reload.

### 2. Run Tests

```bash
docker-compose exec api pytest tests/
```

### 3. Check Coverage

```bash
docker-compose exec api coverage run -m pytest
docker-compose exec api coverage report
```

### 4. View Logs

```bash
docker-compose logs -f api
```

### 5. Test API Endpoints

Use Swagger UI at http://localhost:8000/docs or curl:

```bash
# Health check
curl http://localhost:8000/health

# Authenticate (get token)
curl -X POST http://localhost:8000/authenticate \
  -H "Content-Type: application/json" \
  -d '{"username":"ece30861defaultadminuser","password":"correcthorsebatterystaple123(!__+@**(A;DROP TABLE packages"}'
```

## Switching to AWS

To deploy to AWS instead of local Docker:

1. Update environment variables to use AWS services
2. Set `ENVIRONMENT=production`
3. Remove `S3_ENDPOINT_URL` (use real S3)
4. Update `DATABASE_URL` to AWS RDS endpoint
5. Use AWS credentials instead of MinIO keys

See `docs/DEPLOYMENT.md` for AWS setup guide.

## Clean Up

### Remove Everything

```bash
# Stop and remove containers, networks, volumes
docker-compose down -v

# Remove Docker images
docker-compose down --rmi all -v
```

### Free Disk Space

```bash
docker system prune -a --volumes
```

**Warning**: This removes all unused Docker data system-wide!

## Next Steps

- Read `docs/API_README.md` for API endpoint documentation
- See `docs/TESTING_GUIDE.md` for testing procedures
- Check `docs/SECURITY.md` for security best practices

---

**Need Help?**
- Check logs: `docker-compose logs -f`
- Verify services: `docker-compose ps`
- Restart: `docker-compose restart`
