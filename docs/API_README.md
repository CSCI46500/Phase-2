
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

**Response:**
```json
{
  "package_id": "uuid",
  "name": "my-model",
  "version": "1.0.0",
  "download_url": "https://s3.amazonaws.com/...",
  "expires_in_seconds": 300
}
```

#### POST `/packages`
Search/enumerate packages.

**Request:**
```json
{
  "name": "bert",
  "version": "1.0.0",
  "regex": "^bert.*"
}
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

### Health Check

#### GET `/health`
Check system health.

**Response:**
```json
{
  "status": "healthy",
  "components": {
    "database": "healthy",
    "s3": "healthy"
  }
}
```

## Permission System

The API uses a role-based permission system:

- **search**: Can search and view packages
- **download**: Can download packages
- **upload**: Can upload new packages
- **admin**: Full administrative access

Admins automatically have all permissions.

## Database Schema

The system uses 8 PostgreSQL tables:

1. **users**: User accounts and permissions
2. **tokens**: API tokens with usage tracking
3. **packages**: Package metadata
4. **metrics**: Evaluation metrics for packages
5. **lineage**: Package relationships
6. **ratings**: User ratings
7. **download_history**: Download audit trail
8. **package_confusion_audit**: Security audit logs

See `models.py` for complete schema details.

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
  -d '{"name": "bert"}'
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