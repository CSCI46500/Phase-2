
# Model Registry API - CRUD Implementation

This API implements comprehensive CRUD operations for a Model Registry system, based on the `CRUD_IMPLEMENTATION_PLAN.md`.

## Features

- **Full CRUD Operations**: Create, Read, Update, Delete for models/packages
- **Authentication & Authorization**: Token-based auth with permission system
- **Metrics Evaluation**: Automatic evaluation using existing MetricsEvaluator
- **S3 Storage**: Package storage in AWS S3 with presigned URLs
- **PostgreSQL Database**: Robust data persistence with relationships
- **Search & Discovery**: Full-text search and regex pattern matching
- **Package Lineage**: Track package relationships and dependencies
- **Rating System**: User ratings and reviews
- **Download Tracking**: Complete audit trail of downloads
- **Package Confusion Detection**: Security feature to detect similar package names

## Architecture

```
User/Client → FastAPI API → PostgreSQL (RDS)
                         ↓
                      AWS S3
```

### Components

- **FastAPI**: REST API framework
- **SQLAlchemy**: ORM for database operations
- **PostgreSQL**: Relational database for metadata
- **AWS S3**: Object storage for package files
- **Boto3**: AWS SDK for S3 operations
- **bcrypt**: Password hashing

## Quick Start

### 1. Install Dependencies

```bash
./run install
```

or

```bash
pip install -r dependencies.txt
```

### 2. Set Up Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Edit `.env` with your settings:
- Database URL (PostgreSQL)
- AWS credentials (for S3)
- API configuration
- Admin credentials

### 3. Set Up PostgreSQL Database

Make sure PostgreSQL is running and create the database:

```bash
createdb model_registry
```

Or using psql:

```sql
CREATE DATABASE model_registry;
```

### 4. Initialize Database

```bash
python3 init_db.py
```

This creates all tables and the default admin user.

### 5. Start the API Server

```bash
chmod +x run_api.sh
./run_api.sh
```

Or directly:

```bash
python3 -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`

### 6. Access API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Authentication

#### POST `/authenticate`
Login and get API token.

**Request:**
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**Response:**
```json
{
  "token": "your-api-token",
  "calls_remaining": 1000
}
```

#### POST `/user/register` (Admin Only)
Register a new user.

**Headers:**
```
X-Authorization: <admin-token>
```

**Request:**
```json
{
  "username": "newuser",
  "password": "password123",
  "permissions": ["upload", "download", "search"]
}
```

### CREATE Operations

#### POST `/package`
Upload and evaluate a package.

**Headers:**
```
X-Authorization: <token>
```

**Form Data:**
- `file`: Package ZIP file
- `name`: Package name
- `version`: Package version
- `description`: Optional description
- `model_url`: HuggingFace model URL
- `dataset_url`: HuggingFace dataset URL
- `code_url`: GitHub repository URL

**Response:**
```json
{
  "package_id": "uuid",
  "name": "my-model",
  "version": "1.0.0",
  "s3_path": "s3://bucket/my-model/1.0.0/package.zip",
  "net_score": 0.85,
  "message": "Package uploaded and evaluated successfully"
}
```

#### PUT `/package/{package_id}/rate`
Rate a package (1-5 stars).

**Request:**
```json
{
  "score": 5
}
```

### READ Operations

#### GET `/package/{package_id}`
Download a package (returns presigned S3 URL).

**Query Parameters (Sprint 2 - Component Downloads):**
- `weights`: boolean - Include model weights
- `datasets`: boolean - Include datasets
- `code`: boolean - Include code/scripts
- `full`: boolean - Download complete package (overrides other params)

If no parameters are specified, returns the full package by default.

**Examples:**
```bash
# Download only weights
GET /package/{id}?weights=true

# Download weights and code (no datasets)
GET /package/{id}?weights=true&code=true

# Download full package explicitly
GET /package/{id}?full=true
```

**Response:**
```json
{
  "package_id": "uuid",
  "name": "my-model",
  "version": "1.0.0",
  "download_url": "https://s3.amazonaws.com/...",
  "expires_in_seconds": 300,
  "components_included": ["weights", "code"]
}
```

#### POST `/packages`
Search/enumerate packages.

**Request:** (Array of query objects)
```json
[
  {
    "name": "bert",
    "version": "1.0.0",
    "regex": "^bert.*"
  }
]
```

**Empty array returns all packages:**
```json
[]
```

**Query Parameters:**
- `offset`: Pagination offset (default: 0)
- `limit`: Results per page (default: 50, max: 100)

**Response:**
```json
{
  "packages": [
    {
      "id": "uuid",
      "name": "bert-base",
      "version": "1.0.0",
      "description": "BERT base model",
      "license": "apache-2.0",
      "net_score": 0.85,
      "upload_date": "2025-01-15T10:30:00"
    }
  ],
  "total": 42,
  "offset": 0,
  "limit": 50
}
```

#### GET `/package/{package_id}/metadata`
Get detailed package metadata.

