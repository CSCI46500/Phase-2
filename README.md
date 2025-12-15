# Trustworthy Model Registry - Phase 2

A comprehensive model registry system for managing, evaluating, and distributing ML/AI models with security-focused access controls and quality metrics.

## Project Overview

This project implements a **Trustworthy Model Registry** as part of ECE 461 Fall 2025 Phase 2. It provides:

- **Model Ingestion**: Automated ingestion from HuggingFace and GitHub
- **Quality Metrics**: 11 automated metrics for model evaluation
- **Security Track**: Token-based authentication, sensitive model protection
- **Browser Interface**: React-based frontend for model management
- **RESTful API**: OpenAPI-compliant endpoints for programmatic access

## Table of Contents

- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [API Endpoints](#api-endpoints)
- [Security Features](#security-features)
- [LLM Integration](#llm-integration)
- [Testing](#testing)
- [Deployment](#deployment)
- [Project Structure](#project-structure)

## Architecture

```
+------------------+     +------------------+     +------------------+
|   React Frontend |---->|   FastAPI Backend|---->|   PostgreSQL DB  |
|   (Vite + TS)    |     |   (Python 3.9+)  |     |                  |
+------------------+     +------------------+     +------------------+
                                  |
                                  v
                         +------------------+
                         |   AWS S3 Storage |
                         |   (Model Files)  |
                         +------------------+
```

### Tech Stack

**Backend:**
- FastAPI 0.100+ (REST API framework)
- SQLAlchemy 2.0+ (ORM)
- PostgreSQL 15 (Database)
- bcrypt (Password hashing)
- boto3 (AWS S3 integration)

**Frontend:**
- React 19 with TypeScript
- Vite (Build tool)
- Axios (HTTP client)
- Recharts (Data visualization)

**Infrastructure:**
- Docker & Docker Compose (Local development)
- AWS ECS Fargate (Production deployment)
- AWS RDS PostgreSQL (Production database)
- AWS S3 (Model storage)
- AWS ALB (Load balancing)

## Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- Docker & Docker Compose
- AWS CLI (for deployment)

### Local Development

1. **Clone and setup:**
   ```bash
   git clone <repository-url>
   cd 200pluscode

   # Create virtual environment
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # or .venv\Scripts\activate on Windows

   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Start with Docker Compose:**
   ```bash
   docker-compose up -d
   ```
   This starts:
   - PostgreSQL database (port 5432)
   - MinIO S3-compatible storage (ports 9000, 9001)
   - FastAPI backend (port 8000)
   - React frontend (port 5173)

3. **Access the application:**
   - Frontend: http://localhost:5173
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Default Credentials

```
Username: ece30861defaultadminuser
Password: correcthorsebatterystaple123(!__+@**(A'";DROP TABLE packages;
```

> Note: The password contains SQL injection test characters intentionally for security testing.

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/model_registry

# AWS S3 (or MinIO for local)
S3_BUCKET_NAME=model-registry-packages
S3_ENDPOINT_URL=http://localhost:9000  # Remove for real AWS
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin123

# Authentication
SECRET_KEY=your-secret-key-here
ADMIN_USERNAME=ece30861defaultadminuser
ADMIN_PASSWORD=correcthorsebatterystaple123(!__+@**(A'";DROP TABLE packages;

# LLM Integration (optional)
ANTHROPIC_API_KEY=your-anthropic-key  # For README analysis

# GitHub Integration (optional)
GITHUB_TOKEN=your-github-token  # For license checking
```

## API Endpoints

### Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/authenticate` | PUT/POST | Get authentication token |

**Request:**
```json
{
  "user": {"name": "username", "is_admin": true},
  "secret": {"password": "password"}
}
```

**Response:** `"bearer <token>"`

### Artifact Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/artifact/{type}` | POST | Create new artifact |
| `/artifacts` | POST | Search/list artifacts |
| `/artifacts/{type}/{id}` | GET | Get artifact details |
| `/artifacts/{type}/{id}` | PUT | Update artifact |
| `/artifacts/{type}/{id}` | DELETE | Delete artifact |

### Model Rating

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/artifact/model/{id}/rate` | GET | Get model quality metrics |
| `/artifact/model/{id}/lineage` | GET | Get model lineage graph |
| `/artifact/{type}/{id}/cost` | GET | Get artifact cost (size) |

### Utility Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | System health check |
| `/tracks` | GET | Implemented feature tracks |
| `/reset` | DELETE | Reset registry to default |
| `/artifact/byRegEx` | POST | Search by regex |
| `/artifact/model/{id}/license-check` | POST | Check license compatibility |

## Security Features

### Token-Based Authentication

- Tokens valid for **1000 API calls** or **10 hours** (configurable)
- Multiple active tokens allowed per user
- Passwords hashed with **bcrypt** (never stored in plaintext)
- Token stored as SHA256 hash in database

### Password Security

The default password intentionally contains:
- Special characters: `(!__+@**(A`
- SQL injection test: `'";DROP TABLE packages;`

This tests that the system properly handles:
- SQL injection attacks (protected via parameterized queries)
- Special character encoding
- Input validation

### Rate Limiting

- 100 requests/minute per IP (general)
- 30 requests/minute for search operations
- Configurable via `RATE_LIMIT_ENABLED` and related settings

## LLM Integration

The system uses Claude (Anthropic) for intelligent README analysis:

### Features

1. **Structured Prompts**: System role defines LLM as ML expert analyst
2. **Parameter Tuning**:
   - Temperature: 0.05-0.2 (low for consistent scoring)
   - top_p: 0.9-0.95 (controlled diversity)
   - max_tokens: 300-800 (task-specific)
3. **Safeguards**:
   - JSON schema validation for outputs
   - Confidence scores (0.0-1.0)
   - Fallback to keyword analysis when unavailable

### Usage Example

```python
from src.services.llm_readme_analyzer import get_llm_analyzer

analyzer = get_llm_analyzer()
result = analyzer.analyze_readme_quality(readme_content)

print(f"Score: {result.score}")
print(f"Confidence: {result.confidence}")
print(f"Sections: {result.metadata['sections']}")
```

### Supported Analysis Types

- **README Quality**: Documentation completeness and clarity
- **Artifact Relationships**: Model derivation and lineage
- **Performance Extraction**: Benchmark and metric extraction

## Testing

### Run All Tests

```bash
# Unit tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src --cov-report=html

# GUI tests (requires Selenium)
pytest tests/gui/ -v

# Accessibility tests
pytest tests/accessibility/ -v
```

### Test Categories

| Directory | Description |
|-----------|-------------|
| `tests/` | Unit tests for core functionality |
| `tests/gui/` | Selenium-based UI tests |
| `tests/accessibility/` | ADA compliance tests |

## Deployment

### AWS Deployment

1. **Configure AWS credentials:**
   ```bash
   cp .env.aws.template .env.aws
   # Edit .env.aws with your values
   ```

2. **Deploy using the automated script:**
   ```bash
   ./deploy-aws.sh
   ```

3. **Manual deployment steps:**
   - Build and push Docker images to ECR
   - Update ECS task definitions
   - Deploy to ECS Fargate

### Current Deployment

- **Backend API**: http://model-registry-alb-531271739.us-east-1.elb.amazonaws.com:8000
- **Frontend UI**: http://model-registry-alb-531271739.us-east-1.elb.amazonaws.com

## Project Structure

```
200pluscode/
├── src/
│   ├── api/
│   │   └── main.py           # FastAPI application
│   ├── core/
│   │   ├── auth.py           # Authentication logic
│   │   ├── config.py         # Configuration management
│   │   ├── database.py       # Database connection
│   │   └── models.py         # SQLAlchemy models
│   ├── crud/
│   │   ├── package.py        # Package CRUD operations
│   │   └── ...               # Other CRUD modules
│   ├── services/
│   │   ├── huggingface_service.py    # HuggingFace integration
│   │   ├── llm_readme_analyzer.py    # LLM-powered analysis
│   │   ├── metrics_service.py        # Metrics orchestration
│   │   └── s3_service.py             # S3 storage
│   └── utils/
│       ├── metric_calculators.py     # Individual metrics
│       └── ...                       # Utility modules
├── front-end/
│   └── model-registry-frontend/
│       ├── src/
│       │   ├── components/   # React components
│       │   ├── hooks/        # Custom React hooks
│       │   ├── services/     # API client
│       │   └── types/        # TypeScript types
│       └── ...
├── tests/
│   ├── gui/                  # Selenium GUI tests
│   └── accessibility/        # ADA compliance tests
├── .github/
│   └── workflows/            # CI/CD pipelines
├── docker-compose.yml        # Local development setup
├── Dockerfile               # Backend container
├── requirements.txt         # Python dependencies
└── openapi.yaml             # API specification
```

## Quality Metrics

The system evaluates models across 11 metrics:

| Metric | Weight | Description |
|--------|--------|-------------|
| License | 15% | Open source license compatibility |
| Code Quality | 11% | Repository quality and maintenance |
| Dataset Quality | 11% | Training data documentation |
| Reproducibility | 10% | Can the model be run from demo code? |
| Ramp-Up Time | 9% | Ease of getting started |
| Bus Factor | 9% | Contributor diversity |
| Reviewedness | 9% | Code review coverage |
| Dataset & Code Score | 9% | Resource availability |
| Size Score | 7% | Hardware compatibility |
| Performance Claims | 7% | Benchmark documentation |
| Tree Score | 3% | Lineage quality |

## CI/CD Pipeline

### Continuous Integration (`.github/workflows/ci.yml`)
- Linting and code style checks
- Unit test execution
- Coverage reporting

### Continuous Deployment (`.github/workflows/deploy-aws.yml`)
- Automatic deployment on main branch push
- Docker image builds
- ECS service updates
- Smoke tests post-deployment

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is for educational purposes as part of ECE 461 Fall 2025.

## Acknowledgments

- ECE 461 Course Staff
- Anthropic Claude API for LLM integration
- HuggingFace for model hosting
