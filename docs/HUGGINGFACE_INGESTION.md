# HuggingFace Model Ingestion

This document describes the HuggingFace model ingestion feature that automatically downloads, evaluates, and stores models from HuggingFace Hub.

## Overview

The HuggingFace ingestion feature allows you to ingest models directly from HuggingFace Hub by providing just the model identifier. The system will:

1. **Download** the complete model package (weights, config, tokenizer, etc.)
2. **Evaluate** the model using your Phase 2 metrics
3. **Validate** that the model meets minimum quality thresholds (≥0.5 for all non-latency metrics)
4. **Package** the model into a zip file
5. **Upload** to S3 storage
6. **Store** metadata and metrics in the database

## API Endpoint

### POST /package/ingest-huggingface

**Authentication Required:** Yes (requires "upload" permission)

**Request Body:**
```json
{
  "model_id": "distilbert-base-uncased-finetuned-sst-2-english",
  "version": "1.0.0",  // Optional: defaults to 1.0.0
  "description": "Sentiment analysis model"  // Optional: auto-generated if not provided
}
```

**Response (Success - 200):**
```json
{
  "package_id": "uuid-here",
  "name": "distilbert-base-uncased-finetuned-sst-2-english",
  "version": "1.0.0",
  "model_id": "distilbert-base-uncased-finetuned-sst-2-english",
  "s3_path": "s3://bucket/model-name/1.0.0/package.zip",
  "net_score": 0.75,
  "size_bytes": 268435456,
  "message": "HuggingFace model ingested successfully",
  "metrics": {
    "license": 1.0,
    "size_score": 0.8,
    "ramp_up_time": 0.7,
    "bus_factor": 0.6,
    "performance_claims": 0.9,
    "dataset_and_code_score": 0.75,
    "dataset_quality": 0.8,
    "code_quality": 0.85,
    "net_score": 0.75
  }
}
```

**Response (Validation Failed - 400):**
```json
{
  "detail": "Model does not meet quality requirements. Failed metrics: Bus Factor (0.3 < 0.5), Ramp-Up Time (0.4 < 0.5)"
}
```

**Response (Not Found - 404):**
```json
{
  "detail": "Model 'invalid-model-id' not found on HuggingFace Hub"
}
```

## Supported Model Identifiers

The endpoint accepts standard HuggingFace model identifiers:

- **Community models:** `gpt2`, `bert-base-uncased`, `distilbert-base-cased`
- **Organization models:** `facebook/bart-large`, `google/flan-t5-small`, `microsoft/phi-2`
- **User models:** `username/model-name`

## Quality Validation

All ingested models must meet the following criteria:

| Metric | Minimum Score |
|--------|---------------|
| License | ≥ 0.5 |
| Size Score | ≥ 0.5 |
| Ramp-Up Time | ≥ 0.5 |
| Bus Factor | ≥ 0.5 |
| Performance Claims | ≥ 0.5 |
| Dataset/Code Score | ≥ 0.5 |
| Dataset Quality | ≥ 0.5 |
| Code Quality | ≥ 0.5 |

If **any** metric scores below 0.5, the ingestion will be rejected with a detailed error message.

## Usage Examples

### Using Python Requests

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. Authenticate
auth_response = requests.post(
    f"{BASE_URL}/authenticate",
    json={"username": "admin", "password": "admin123"}
)
token = auth_response.json()["token"]

# 2. Ingest a model
response = requests.post(
    f"{BASE_URL}/package/ingest-huggingface",
    headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    },
    json={
        "model_id": "distilbert-base-uncased-finetuned-sst-2-english",
        "description": "Sentiment analysis model"
    }
)

if response.status_code == 200:
    result = response.json()
    print(f"Success! Package ID: {result['package_id']}")
    print(f"Net Score: {result['net_score']}")
elif response.status_code == 400:
    print(f"Validation failed: {response.json()['detail']}")
else:
    print(f"Error: {response.text}")
```

### Using cURL

```bash
# 1. Authenticate
curl -X POST http://localhost:8000/authenticate \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# 2. Set token (replace with actual token from step 1)
TOKEN="your-token-here"