**Response:**
```json
{
  "id": "uuid",
  "name": "my-model",
  "version": "1.0.0",
  "description": "My awesome model",
  "license": "mit",
  "size_bytes": 1073741824,
  "uploader_id": "uuid",
  "upload_date": "2025-01-15T10:30:00",
  "metrics": {
    "net_score": 0.85,
    "bus_factor": 0.8,
    "ramp_up": 0.9,
    "code_quality": 0.7,
    "dataset_quality": 0.85
  },
  "average_rating": 4.5
}
```

#### GET `/package/{package_id}/lineage`
Get package lineage tree (parent-child relationships).

**Response:**
```json
{
  "package_id": "uuid",
  "lineage": [
    {
      "id": "uuid-1",
      "name": "model-v3",
      "version": "3.0.0",
      "depth": 0
    },
    {
      "id": "uuid-2",
      "name": "model-v2",
      "version": "2.0.0",
      "depth": 1
    }
  ]
}
```

#### POST `/package/license-check` (Sprint 2)
Check license compatibility between a GitHub repository and a model package.

**Request:**
```json
{
  "github_url": "https://github.com/user/my-project",
  "model_id": "uuid-of-model-package"
}
```

**Response - Compatible:**
```json
{
  "compatible": true,
  "github_license": "MIT",
  "model_license": "Apache-2.0",
  "reason": "MIT is compatible with Apache-2.0 licenses",
  "warnings": null
}
```

**Response - Incompatible:**
```json
{
  "compatible": false,
  "github_license": "GPL-3.0",
  "model_license": "MIT",
  "reason": "GPL-3.0 is not compatible with MIT license. GPL requires derivative works to use GPL.",
  "warnings": ["Consider using a GPL-compatible license or choosing a different model"]
}
```

**Supported Licenses:**
- MIT
- Apache-2.0
- BSD-2-Clause, BSD-3-Clause
- GPL-2.0, GPL-3.0
- LGPL-2.1, LGPL-3.0
- MPL-2.0
- ISC
- CC-BY-4.0, CC-BY-SA-4.0
- Unlicense
- Proprietary

The endpoint uses ModelGo-inspired compatibility rules to determine if the GitHub project license is compatible with the model's license.

### UPDATE Operations

#### PUT `/user/{user_id}/permissions` (Admin Only)
Update user permissions.

**Request:**
```json
{
  "permissions": ["upload", "download", "search"]
}
```

### DELETE Operations

#### DELETE `/package/{package_id}` (Admin Only)
Delete a package (removes from S3 and database).

#### DELETE `/user/{user_id}`
Delete a user. Users can delete themselves; admins can delete anyone.

#### DELETE `/reset` (Admin Only)
Reset entire system (deletes all packages and users except default admin).

### Observability & Monitoring (Sprint 3)

#### GET `/health`
Check system health with optional detailed performance metrics.

**Query Parameters:**
- `detailed`: boolean - Include detailed performance metrics (default: false)

**Basic Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-24T00:14:54.071484",
  "components": {
    "database": "healthy",
    "s3": "healthy"
  }
}
```

**Detailed Response (`?detailed=true`):**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-24T00:14:54.071484",
  "components": {
    "database": "healthy",
    "s3": "healthy"
  },
  "metrics": {
    "total_requests": 150,
    "successful_requests": 142,
    "failed_requests": 8,
    "error_rate_percent": 5.33,
    "avg_response_time_ms": 124.5,
    "p95_response_time_ms": 450.2,
    "p99_response_time_ms": 890.5,
    "cpu_percent": 12.3,
    "memory_percent": 45.8,
    "disk_percent": 23.1
  },
  "top_endpoints": [
    {
      "endpoint": "POST /package",
      "count": 45,
      "errors": 2,
      "avg_response_ms": 450.5
    },
    {
      "endpoint": "GET /packages",
      "count": 38,
      "errors": 0,
      "avg_response_ms": 45.2
    }
  ]
}
```

**Metrics Details:**
- `total_requests`: Total API requests since startup
- `successful_requests`: Requests with 2xx/3xx status
- `failed_requests`: Requests with 4xx/5xx status
- `error_rate_percent`: Percentage of failed requests
- `avg_response_time_ms`: Average response time
- `p95_response_time_ms`: 95th percentile response time
- `p99_response_time_ms`: 99th percentile response time
- `cpu_percent`: Current CPU usage
- `memory_percent`: Current memory usage
- `disk_percent`: Current disk usage
- `top_endpoints`: Top 5 endpoints by request count

#### GET `/logs` (Admin Only)
Get application logs with filtering capabilities.

**Headers:**
```
X-Authorization: <admin-token>
```

**Query Parameters:**
- `level`: Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `start_time`: ISO format datetime for range start (e.g., "2025-11-24T00:00:00")
- `end_time`: ISO format datetime for range end
- `offset`: Pagination offset (default: 0)
- `limit`: Max logs to return (default: 100, max: 1000)

**Examples:**
```bash
# Get recent error logs
GET /logs?level=ERROR&limit=50

# Get logs in time range
GET /logs?start_time=2025-11-24T00:00:00&end_time=2025-11-24T23:59:59

# Paginate through logs
GET /logs?offset=100&limit=50
```

