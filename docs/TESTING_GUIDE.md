# Testing Guide for Model Registry API

## Quick Testing Options

### Option 1: Interactive Swagger UI (Easiest)
### Option 2: Manual curl Commands
### Option 3: Automated Test Suite
### Option 4: Python Test Script

---

## Option 1: Interactive Swagger UI ⭐ RECOMMENDED

This is the easiest way to test all endpoints interactively.

### 1. Start the API Server
```bash
# First, set up the database
python3 init_db.py

# Start the server
./run_api.sh
```

### 2. Open Swagger UI
Navigate to: **http://localhost:8000/docs**

### 3. Authenticate
1. Click on **POST /authenticate**
2. Click "Try it out"
3. Enter credentials:
   ```json
   {
     "username": "admin",
     "password": "admin123"
   }
   ```
4. Click "Execute"
5. Copy the token from the response
6. Click "Authorize" button at the top
7. Enter: `Bearer <your-token>` (or just the token if using X-Authorization header)
8. Now you can test all endpoints!

### 4. Test Endpoints
Try these in order:
1. **GET /health** - Check system health
2. **POST /user/register** - Create a test user
3. **POST /package** - Upload a test package (you'll need a zip file)
4. **POST /packages** - Search for packages
5. **GET /package/{id}** - Get download URL
6. **PUT /package/{id}/rate** - Rate a package
7. **GET /package/{id}/metadata** - Get metadata

---

## Option 2: Manual Testing with curl

### Step 1: Setup
```bash
# Initialize database
python3 init_db.py

# Start server in background
python3 -m uvicorn api:app --host 0.0.0.0 --port 8000 &
```

### Step 2: Authenticate and Get Token
```bash
# Login and save token
TOKEN=$(curl -s -X POST http://localhost:8000/authenticate \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])")

echo "Token: $TOKEN"
```

### Step 3: Test Health Endpoint
```bash
curl -X GET http://localhost:8000/health
```

### Step 4: Register a Test User
```bash
curl -X POST http://localhost:8000/user/register \
  -H "X-Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "test123",
    "permissions": ["upload", "download", "search"]
  }'
```

### Step 5: Create a Test Package (Simulated)
```bash
# Create a dummy zip file for testing
echo "test model data" > test_model.txt
zip test_package.zip test_model.txt

# Upload package
curl -X POST http://localhost:8000/package \
  -H "X-Authorization: $TOKEN" \
  -F "file=@test_package.zip" \
  -F "name=test-model" \
  -F "version=1.0.0" \
  -F "description=Test model for API testing" \
  -F "model_url=https://huggingface.co/bert-base-uncased" \
  -F "code_url=https://github.com/huggingface/transformers"

# Save the package ID from response
```

### Step 6: Search Packages
```bash
curl -X POST http://localhost:8000/packages \
  -H "X-Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "test"}'
```

### Step 7: Get Package Metadata
```bash
# Replace PACKAGE_ID with actual ID from previous response
PACKAGE_ID="your-package-id-here"

curl -X GET "http://localhost:8000/package/$PACKAGE_ID/metadata" \
  -H "X-Authorization: $TOKEN"
```

### Step 8: Rate Package
```bash
curl -X PUT "http://localhost:8000/package/$PACKAGE_ID/rate" \
  -H "X-Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"score": 5}'
```

### Step 9: Download Package
```bash
curl -X GET "http://localhost:8000/package/$PACKAGE_ID" \
  -H "X-Authorization: $TOKEN"
# Returns a presigned S3 URL
```

---

## Option 3: Automated Test Suite with pytest

I'll create a test file for you. See `tests/test_api.py`

### Run Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/test_api.py -v

# Run with coverage
pytest tests/test_api.py -v --cov=. --cov-report=term
```

---

## Option 4: Python Test Script

See `test_api_manual.py` for a complete manual test script.

### Run the Test Script
```bash
python3 test_api_manual.py
```

This script will:
1. Authenticate
2. Create a test user
3. Upload a test package
4. Search packages
5. Rate a package
6. Get metadata
7. Clean up test data

---

## Testing Without S3 (Local Development)

If you don't have S3 set up yet, you can test with local file storage:

### 1. Modify s3_helper.py for Local Testing
Create a mock version or use local filesystem:

```bash
# Set environment variable to skip S3
export S3_MOCK=true
```

### 2. Use SQLite Instead of PostgreSQL
```bash
# In .env, change DATABASE_URL to:
DATABASE_URL=sqlite:///./test_model_registry.db
```

---

## Testing Checklist

### ✅ Authentication
- [ ] Login with admin credentials
- [ ] Receive valid token
- [ ] Token works for authenticated requests
- [ ] Invalid credentials return 401
- [ ] Expired token returns 401

### ✅ User Management
- [ ] Register new user (admin only)
- [ ] Update user permissions (admin only)
- [ ] Delete user
- [ ] Non-admin cannot register users

### ✅ Package Management
- [ ] Upload package with metrics evaluation
- [ ] Package stored in S3
- [ ] Metrics calculated and stored
- [ ] Search packages by name
- [ ] Search packages with regex
- [ ] Get package metadata
- [ ] Download package (presigned URL)
- [ ] Delete package (admin only)

### ✅ Rating System
- [ ] Rate package (1-5)
- [ ] Update existing rating
- [ ] Calculate average rating
- [ ] Invalid score rejected

### ✅ Permission System
- [ ] Upload requires 'upload' permission
- [ ] Download requires 'download' permission
- [ ] Search requires 'search' permission
- [ ] Admin can do everything
- [ ] Non-admin blocked from admin operations

### ✅ Edge Cases
- [ ] Duplicate package name/version rejected
- [ ] Missing required fields rejected
- [ ] Invalid UUID returns 404
- [ ] Package not found returns 404
- [ ] User not found returns 404

---

## Common Issues and Solutions

### Issue: Database Connection Error
```bash
# Check PostgreSQL is running
psql -U postgres -l

# Create database if missing
createdb model_registry

# Test connection
psql -U postgres -d model_registry -c "SELECT 1;"
```

### Issue: S3 Connection Error
```bash
# Check AWS credentials
aws s3 ls

# Test S3 access
aws s3 ls s3://model-registry-packages

# Use local storage for testing (modify config)
```

### Issue: Import Errors
```bash
# Reinstall dependencies
pip install -r dependencies.txt

# Check Python version (need 3.8+)
python3 --version
```

### Issue: Port Already in Use
```bash
# Kill existing process
lsof -ti:8000 | xargs kill -9

# Or use different port
python3 -m uvicorn api:app --port 8001
```

---

## Performance Testing

### Load Testing with Apache Bench
```bash
# Install Apache Bench
# macOS: brew install httpd
# Ubuntu: apt-get install apache2-utils

# Test health endpoint
ab -n 1000 -c 10 http://localhost:8000/health

# Test authenticated endpoint
ab -n 100 -c 5 -H "X-Authorization: $TOKEN" http://localhost:8000/packages
```

### Load Testing with Locust
```bash
pip install locust

# Create locustfile.py and run
locust -f locustfile.py --host=http://localhost:8000
```

---

## Database Inspection

### View Database Contents
```bash
# Connect to database
psql -U postgres -d model_registry

# List tables
\dt

# View users
SELECT id, username, is_admin, permissions FROM users;

# View packages
SELECT id, name, version, upload_date FROM packages;

# View metrics
SELECT package_id, net_score, bus_factor FROM metrics;

# Exit
\q
```

---

## API Testing Best Practices

1. **Always test with fresh database** for consistent results
2. **Use test data** that can be easily cleaned up
3. **Test error cases** not just happy paths
4. **Check response status codes** (200, 201, 400, 401, 403, 404, 500)
5. **Verify data persistence** by querying database
6. **Test pagination** with large datasets
7. **Test concurrent requests** for race conditions
8. **Monitor logs** for errors during testing

---

## Next Steps

1. Start with **Swagger UI** testing (easiest)
2. Run the **manual test script** for automation
3. Create **pytest tests** for CI/CD
4. Set up **integration tests** with real S3 bucket
5. Add **performance tests** for production readiness