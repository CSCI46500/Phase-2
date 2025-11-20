# Model Registry - Frontend & Backend Integration Setup

This guide explains how to connect the frontend and backend together and configure AWS credentials.

## Architecture Overview

- **Backend**: FastAPI (Python) - Port 8000
- **Frontend**: React + Vite (TypeScript) - Port 5173
- **Database**: PostgreSQL
- **Storage**: AWS S3
- **API Communication**: REST API with CORS enabled

## Prerequisites

1. Python 3.8+
2. Node.js 18+
3. PostgreSQL database
4. AWS Account with S3 access

## Backend Setup

### 1. Install Dependencies

```bash
cd /home/bperovic/software-engineering/Phase-2
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and fill in your AWS credentials:

```env
# Database Configuration
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/model_registry

# AWS S3 Configuration - REPLACE THESE WITH YOUR ACTUAL AWS CREDENTIALS
S3_BUCKET_NAME=model-registry-packages
S3_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-actual-aws-access-key-here
AWS_SECRET_ACCESS_KEY=your-actual-aws-secret-key-here

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Authentication
TOKEN_EXPIRY_DAYS=30
DEFAULT_API_CALLS=1000
SECRET_KEY=change-this-to-a-random-secret-key-in-production

# Default Admin Credentials (CHANGE IN PRODUCTION!)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123

# Anthropic API Key (for metrics evaluation)
ANTHROPIC_API_KEY=your-anthropic-api-key-here
```

### 3. Set Up Database

Make sure PostgreSQL is running, then create the database:

```bash
createdb model_registry
```

The application will automatically initialize the database schema on first run.

### 4. Start Backend Server

```bash
cd /home/bperovic/software-engineering/Phase-2
python -m src.api.main
```

Or using uvicorn directly:

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend should now be running at: **http://localhost:8000**

API documentation available at: **http://localhost:8000/docs**

## Frontend Setup

### 1. Install Dependencies

```bash
cd /home/bperovic/software-engineering/Phase-2/front-end/model-registry-frontend
npm install
```

### 2. Configure Environment Variables

Create a `.env` file in the frontend directory:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Backend API URL
VITE_API_URL=http://localhost:8000

# Default credentials (for development)
VITE_DEFAULT_USERNAME=admin
VITE_DEFAULT_PASSWORD=admin123
```

### 3. Start Frontend Development Server

```bash
npm run dev
```

The frontend should now be running at: **http://localhost:5173**

## Integration Details

### CORS Configuration

The backend has been configured with CORS middleware to allow requests from the frontend:

```python
# src/api/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative dev port
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### API Endpoints Used by Frontend

#### Authentication
- `POST /authenticate` - Login and get auth token

#### Package Management
- `POST /package/ingest-huggingface` - Ingest HuggingFace model
- `POST /packages` - Search packages (supports name, version, regex)
- `GET /package/{id}/metadata` - Get package details
- `GET /package/{id}` - Download package (returns presigned S3 URL)

#### Health Check
- `GET /health` - Check API and service health

### Frontend API Service

The frontend API service (`src/services/api.ts`) automatically:
- Handles authentication tokens via `X-Authorization` header
- Transforms backend responses to frontend format
- Provides error handling and retry logic
- Maps backend metric names to frontend expectations

## AWS S3 Setup

### 1. Create S3 Bucket

1. Log into AWS Console
2. Navigate to S3
3. Create a new bucket named `model-registry-packages` (or your preferred name)
4. Region: `us-east-1` (or your preferred region)
5. Keep default settings for now

### 2. Configure IAM User

Create an IAM user with S3 permissions:

1. Navigate to IAM → Users → Create User
2. Name: `model-registry-api`
3. Attach policy: `AmazonS3FullAccess` (or create a custom policy for your bucket)
4. Create access key
5. Copy the Access Key ID and Secret Access Key to your `.env` file

### 3. Bucket Policy (Optional but Recommended)

For better security, create a custom policy limited to your specific bucket:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::model-registry-packages",
        "arn:aws:s3:::model-registry-packages/*"
      ]
    }
  ]
}
```

## Testing the Integration

### 1. Start Both Servers

Terminal 1 (Backend):
```bash
cd /home/bperovic/software-engineering/Phase-2
python -m src.api.main
```

Terminal 2 (Frontend):
```bash
cd /home/bperovic/software-engineering/Phase-2/front-end/model-registry-frontend
npm run dev
```

### 2. Test Authentication

The frontend automatically uses the default admin credentials. You should be able to access all features without manual login.

### 3. Test Package Ingestion

1. Open http://localhost:5173
2. Navigate to "Ingest Package"
3. Enter a HuggingFace model ID (e.g., `bert-base-uncased`)
4. Click "Ingest Package"
5. The backend will:
   - Download the model from HuggingFace
   - Run metrics evaluation
   - Upload to S3
   - Store metadata in PostgreSQL

### 4. Test Package Search

1. Navigate to "Search Artifacts"
2. Try different search types:
   - All packages
   - Search by name/regex
   - Search by ID

## Troubleshooting

### CORS Errors

If you see CORS errors:
- Ensure backend is running on port 8000
- Ensure frontend is running on port 5173
- Check browser console for exact error
- Verify CORS middleware is configured in `src/api/main.py`

### Authentication Errors

If you get 401 Unauthorized:
- Check that you're using the correct credentials in `.env`
- The default admin user is created automatically on first startup
- Try restarting the backend server

### S3 Upload Errors

If package upload fails:
- Verify AWS credentials in `.env`
- Check S3 bucket exists and name matches
- Verify IAM user has S3 permissions
- Check AWS region matches

### Database Errors

If you see database errors:
- Ensure PostgreSQL is running
- Verify database exists: `psql -l`
- Check DATABASE_URL in `.env`
- Try recreating database: `dropdb model_registry && createdb model_registry`

## Production Deployment Checklist

Before deploying to production:

- [ ] Change `ADMIN_PASSWORD` to a strong password
- [ ] Generate a secure `SECRET_KEY`
- [ ] Use production database (not localhost)
- [ ] Update CORS origins to your production domain
- [ ] Use environment-specific S3 buckets
- [ ] Enable HTTPS/SSL
- [ ] Set up proper logging and monitoring
- [ ] Configure rate limiting
- [ ] Review and restrict IAM permissions
- [ ] Set up database backups
- [ ] Configure S3 lifecycle policies

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## File Structure

```
Phase-2/
├── src/
│   ├── api/
│   │   └── main.py          # FastAPI app with CORS
│   ├── core/
│   │   ├── config.py        # Environment config
│   │   └── ...
│   └── services/
│       ├── s3_service.py    # S3 integration
│       └── ...
├── front-end/
│   └── model-registry-frontend/
│       ├── src/
│       │   ├── services/
│       │   │   └── api.ts   # API client
│       │   └── components/
│       └── .env             # Frontend config
├── .env                     # Backend config
└── .env.example             # Backend config template
```
