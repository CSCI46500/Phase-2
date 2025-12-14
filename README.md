# ECE 461 - Trustworthy Model Registry

A secure, trustworthy model registry system for managing AI/ML models, datasets, and code artifacts with comprehensive security features and access control.

## Purpose

This project implements a trustworthy model registry as part of ECE 461 Fall 2025 Project Phase 2. The system provides:

- **Artifact Management**: Upload, download, search, and manage ML models, datasets, and code
- **Security & Access Control**: Token-based authentication, rate limiting, and sensitive model protection
- **Metrics & Rating**: Automated quality scoring for models based on multiple criteria
- **Audit Trail**: Comprehensive tracking of all operations (who/what/when)
- **Malicious Detection**: Automated detection of suspicious or low-quality models

## Key Features

### ✅ Baseline Features
- Upload/ingest artifacts from HuggingFace and GitHub
- Search and query artifacts by name, type, or regex
- Download artifacts with S3 storage backend
- Model rating system (license, bus factor, code quality, etc.)
- Lineage tracking for model relationships
- License compatibility checking
- Cost analysis (storage size calculation)

### 🔒 Security Track (Access Control)
- **JWT-like Token System**: Tokens valid for 1000 API calls OR 10 hours
- **Bcrypt Password Hashing**: Secure credential storage
- **Multiple Active Tokens**: Per-user token management
- **Sensitive Model Protection**: JavaScript policies for access control
- **Malicious Model Detection**: Automated flagging of suspicious artifacts
- **Comprehensive Audit Trail**: Track all uploads and downloads

### 🚀 Performance
- **Rate Limiting**: DoS protection with configurable limits
- **Async Architecture**: Handle concurrent requests efficiently
- **S3 Storage**: Scalable artifact storage

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/model_registry

# AWS S3
S3_BUCKET_NAME=model-registry-packages
S3_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# HuggingFace Token (for model downloads)
HF_TOKEN=your_huggingface_token

# Admin Credentials (DO NOT CHANGE - per specification)
ADMIN_USERNAME=ece30861defaultadminuser
ADMIN_PASSWORD=correcthorsebatterystaple123(!__+@**(A;DROP TABLE packages

# Security
SECRET_KEY=your_random_secret_key

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_SEARCH_PER_MINUTE=30
```

### Dependencies

Install Python dependencies:

```bash
pip install -r requirements.txt
```

## Deployment

### Local Development

1. **Initialize the database:**
   ```bash
   python -m src.core.database
   ```

2. **Run the API server:**
   ```bash
   python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Access the API:**
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs

### AWS Deployment

1. **Configure AWS credentials:**
   ```bash
   cp .env.aws.template .env.aws
   # Edit .env.aws with your AWS settings
   ```

2. **Deploy to AWS:**
   ```bash
   ./deploy-to-aws-complete.sh
   ```

3. **Update ECS task:**
   - The deployment script will create ECR repositories, RDS database, S3 bucket, and ECS services
   - Environment variables are configured via ECS task definition

## How to Interact with the API

### Authentication

**1. Get a token:**
```bash
curl -X PUT http://localhost:8000/authenticate \
  -H "Content-Type: application/json" \
  -d '{
    "user": {"name": "ece30861defaultadminuser", "is_admin": true},
    "secret": {"password": "correcthorsebatterystaple123(!__+@**(A;DROP TABLE packages"}
  }'
```

Response: `bearer <token>`

**2. Use the token in requests:**
```bash
curl -X GET http://localhost:8000/artifacts \
  -H "X-Authorization: bearer <token>"
```

### Common Operations

#### Upload a Model
```bash
curl -X POST http://localhost:8000/artifact/model \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://huggingface.co/google-bert/bert-base-uncased"
  }'
```

#### Search for Artifacts
```bash
curl -X POST http://localhost:8000/artifacts \
  -H "Content-Type: application/json" \
  -d '[{"name": "bert"}]'
```

#### Get Model Rating
```bash
curl -X GET http://localhost:8000/artifact/model/{id}/rate
```

#### Download an Artifact
```bash
curl -X GET http://localhost:8000/artifacts/model/{id}
```

### Security Track Operations

#### Mark Model as Sensitive (with JS Policy)
```bash
curl -X PUT http://localhost:8000/artifact/model/{id}/sensitive \
  -H "X-Authorization: bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "js_program": "console.log(\"Access granted\"); process.exit(0);"
  }'
```

#### Get Malicious Models (Admin Only)
```bash
curl -X GET http://localhost:8000/security/malicious-models \
  -H "X-Authorization: bearer <admin_token>"
```

#### Get Audit Trail (Admin Only)
```bash
curl -X GET "http://localhost:8000/security/audit-trail?limit=50" \
  -H "X-Authorization: bearer <admin_token>"
```

## API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Architecture

```
Phase-2/
├── src/
│   ├── api/              # FastAPI endpoints
│   ├── core/             # Database models, auth, config
│   ├── services/         # Business logic (S3, metrics, HuggingFace)
│   └── utils/            # Helpers (logging, license checking)
├── tests/                # Test suite
├── front-end/            # React frontend
└── .env                  # Environment configuration
```

## Security Features

### Token Management
- Tokens expire after **10 hours** OR **1000 API calls** (whichever comes first)
- Multiple active tokens supported per user
- Automatic token cleanup on expiry

### Rate Limiting
- General endpoints: 100 requests/minute
- Search endpoints: 30 requests/minute (more expensive operations)
- Per-IP rate limiting to prevent DoS attacks

### Sensitive Models
- Models can be marked as "sensitive" with JavaScript access policies
- JS program must exit with code 0 to allow download
- Only model owner or admin can set policies

### Malicious Model Detection
Automatically flags models based on:
- Low license score (< 0.3)
- Low net quality score (< 0.2)
- Package confusion audit flags

## Testing

Run the test suite:
```bash
# Unit tests
pytest tests/

# Integration tests
pytest tests/test_api_crud.py

# GUI tests (requires frontend)
./run_gui_tests.sh
```

## Troubleshooting

### Database Connection Issues
- Ensure PostgreSQL is running
- Check `DATABASE_URL` in `.env`
- Run: `python -m src.core.database` to initialize

### S3 Upload Failures
- Verify AWS credentials in `.env`
- Check S3 bucket permissions
- Ensure bucket exists in specified region

### HuggingFace Download Errors
- Verify `HF_TOKEN` in `.env`
- Check network connectivity
- Some models may require authentication

## Project Status

- **Baseline Features**: ✅ Complete
- **Security/Access Control Track**: ✅ Complete
- **Frontend**: ✅ Complete
- **Deployment**: ✅ AWS-ready

## License

This project is part of ECE 461 coursework at Purdue University.

## Contributors

- Anthony Chavez
- Bozidar Perovic
- Eli Beyer
- Mauricio Salazar

---

**Version**: 3.4.7
**Last Updated**: December 2024
