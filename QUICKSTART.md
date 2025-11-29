# Quick Start Guide - Local Development

This guide will help you start the entire Phase 2 Model Registry system locally.

## Prerequisites

- Docker and Docker Compose installed
- At least 4GB of free RAM
- Ports 5432, 8000, 5173, 9000, 9001 available

## Architecture

The system consists of:
1. **PostgreSQL** (port 5432) - Database
2. **MinIO** (ports 9000, 9001) - S3-compatible local storage
3. **FastAPI Backend** (port 8000) - REST API
4. **React Frontend** (port 5173) - Web UI

## Step 1: Start Everything with Docker Compose

```bash
# From the Phase-2 directory
docker-compose up --build
```

This will:
- ✅ Start PostgreSQL database
- ✅ Start MinIO (local S3) and create bucket
- ✅ Start FastAPI backend with auto-reload
- ✅ Start React frontend with hot reload
- ✅ Create default admin user: `ece30861defaultadminuser`

**Wait for all services to be healthy** (watch the logs):
- ✅ `phase2-postgres` - Ready to accept connections
- ✅ `phase2-minio` - MinIO started
- ✅ `phase2-api` - Application startup complete
- ✅ `phase2-frontend` - ready in Xms

## Step 2: Verify Services Are Running

Open these URLs in your browser:

### 1. Backend API Documentation
- **URL**: http://localhost:8000/docs
- **What you'll see**: Interactive Swagger UI with all API endpoints
- **Try**: Click on any endpoint to see request/response schemas

### 2. Health Check
- **URL**: http://localhost:8000/health
- **Expected response**: JSON with system metrics
```json
{
  "status": "healthy",
  "timestamp": "2025-11-23T...",
  "database": "connected",
  "storage": "connected",
  ...
}
```

### 3. Frontend Web UI
- **URL**: http://localhost:5173
- **What you'll see**: Model Registry interface
- **Features**:
  - Search artifacts
  - Ingest from HuggingFace
  - View model details

### 4. MinIO Console (S3 Storage)
- **URL**: http://localhost:9001
- **Login**:
  - Username: `minioadmin`
  - Password: `minioadmin123`
- **What you'll see**: S3 bucket `phase2-models` with uploaded packages

## Step 3: Test the API Manually

### Authenticate (Get Token)
```bash
curl -X POST http://localhost:8000/authenticate \
  -H "Content-Type: application/json" \
  -d '{
    "username": "ece30861defaultadminuser",
    "password": "correcthorsebatterystaple123(!__+@**(A;DROP TABLE packages"
  }'
```

**Expected response**:
```json
{
  "token": "your-auth-token-here",
  "user_id": "...",
  "username": "ece30861defaultadminuser",
  "expires_at": "..."
}
```

**Save the token** - you'll need it for all other requests.

### Search Packages (Empty at first)
```bash
curl -X POST http://localhost:8000/packages \
  -H "X-Authorization: your-auth-token-here" \
  -H "Content-Type: application/json" \
  -d '{"name": "", "regex": false}'
```

### Ingest a HuggingFace Model
```bash
curl -X POST http://localhost:8000/package/ingest-huggingface \
  -H "X-Authorization: your-auth-token-here" \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "bert-base-uncased",
    "version": "1.0.0"
  }'
```

This will:
1. Download the model from HuggingFace
2. Calculate all metrics (including Reproducibility, Reviewedness, Treescore)
3. Check if all metrics ≥ 0.5 (ingestibility threshold)
4. Upload to MinIO if ingestible
5. Store metadata in PostgreSQL

**Note**: This may take 1-2 minutes for the first model.

## Step 4: Explore the Frontend

1. Open http://localhost:5173
2. Click "Ingest from HuggingFace"
3. Enter model ID: `bert-base-uncased`
4. Click "Ingest Model"
5. Wait for completion
6. Go to "Search" to see the ingested model
7. Click "Show More" to see all metrics

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