# 3. Ingest a model
curl -X POST http://localhost:8000/package/ingest-huggingface \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "distilbert-base-uncased-finetuned-sst-2-english",
    "description": "Sentiment analysis model"
  }'
```

### Using Swagger UI

1. Navigate to `http://localhost:8000/docs`
2. Click on "POST /authenticate" and authenticate
3. Copy the token from the response
4. Click the "Authorize" button at the top and paste the token
5. Navigate to "POST /package/ingest-huggingface"
6. Click "Try it out" and provide the model_id
7. Click "Execute"

## Implementation Details

### Files Created

1. **src/services/huggingface_service.py**
   - `HuggingFaceIngestionService` class
   - Methods for downloading models, creating zip packages
   - Model metadata extraction

2. **src/utils/validation.py**
   - `validate_metric_threshold()` - Validates metrics meet minimum requirements
   - `validate_package_name()` - Validates package name format
   - `validate_version()` - Validates semantic versioning

3. **src/api/schemas.py** (updated)
   - `HuggingFaceIngestRequest` - Request model
   - `HuggingFaceIngestResponse` - Response model

4. **src/api/main.py** (updated)
   - New endpoint: `POST /package/ingest-huggingface`
   - Integrated with existing metrics evaluation
   - Automatic cleanup of temporary files

5. **tests/test_huggingface_ingestion.py**
   - Test suite for the ingestion feature
   - Examples of successful and failed ingestions

6. **docs/HUGGINGFACE_INGESTION.md** (this file)
   - Complete documentation

### Architecture

```
User Request
    ↓
FastAPI Endpoint (/package/ingest-huggingface)
    ↓
HuggingFaceIngestionService.download_model()
    ↓ (downloads full model from HF Hub)
Create Zip Package
    ↓
MetricsEvaluator.evaluate()
    ↓ (parallel evaluation of 8 metrics)
validate_metric_threshold()
    ↓ (check all metrics ≥ 0.5)
Upload to S3
    ↓
Save to Database (packages + metrics tables)
    ↓
Return Response
```

## Testing

Run the test suite:

```bash
# Make sure the API is running
./run_api_new.sh

# In another terminal, run tests
python3 tests/test_huggingface_ingestion.py

# Or see curl examples
python3 tests/test_huggingface_ingestion.py --curl
```

## Performance Considerations

- **Download time:** Depends on model size and network speed (typically 30 seconds to 5 minutes)
- **Metrics evaluation:** Runs in parallel, typically completes in 10-30 seconds
- **Zip creation:** Fast, usually < 10 seconds
- **S3 upload:** Depends on model size and AWS region

### Recommended Models for Testing

| Model | Size | Expected Download Time |
|-------|------|------------------------|
| `distilbert-base-uncased-finetuned-sst-2-english` | ~250MB | 1-2 minutes |
| `gpt2` | ~500MB | 2-3 minutes |
| `distilgpt2` | ~350MB | 1-2 minutes |

## Error Handling

The endpoint handles the following error cases:

1. **Model not found (404):** Invalid HuggingFace model ID
2. **Validation failed (400):** Model doesn't meet quality thresholds
3. **Duplicate (400):** Model already exists with the same version
4. **S3 upload failed (500):** AWS credentials or connectivity issues
5. **Authentication (401):** Invalid or missing token
6. **Permission denied (403):** User lacks "upload" permission

## Future Enhancements

Possible improvements:

1. **Dataset ingestion:** Support for HuggingFace datasets
2. **Batch ingestion:** Ingest multiple models in one request
3. **Version detection:** Automatically detect model versions from HF metadata
4. **Incremental updates:** Update existing models without re-downloading
5. **Custom metrics threshold:** Allow per-model threshold configuration
6. **Progress tracking:** WebSocket or polling endpoint for download progress

## Related Documentation

- [API README](./API_README.md) - Complete API documentation
- [CRUD Implementation Plan](./CRUD_IMPLEMENTATION_PLAN.md) - System architecture
- [Testing Guide](./TESTING_GUIDE.md) - Testing procedures

## Support

For issues or questions:
- Check the logs in `/tmp/model_registry.log`
- Verify AWS S3 credentials in `.env`
- Ensure HuggingFace Hub is accessible from your network
- Test with small models first (< 500MB)