**Response:**
```json
{
  "logs": [
    {
      "timestamp": "2025-11-24T12:34:56.789000",
      "endpoint": "POST /package",
      "method": "POST",
      "status_code": 500,
      "error": "S3 connection timeout"
    },
    {
      "timestamp": "2025-11-24T12:30:15.123000",
      "endpoint": "GET /package/uuid",
      "method": "GET",
      "status_code": 404,
      "error": "Package not found"
    }
  ],
  "total": 2,
  "offset": 0,
  "limit": 100,
  "note": "Showing recent request errors. For full logs, check application log files."
}
```

**Note:** The `/logs` endpoint returns recent errors tracked by the metrics collector. For comprehensive log analysis, access the application log files directly.

## Permission System

The API uses a role-based permission system:

- **search**: Can search and view packages
- **download**: Can download packages
- **upload**: Can upload new packages
- **admin**: Full administrative access

Admins automatically have all permissions.

## Database Schema

The system uses 9 PostgreSQL tables:

1. **users**: User accounts and permissions
2. **tokens**: API tokens with usage tracking
3. **packages**: Package metadata
4. **metrics**: Evaluation metrics for packages (11 metrics including Phase 2 additions)
5. **lineage**: Package relationships and dependencies
6. **ratings**: User ratings
7. **download_history**: Download audit trail
8. **package_confusion_audit**: Security audit logs
9. **system_metrics** (Sprint 3): Observability metrics (requests, response times, errors, system resources)

See `src/core/models.py` for complete schema details.

## Integration with Existing CLI

The API seamlessly integrates with your existing metrics evaluation system:

- Uses `MetricsEvaluator` for package evaluation
- Uses `DataFetcher` for fetching metadata
- Preserves all existing metric calculators
- Compatible with existing CLI tools

You can still use the CLI for batch evaluation:

```bash
./run sample_input
```

And now also use the API for CRUD operations!

## Security Features

1. **Token-based Authentication**: Secure API access
2. **Permission System**: Fine-grained access control
3. **Password Hashing**: bcrypt with salt
4. **API Call Limits**: Prevent abuse (1000 calls per token by default)
5. **Token Expiry**: Tokens expire after 30 days
6. **Download Tracking**: Complete audit trail
7. **Package Confusion Detection**: Detect similar package names

## Example Workflow

### 1. Authenticate
```bash
curl -X POST http://localhost:8000/authenticate \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

### 2. Upload a Package
```bash
curl -X POST http://localhost:8000/package \
  -H "X-Authorization: YOUR_TOKEN" \
  -F "file=@model.zip" \
  -F "name=my-model" \
  -F "version=1.0.0" \
  -F "model_url=https://huggingface.co/bert-base" \
  -F "code_url=https://github.com/user/repo"
```

### 3. Search Packages
```bash
curl -X POST http://localhost:8000/packages \
  -H "X-Authorization: YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '[{"name": "bert"}]'
```

### 4. Download Package
```bash
curl -X GET http://localhost:8000/package/{package_id} \
  -H "X-Authorization: YOUR_TOKEN"
```

### 5. Rate Package
```bash
curl -X PUT http://localhost:8000/package/{package_id}/rate \
  -H "X-Authorization: YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"score": 5}'
```

## Production Deployment

For production deployment:

1. **Change default credentials** in `.env`
2. **Use production database** (AWS RDS recommended)
3. **Configure S3 bucket** with proper IAM roles
4. **Enable HTTPS** (use reverse proxy like nginx)
5. **Set up monitoring** (CloudWatch, Datadog, etc.)
6. **Use environment-specific configs**
7. **Enable database backups**
8. **Implement rate limiting** at API Gateway level

See `CRUD_IMPLEMENTATION_PLAN.md` for AWS deployment architecture.

## Troubleshooting

### Database Connection Issues
```bash
# Check PostgreSQL is running
psql -U postgres -l

# Test connection
psql -U postgres -d model_registry
```

### S3 Connection Issues
```bash
# Verify AWS credentials
aws s3 ls s3://model-registry-packages

# Check IAM permissions
```

### Import Errors
```bash
# Reinstall dependencies
pip install -r dependencies.txt
```

## Files Created

- `api.py` - Main FastAPI application
- `models.py` - SQLAlchemy database models
- `database.py` - Database configuration
- `auth.py` - Authentication and authorization
- `crud.py` - CRUD operations
- `s3_helper.py` - S3 integration
- `config.py` - Configuration management
- `init_db.py` - Database initialization script
- `run_api.sh` - API server startup script

## Next Steps

1. Test all endpoints using Swagger UI
2. Set up production database (AWS RDS)
3. Configure S3 bucket and IAM roles
4. Implement additional metrics from Phase 2
5. Add frontend integration
6. Set up CI/CD pipeline (see `.github/workflows/`)

## Support

For issues and questions, refer to:
- `CRUD_IMPLEMENTATION_PLAN.md` - Complete implementation details
- FastAPI documentation: https://fastapi.tiangolo.com/
- SQLAlchemy documentation: https://docs.sqlalchemy.org/