### Restart Services
```bash
# Restart everything
docker-compose restart

# Restart just backend (to reload code changes)
docker-compose restart api

# Restart just frontend
docker-compose restart frontend
```

### Stop Everything
```bash
docker-compose down
```

### Reset Everything (including data)
```bash
# WARNING: This deletes all data!
docker-compose down -v
docker-compose up --build
```

### Access Database Directly
```bash
docker exec -it phase2-postgres psql -U phase2user -d phase2db

# Once inside psql:
\dt                    # List tables
SELECT * FROM users;   # View users
SELECT * FROM packages; # View packages
SELECT * FROM metrics;  # View metrics
\q                      # Quit
```

### Check MinIO Storage
```bash
# Open MinIO Console: http://localhost:9001
# Login: minioadmin / minioadmin123
# Navigate to: Buckets > phase2-models
```

## Troubleshooting

### Port Already in Use
If you see "port already allocated" errors:

```bash
# Check what's using the ports
sudo lsof -i :5432  # PostgreSQL
sudo lsof -i :8000  # Backend
sudo lsof -i :5173  # Frontend
sudo lsof -i :9000  # MinIO

# Kill the process or change ports in docker-compose.yml
```

### Backend Won't Start
```bash
# Check logs
docker-compose logs api

# Common issues:
# 1. Database not ready - wait 10 more seconds
# 2. Missing dependencies - rebuild: docker-compose build api
# 3. Code syntax error - check logs for Python traceback
```

### Frontend Won't Start
```bash
# Check logs
docker-compose logs frontend

# Common issues:
# 1. npm install failed - rebuild: docker-compose build frontend
# 2. Port 5173 in use - change port in docker-compose.yml
```

### Database Connection Failed
```bash
# Verify PostgreSQL is running
docker-compose ps postgres

# Check if it's healthy
docker-compose exec postgres pg_isready -U phase2user

# Reset database
docker-compose down -v
docker-compose up postgres
```

### MinIO Not Accessible
```bash
# Check MinIO status
docker-compose ps minio

# Verify bucket exists
docker-compose exec minio mc ls myminio/

# Recreate bucket
docker-compose up minio-setup
```

## Development Workflow

### Making Backend Changes
1. Edit files in `src/`
2. Backend auto-reloads (thanks to `--reload` flag)
3. Refresh http://localhost:8000/docs to see changes

### Making Frontend Changes
1. Edit files in `front-end/model-registry-frontend/src/`
2. Vite hot-reloads automatically
3. Browser refreshes automatically

### Running Tests
```bash
# Run tests inside Docker
docker-compose exec api pytest tests/ -v

# Or run locally if you have Python installed
PYTHONPATH=. pytest tests/ -v

# With coverage
docker-compose exec api pytest tests/ --cov=src --cov-report=html
```

## Next Steps

Once everything is running:

1. ✅ Test all API endpoints (see `/docs`)
2. ✅ Test frontend features
3. ✅ Ingest a few models
4. ✅ Test search and download
5. ✅ Check lineage graph: `/package/{id}/lineage`
6. ✅ Test license check: `/package/license-check`
7. ✅ View health metrics: `/health`
8. ✅ Build the HealthDashboard component

## Useful API Endpoints

- `POST /authenticate` - Get auth token
- `POST /package` - Upload package
- `POST /package/ingest-huggingface` - Ingest from HF
- `POST /packages` - Search/enumerate
- `GET /package/{id}` - Download (full or partial)
- `GET /package/{id}/lineage` - View lineage graph
- `GET /package/{id}/metadata` - View all metrics
- `POST /package/license-check` - Check license compatibility
- `GET /health` - System health metrics
- `GET /logs` - View application logs
- `DELETE /reset` - Reset to default state

---

**Need help?** Check the logs:
```bash
docker-compose logs -f api frontend
```
