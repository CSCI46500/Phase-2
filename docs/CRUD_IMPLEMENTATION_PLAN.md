# CRUD Operations Implementation Plan

## Overvi
This document describes the specific implementation plan for CRUD operations in the Model Registry system using the selected technology stack.

---

## Architecture Overview

```
User/Frontend → API Gateway → Lambda/EC2 → PostgreSQL (RDS)
                                        ↓
                                      AWS S3
```

---

## CRUD Operations Breakdown

### **CREATE Operations**

#### 1. Upload Model Package
**Endpoint:** `POST /package`

**Technology Stack:**
- **API Gateway**: Receives upload request, routes to Lambda
- **AWS Lambda**: Validates request, authentication token
- **AWS EC2**: Handles heavy lifting (unzip, parse, metric calculation)
- **PostgreSQL (RDS)**: Stores metadata (name, version, uploader, metrics, timestamps)
- **AWS S3**: Stores the actual .zip package

**Implementation Flow:**
```
1. User uploads via React frontend (file + metadata)
2. API Gateway receives multipart/form-data request
3. Lambda function validates:
   - Authentication token (check permission: 'upload')
   - Package name format
   - Required metadata fields
4. Lambda triggers EC2 instance or ECS task for processing:
   - Extract zip contents
   - Parse package.json/config.json
   - Calculate metrics (BusFactor, Correctness, RampUp, etc.)
   - Calculate new metrics (Reproducibility, Reviewedness, TreeScore)
   - Extract README for model card
5. EC2 stores zip in S3 bucket: s3://model-registry/{name}/{version}/package.zip
6. EC2 inserts metadata into PostgreSQL:
   - Table: packages (id, name, version, uploader_id, upload_date)
   - Table: metrics (package_id, busfactor, correctness, ...)
   - Table: lineage (package_id, parent_id) - parsed from config.json
7. Return package_id and confirmation to user
```

**FastAPI Endpoint Implementation:**
```python
@app.post("/package")
async def upload_package(
    file: UploadFile,
    name: str,
    version: str,
    token: str = Header(...)
):
    # Verify token and 'upload' permission
    user = verify_token(token)
    if not user.has_permission('upload'):
        raise HTTPException(403, "No upload permission")

    # Trigger async processing (Lambda → EC2)
    job_id = await trigger_package_processing(file, name, version, user.id)

    # Return job status
    return {"message": "Processing started", "job_id": job_id}
```

#### 2. Upload via URL (HuggingFace/npm)
**Endpoint:** `POST /package/ingest`

**Technology Stack:**
- **Lambda**: Validates URL and permission
- **EC2**: Downloads package, validates metrics (≥0.5 for non-latency)
- **S3**: Stores downloaded package
- **PostgreSQL**: Stores metadata

**Implementation Flow:**
```
1. User provides URL (HuggingFace model or npm package)
2. Lambda validates URL format and user permission
3. EC2 downloads package from external source
4. EC2 calculates all metrics
5. If all non-latency metrics ≥ 0.5:
   - Store in S3
   - Insert into PostgreSQL
   - Return success
6. Else:
   - Reject and return metric scores
```

#### 3. Rate Model
**Endpoint:** `PUT /package/{id}/rate`

**Technology Stack:**
- **API Gateway**: Routes to Lambda
- **Lambda**: Updates rating in PostgreSQL
- **PostgreSQL**: Stores ratings

**Implementation Flow:**
```
1. User submits rating (1-5 stars)
2. Lambda validates token and permission
3. Update ratings table in PostgreSQL:
   - INSERT INTO ratings (package_id, user_id, score, timestamp)
4. Recalculate average rating for package
5. Return updated average
```

---

### **READ Operations**

#### 1. Download Full Package
**Endpoint:** `GET /package/{id}`

**Technology Stack:**
- **API Gateway**: Routes request
- **Lambda**: Validates permission, checks if sensitive
- **EC2**: Executes JavaScript for sensitive models
- **S3**: Retrieves zip file
- **PostgreSQL**: Logs download history

**Implementation Flow:**
```
1. User requests package by ID
2. Lambda validates token and 'download' permission
3. Lambda queries PostgreSQL for package metadata
4. Check if model is marked 'sensitive':
   - YES: Trigger EC2 to execute JavaScript sandbox
     - Pass MODEL_NAME, UPLOADER, DOWNLOADER, ZIP_PATH
     - JavaScript validates safety conditions
     - If approved, proceed to download
     - If rejected, return error
   - NO: Proceed directly to download
5. Lambda generates signed S3 URL (expires in 5 minutes)
6. Record download in PostgreSQL:
   - INSERT INTO download_history (package_id, user_id, timestamp)
7. Return signed URL or stream file to user
```

**FastAPI Implementation:**
```python
@app.get("/package/{id}")
async def download_package(
    id: str,
    token: str = Header(...)
):
    user = verify_token(token)
    if not user.has_permission('download'):
        raise HTTPException(403, "No download permission")

    package = db.query(Package).filter(Package.id == id).first()

    if package.is_sensitive:
        # Execute JavaScript validation on EC2
        validation_result = await execute_js_validation(
            package.name, package.uploader, user.username, package.s3_path
        )
        if not validation_result.approved:
            raise HTTPException(403, "Download rejected by security policy")

    # Log download
    db.add(DownloadHistory(package_id=id, user_id=user.id))
    db.commit()

    # Generate signed S3 URL
    signed_url = s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': 'model-registry', 'Key': package.s3_path},
        ExpiresIn=300
    )

    return {"url": signed_url}
```

#### 2. Download Partial Package (Weights Only)
**Endpoint:** `GET /package/{id}/weights`

**Implementation:**
```
1. Query PostgreSQL for package structure
2. Check if package has separate weight files
3. Generate signed S3 URL for specific file:
   - s3://model-registry/{name}/{version}/model.safetensors
4. Return partial download URL
```

#### 3. Enumerate/Search Packages
**Endpoint:** `POST /packages`

**Technology Stack:**
- **Lambda**: Handles query parsing and pagination
- **PostgreSQL**: Full-text search, regex matching
- **S3**: Not involved in search

**Implementation Flow:**
```
1. User submits search query (name, regex, version filter)
2. Lambda validates token and 'search' permission
3. Lambda constructs PostgreSQL query:
   - Name search: SELECT * FROM packages WHERE name ILIKE '%query%'
   - Regex search: SELECT * FROM packages WHERE name ~ 'regex_pattern'
   - Version filter: SELECT * FROM packages WHERE version = '1.2.3'
4. Implement pagination (offset/limit):
   - Default: 50 results per page
   - Prevents DoS by limiting max results
5. Return list of package metadata (no zip files)
```

**Pagination Example:**
```python
@app.post("/packages")
async def search_packages(
    query: PackageQuery,
    token: str = Header(...),
    offset: int = 0,
    limit: int = 50
):
    user = verify_token(token)
    if not user.has_permission('search'):
        raise HTTPException(403, "No search permission")

    # Build query
    db_query = db.query(Package)

    if query.name:
        db_query = db_query.filter(Package.name.ilike(f"%{query.name}%"))

    if query.version:
        db_query = db_query.filter(Package.version == query.version)

    if query.regex:
        db_query = db_query.filter(Package.name.op('~')(query.regex))

    # Paginate
    total = db_query.count()
    results = db_query.offset(offset).limit(min(limit, 100)).all()

    return {
        "packages": [p.to_dict() for p in results],
        "total": total,
        "offset": offset,
        "limit": limit
    }
```

#### 4. Get Package Metadata
**Endpoint:** `GET /package/{id}/metadata`

**Implementation:**
```
1. Query PostgreSQL for package metadata
2. Return JSON with:
   - Name, version, description
   - Metrics scores
   - Upload date, uploader
   - Dependencies (from lineage table)
   - Average rating
```

#### 5. View Lineage Graph
**Endpoint:** `GET /package/{id}/lineage`

**Technology Stack:**
- **Lambda**: Queries PostgreSQL
- **PostgreSQL**: Recursive CTE for parent-child relationships

**Implementation:**
```sql
-- Recursive query to get full lineage tree
WITH RECURSIVE lineage_tree AS (
  -- Base case: current package
  SELECT id, name, version, parent_id, 0 as depth
  FROM packages
  WHERE id = {package_id}

  UNION ALL

  -- Recursive case: parents
  SELECT p.id, p.name, p.version, p.parent_id, lt.depth + 1
  FROM packages p
  JOIN lineage_tree lt ON p.id = lt.parent_id
)
SELECT * FROM lineage_tree ORDER BY depth;
```

**Return format:**
```json
{
  "package_id": "123",
  "lineage": [
    {"id": "123", "name": "model-v3", "version": "3.0.0", "depth": 0},
    {"id": "122", "name": "model-v2", "version": "2.0.0", "depth": 1},
    {"id": "100", "name": "model-v1", "version": "1.0.0", "depth": 2}
  ]
}
```

---

### **UPDATE Operations**

#### 1. Update Model Rating
**Endpoint:** `PUT /package/{id}/rate`

**Implementation:** (See CREATE section - Rate Model)

#### 2. Update User Permissions (Admin Only)
**Endpoint:** `PUT /user/{id}/permissions`

**Technology Stack:**
- **Lambda**: Validates admin token
- **PostgreSQL**: Updates user_permissions table

**Implementation:**
```python
@app.put("/user/{user_id}/permissions")
async def update_permissions(
    user_id: str,
    permissions: List[str],  # ['upload', 'download', 'search', 'admin']
    token: str = Header(...)
):
    admin = verify_token(token)
    if not admin.is_admin:
        raise HTTPException(403, "Admin permission required")

    # Update permissions
    user = db.query(User).filter(User.id == user_id).first()
    user.permissions = json.dumps(permissions)
    db.commit()

    return {"message": "Permissions updated"}
```

**Note:** The specification shows [U]pdate in brackets, suggesting limited update support. Full package updates (re-upload) are NOT supported—only ratings and metadata.

---

### **DELETE Operations**

#### 1. Delete Package (Admin Only)
**Endpoint:** `DELETE /package/{id}`

**Technology Stack:**
- **Lambda**: Validates admin permission
- **PostgreSQL**: Deletes metadata (cascades to metrics, ratings, lineage)
- **S3**: Deletes zip file

**Implementation:**
```python
@app.delete("/package/{id}")
async def delete_package(
    id: str,
    token: str = Header(...)
):
    user = verify_token(token)
    if not user.is_admin:
        raise HTTPException(403, "Admin permission required")

    package = db.query(Package).filter(Package.id == id).first()

    # Delete from S3
    s3_client.delete_object(
        Bucket='model-registry',
        Key=package.s3_path
    )

    # Delete from PostgreSQL (cascades to related tables)
    db.delete(package)
    db.commit()

    return {"message": "Package deleted"}
```

#### 2. Delete User Account
**Endpoint:** `DELETE /user/{id}`

**Technology Stack:**
- **Lambda**: Validates permission (self-delete or admin)
- **PostgreSQL**: Deletes user record

**Implementation:**
```python
@app.delete("/user/{user_id}")
async def delete_user(
    user_id: str,
    token: str = Header(...)
):
    user = verify_token(token)

    # Users can delete themselves, admins can delete anyone
    if user.id != user_id and not user.is_admin:
        raise HTTPException(403, "Cannot delete other users")

    target_user = db.query(User).filter(User.id == user_id).first()
    db.delete(target_user)
    db.commit()

    return {"message": "User deleted"}
```

#### 3. Reset System
**Endpoint:** `DELETE /reset`

**Technology Stack:**
- **Lambda**: Validates admin permission
- **PostgreSQL**: Truncates all tables except default user
- **S3**: Deletes all objects in bucket

**Implementation:**
```python
@app.delete("/reset")
async def reset_system(token: str = Header(...)):
    user = verify_token(token)
    if not user.is_admin:
        raise HTTPException(403, "Admin permission required")

    # Delete all S3 objects
    s3_resource = boto3.resource('s3')
    bucket = s3_resource.Bucket('model-registry')
    bucket.objects.all().delete()

    # Truncate PostgreSQL tables
    db.execute("TRUNCATE packages, metrics, ratings, lineage, download_history CASCADE")
    db.execute("DELETE FROM users WHERE id != 'default_admin'")
    db.commit()

    return {"message": "System reset to default state"}
```

---

## Database Schema (PostgreSQL)

### Tables

#### 1. **users**
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,  -- bcrypt hash
    salt VARCHAR(32) NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    permissions JSONB DEFAULT '["search"]',  -- ['upload', 'download', 'search', 'admin']
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_username ON users(username);
```

#### 2. **tokens**
```sql
CREATE TABLE tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    api_calls_remaining INT DEFAULT 1000,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP
);

CREATE INDEX idx_tokens_hash ON tokens(token_hash);
```

#### 3. **packages**
```sql
CREATE TABLE packages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    description TEXT,
    uploader_id UUID REFERENCES users(id),
    s3_path VARCHAR(500) NOT NULL,  -- s3://bucket/name/version/package.zip
    is_sensitive BOOLEAN DEFAULT FALSE,
    js_policy_path VARCHAR(500),  -- Path to JS validation script
    size_bytes BIGINT,
    license VARCHAR(100),
    model_card TEXT,  -- Extracted from README
    upload_date TIMESTAMP DEFAULT NOW(),
    UNIQUE(name, version)
);

CREATE INDEX idx_packages_name ON packages(name);
CREATE INDEX idx_packages_version ON packages(version);
CREATE INDEX idx_packages_uploader ON packages(uploader_id);
CREATE FULLTEXT INDEX idx_packages_search ON packages(name, description, model_card);
```

#### 4. **metrics**
```sql
CREATE TABLE metrics (
    package_id UUID PRIMARY KEY REFERENCES packages(id) ON DELETE CASCADE,
    bus_factor FLOAT,
    correctness FLOAT,
    ramp_up FLOAT,
    responsive_maintainer FLOAT,
    license_score FLOAT,
    good_pinning_practice FLOAT,
    pull_request FLOAT,
    net_score FLOAT,
    -- New metrics
    reproducibility FLOAT,
    reviewedness FLOAT,
    tree_score FLOAT,
    calculated_at TIMESTAMP DEFAULT NOW()
);
```

#### 5. **lineage**
```sql
CREATE TABLE lineage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    package_id UUID REFERENCES packages(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES packages(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) DEFAULT 'derived_from',  -- 'derived_from', 'forked_from', etc.
    UNIQUE(package_id, parent_id)
);

CREATE INDEX idx_lineage_package ON lineage(package_id);
CREATE INDEX idx_lineage_parent ON lineage(parent_id);
```

#### 6. **ratings**
```sql
CREATE TABLE ratings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    package_id UUID REFERENCES packages(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    score INT CHECK (score >= 1 AND score <= 5),
    timestamp TIMESTAMP DEFAULT NOW(),
    UNIQUE(package_id, user_id)  -- One rating per user per package
);

CREATE INDEX idx_ratings_package ON ratings(package_id);
```

#### 7. **download_history**
```sql
CREATE TABLE download_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    package_id UUID REFERENCES packages(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    ip_address VARCHAR(45),  -- IPv6 support
    user_agent TEXT
);

CREATE INDEX idx_downloads_package ON download_history(package_id);
CREATE INDEX idx_downloads_user ON download_history(user_id);
CREATE INDEX idx_downloads_timestamp ON download_history(timestamp);
```

#### 8. **package_confusion_audit**
```sql
CREATE TABLE package_confusion_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    package_id UUID REFERENCES packages(id) ON DELETE CASCADE,
    suspicious_pattern VARCHAR(255),  -- What triggered the audit
    detected_at TIMESTAMP DEFAULT NOW(),
    severity VARCHAR(20),  -- 'low', 'medium', 'high'
    details JSONB  -- Additional metadata
);

CREATE INDEX idx_audit_package ON package_confusion_audit(package_id);
CREATE INDEX idx_audit_severity ON package_confusion_audit(severity);
```

---

## AWS Infrastructure

### Lambda Functions

#### 1. **auth-validator** (Node.js or Python)
- Validates JWT tokens
- Decrements API call counter
- Returns user permissions
- Execution time: < 100ms

#### 2. **api-handler** (Python + FastAPI)
- Handles CRUD endpoints
- Lightweight operations (metadata queries)
- Execution time: < 500ms

#### 3. **search-handler** (Python)
- Executes complex PostgreSQL queries
- Implements pagination
- Execution time: < 1s

### EC2 Instances

#### 1. **package-processor** (t3.medium)
- Unzips packages
- Calculates metrics (CPU intensive)
- Executes Node.js for metric calculations
- Auto-starts when Lambda triggers via SQS

#### 2. **js-sandbox** (t3.micro)
- Executes sensitive model JavaScript validation
- Isolated environment (no network access)
- Terminates after execution

### S3 Buckets

#### 1. **model-registry-packages**
- Structure:
  ```
  /{package_name}/{version}/
    ├── package.zip
    ├── model.safetensors  (optional, for partial downloads)
    ├── config.json
    └── js_policy.js  (for sensitive models)
  ```
- Versioning: Enabled
- Lifecycle policy: Move to Glacier after 90 days

#### 2. **model-registry-logs**
- Stores CloudWatch logs
- Retention: 30 days

### RDS (PostgreSQL)

- Instance type: db.t3.small (initially)
- Multi-AZ: Yes (for high availability)
- Automated backups: Daily
- Connection pooling: PgBouncer

### API Gateway

- REST API
- Endpoints:
  - `/package` (POST, GET)
  - `/packages` (POST - search)
  - `/package/{id}` (GET, DELETE)
  - `/package/{id}/rate` (PUT)
  - `/user` (POST, DELETE)
  - `/reset` (DELETE)
  - `/health` (GET)
- Rate limiting: 100 requests/second per user
- Throttling: 10,000 requests/second total
- Integration: Lambda proxy integration

---

## Authentication Flow

### 1. User Registration (Admin-initiated)
```
Admin → POST /user/register
  ↓
Lambda validates admin token
  ↓
PostgreSQL: INSERT INTO users (username, password_hash, salt)
  ↓
Return user credentials
```

**Implementation:**
```python
@app.post("/user/register")
async def register_user(
    username: str,
    password: str,
    permissions: List[str],
    admin_token: str = Header(...)
):
    admin = verify_token(admin_token)
    if not admin.is_admin:
        raise HTTPException(403, "Admin permission required")

    # Hash password with salt
    salt = secrets.token_hex(16)
    password_hash = bcrypt.hashpw(
        (password + salt).encode(),
        bcrypt.gensalt()
    ).decode()

    # Create user
    user = User(
        username=username,
        password_hash=password_hash,
        salt=salt,
        permissions=json.dumps(permissions)
    )
    db.add(user)
    db.commit()

    return {"user_id": user.id, "username": username}
```

### 2. User Authentication (Login)
```
User → POST /authenticate
  ↓
Lambda validates credentials
  ↓
PostgreSQL: SELECT user WHERE username = ?
  ↓
Verify password hash
  ↓
Generate JWT token (valid for 1000 API calls)
  ↓
INSERT INTO tokens (user_id, token_hash, api_calls_remaining)
  ↓
Return token
```

**Implementation:**
```python
@app.post("/authenticate")
async def authenticate(username: str, password: str):
    user = db.query(User).filter(User.username == username).first()

    if not user:
        raise HTTPException(401, "Invalid credentials")

    # Verify password
    password_hash = bcrypt.hashpw(
        (password + user.salt).encode(),
        user.password_hash.encode()
    )

    if password_hash.decode() != user.password_hash:
        raise HTTPException(401, "Invalid credentials")

    # Generate token
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    # Store token
    db_token = Token(
        user_id=user.id,
        token_hash=token_hash,
        api_calls_remaining=1000
    )
    db.add(db_token)
    db.commit()

    return {"token": token, "calls_remaining": 1000}
```

### 3. Token Validation (Every Request)
```
User → Any API call with token header
  ↓
Lambda: Verify token
  ↓
PostgreSQL: SELECT token WHERE token_hash = ?
  ↓
Check api_calls_remaining > 0
  ↓
UPDATE tokens SET api_calls_remaining = api_calls_remaining - 1
  ↓
Proceed with request
```

---

## Frontend (React) Implementation

### Pages

#### 1. **Dashboard** (`/dashboard`)
- Display:
  - Total packages
  - Recent uploads
  - Popular downloads
  - System health metrics (from CloudWatch)
- Components:
  - `<MetricsCard />`: Shows individual metrics
  - `<PackageList />`: Lists recent packages
  - `<HealthStatus />`: System health indicators

#### 2. **Search** (`/search`)
- Features:
  - Text search input
  - Regex toggle
  - Version filter dropdown
  - Results table with pagination
- Components:
  - `<SearchBar />`: Input and filters
  - `<PackageTable />`: Results display
  - `<Pagination />`: Page controls

#### 3. **Upload** (`/upload`)
- Features:
  - File upload drag-and-drop
  - URL input for HuggingFace/npm
  - Metadata form (name, version, description)
  - Progress indicator
- Components:
  - `<FileUploader />`: Drag-and-drop zone
  - `<URLInput />`: Import from URL
  - `<UploadProgress />`: Processing status

#### 4. **Package Details** (`/package/:id`)
- Display:
  - Metadata (name, version, uploader, date)
  - Metrics scores with visualizations
  - Lineage graph (interactive tree)
  - Download buttons (full/partial)
  - Rating widget
- Components:
  - `<PackageMetadata />`: Info display
  - `<MetricsChart />`: Radar chart for metrics
  - `<LineageTree />`: D3.js tree visualization
  - `<RatingWidget />`: Star rating input

#### 5. **Admin Panel** (`/admin`)
- Features:
  - User management table
  - Register new users
  - Edit permissions
  - Delete users/packages
  - System reset button
- Components:
  - `<UserTable />`: List of users with actions
  - `<PermissionEditor />`: Checkboxes for permissions
  - `<DangerZone />`: Reset button with confirmation

### API Client (Axios)

```javascript
// src/api/client.js
import axios from 'axios';

const apiClient = axios.create({
  baseURL: 'https://api.model-registry.com',
  timeout: 30000,
});

// Request interceptor: Add token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers['X-Auth-Token'] = token;
  }
  return config;
});

// Response interceptor: Handle errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response.status === 401) {
      // Redirect to login
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default apiClient;
```

### Example Component: Upload

```javascript
// src/components/Upload.jsx
import React, { useState } from 'react';
import apiClient from '../api/client';

function Upload() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);

  const handleUpload = async () => {
    setUploading(true);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('name', 'my-model');
    formData.append('version', '1.0.0');

    try {
      const response = await apiClient.post('/package', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      alert('Upload successful! Job ID: ' + response.data.job_id);
    } catch (error) {
      alert('Upload failed: ' + error.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      <input type="file" onChange={(e) => setFile(e.target.files[0])} />
      <button onClick={handleUpload} disabled={!file || uploading}>
        {uploading ? 'Uploading...' : 'Upload Package'}
      </button>
    </div>
  );
}

export default Upload;
```

---

## Security Implementation (Access Control Track)

### 1. Sensitive Models with JavaScript Execution

**Scenario:** A model uploader wants to restrict downloads based on custom logic.

**Implementation:**
```javascript
// Example js_policy.js stored in S3
function validateDownload(MODEL_NAME, UPLOADER, DOWNLOADER, ZIP_PATH) {
  // Custom logic: Only allow downloads by users from the same organization
  const uploaderOrg = UPLOADER.split('@')[1];
  const downloaderOrg = DOWNLOADER.split('@')[1];

  if (uploaderOrg !== downloaderOrg) {
    return {
      approved: false,
      reason: 'Downloader not from same organization'
    };
  }

  // Additional checks: Time-based restrictions
  const currentHour = new Date().getHours();
  if (currentHour < 9 || currentHour > 17) {
    return {
      approved: false,
      reason: 'Downloads only allowed during business hours (9am-5pm)'
    };
  }

  return { approved: true };
}
```

**EC2 Execution:**
```python
# On EC2 instance
import subprocess
import json

def execute_js_policy(policy_path, model_name, uploader, downloader, zip_path):
    # Download JS file from S3
    s3_client.download_file('model-registry-packages', policy_path, '/tmp/policy.js')

    # Execute in Node.js sandbox (no network access)
    js_code = f"""
    const fs = require('fs');
    const policy = require('/tmp/policy.js');
    const result = policy.validateDownload(
        '{model_name}',
        '{uploader}',
        '{downloader}',
        '{zip_path}'
    );
    console.log(JSON.stringify(result));
    """

    # Run in isolated container
    result = subprocess.run(
        ['node', '-e', js_code],
        capture_output=True,
        timeout=5,  # 5 second timeout
        text=True
    )

    return json.loads(result.stdout)
```

### 2. Package Confusion Detection

**Implementation:**
```python
@app.post("/package")
async def upload_package(...):
    # After package is uploaded, check for suspicious patterns

    # 1. Check for similar names (Levenshtein distance)
    existing_packages = db.query(Package.name).all()
    for existing in existing_packages:
        distance = levenshtein_distance(name, existing.name)
        if distance <= 2:  # Very similar names
            # Log audit event
            db.add(PackageConfusionAudit(
                package_id=new_package.id,
                suspicious_pattern=f'Similar to {existing.name}',
                severity='medium'
            ))

    # 2. Check for typosquatting (common libraries)
    popular_packages = ['tensorflow', 'pytorch', 'transformers']
    for popular in popular_packages:
        if levenshtein_distance(name.lower(), popular) <= 2:
            db.add(PackageConfusionAudit(
                package_id=new_package.id,
                suspicious_pattern=f'Typosquatting of {popular}',
                severity='high'
            ))

    # 3. Check download patterns (after first downloads)
    # If package has unusually high downloads in first 24 hours, flag it
```

### 3. Download History Tracking

**Implementation:**
```python
@app.get("/package/{id}/download-history")
async def get_download_history(
    id: str,
    token: str = Header(...)
):
    user = verify_token(token)
    package = db.query(Package).filter(Package.id == id).first()

    # Only uploader or admins can view download history
    if user.id != package.uploader_id and not user.is_admin:
        raise HTTPException(403, "Not authorized")

    history = db.query(DownloadHistory).filter(
        DownloadHistory.package_id == id
    ).order_by(DownloadHistory.timestamp.desc()).all()

    return {
        "package_id": id,
        "downloads": [
            {
                "user": h.user.username,
                "timestamp": h.timestamp.isoformat(),
                "ip": h.ip_address
            }
            for h in history
        ]
    }
```

---

## CI/CD Pipeline (GitHub Actions)

### Workflow: `test.yml`
```yaml
name: Test Pipeline

on:
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install flake8 black mypy
      - run: flake8 . --max-line-length=100
      - run: black --check .
      - run: mypy .

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: pip install bandit
      - run: bandit -r . -f json -o bandit-report.json

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - run: pip install -r requirements.txt
      - run: pytest --cov=. --cov-report=xml
      - name: Check coverage
        run: |
          coverage=$(python -c "import xml.etree.ElementTree as ET; print(ET.parse('coverage.xml').getroot().attrib['line-rate'])")
          if (( $(echo "$coverage < 0.6" | bc -l) )); then
            echo "Coverage $coverage is below 60%"
            exit 1
          fi
```

### Workflow: `deploy.yml`
```yaml
name: Deploy to AWS

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Deploy Lambda functions
        run: |
          zip -r api-handler.zip lambda/
          aws lambda update-function-code \
            --function-name model-registry-api \
            --zip-file fileb://api-handler.zip

      - name: Update EC2 instances
        run: |
          aws ssm send-command \
            --document-name "AWS-RunShellScript" \
            --targets "Key=tag:Name,Values=package-processor" \
            --parameters 'commands=["cd /app && git pull && systemctl restart app"]'
```

---

## Testing Strategy

### 1. Unit Tests (pytest)

**Coverage target:** 60% minimum

**Example: Test metric calculation**
```python
# tests/test_metrics.py
import pytest
from metrics import calculate_bus_factor

def test_calculate_bus_factor_high():
    # Mock GitHub data
    contributors = [
        {'commits': 100},
        {'commits': 90},
        {'commits': 80},
    ]
    assert calculate_bus_factor(contributors) >= 0.8

def test_calculate_bus_factor_low():
    contributors = [
        {'commits': 1000},
        {'commits': 10},
    ]
    assert calculate_bus_factor(contributors) <= 0.3
```

### 2. Integration Tests

**Example: Test full upload flow**
```python
# tests/test_integration.py
import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_upload_package():
    # Register admin
    admin_response = client.post('/user/register', json={
        'username': 'admin',
        'password': 'test123',
        'permissions': ['admin', 'upload']
    }, headers={'X-Auth-Token': 'default_admin_token'})

    # Authenticate
    auth_response = client.post('/authenticate', json={
        'username': 'admin',
        'password': 'test123'
    })
    token = auth_response.json()['token']

    # Upload package
    with open('test_package.zip', 'rb') as f:
        response = client.post('/package', files={'file': f}, headers={
            'X-Auth-Token': token
        })

    assert response.status_code == 200
    assert 'job_id' in response.json()
```

### 3. E2E Tests (Selenium)

**Example: Test UI upload flow**
```python
# tests/test_e2e.py
from selenium import webdriver
from selenium.webdriver.common.by import By

def test_upload_via_ui():
    driver = webdriver.Chrome()
    driver.get('http://localhost:3000')

    # Login
    driver.find_element(By.ID, 'username').send_keys('admin')
    driver.find_element(By.ID, 'password').send_keys('test123')
    driver.find_element(By.ID, 'login-btn').click()

    # Navigate to upload
    driver.find_element(By.LINK_TEXT, 'Upload').click()

    # Upload file
    driver.find_element(By.ID, 'file-input').send_keys('/path/to/test.zip')
    driver.find_element(By.ID, 'upload-btn').click()

    # Verify success message
    success_msg = driver.find_element(By.CLASS_NAME, 'success-message')
    assert 'Upload successful' in success_msg.text

    driver.quit()
```

### 4. ADA Compliance Testing

**Automated checks with axe-core:**
```python
from selenium import webdriver
from axe_selenium_python import Axe

def test_ada_compliance_dashboard():
    driver = webdriver.Chrome()
    driver.get('http://localhost:3000/dashboard')

    axe = Axe(driver)
    axe.inject()
    results = axe.run()

    # Check for WCAG 2.1 Level AA violations
    violations = results['violations']
    assert len(violations) == 0, f"Found {len(violations)} accessibility violations"

    driver.quit()
```

---

## Monitoring and Observability (CloudWatch)

### Metrics to Track

1. **API Metrics**
   - Request count (per endpoint)
   - Response time (p50, p95, p99)
   - Error rate (4xx, 5xx)
   - Token consumption rate

2. **System Metrics**
   - Lambda invocations
   - Lambda duration
   - Lambda errors
   - EC2 CPU/memory usage
   - RDS connections
   - RDS query time
   - S3 GET/PUT requests

3. **Business Metrics**
   - Total packages
   - Daily uploads
   - Daily downloads
   - Active users
   - Search queries

### Dashboard Implementation

**CloudWatch Dashboard JSON:**
```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/Lambda", "Invocations", {"stat": "Sum"}],
          [".", "Errors", {"stat": "Sum"}]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "Lambda Health"
      }
    }
  ]
}
```

### Health Endpoint

**Implementation:**
```python
@app.get("/health")
async def health_check():
    health = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {}
    }

    # Check PostgreSQL
    try:
        db.execute("SELECT 1")
        health["components"]["database"] = "healthy"
    except Exception as e:
        health["components"]["database"] = f"unhealthy: {str(e)}"
        health["status"] = "degraded"

    # Check S3
    try:
        s3_client.head_bucket(Bucket='model-registry-packages')
        health["components"]["s3"] = "healthy"
    except Exception as e:
        health["components"]["s3"] = f"unhealthy: {str(e)}"
        health["status"] = "degraded"

    # Get CloudWatch metrics
    try:
        cloudwatch = boto3.client('cloudwatch')
        response = cloudwatch.get_metric_statistics(
            Namespace='AWS/Lambda',
            MetricName='Invocations',
            StartTime=datetime.now() - timedelta(minutes=5),
            EndTime=datetime.now(),
            Period=300,
            Statistics=['Sum']
        )
        health["metrics"] = {
            "lambda_invocations_5min": response['Datapoints'][0]['Sum']
        }
    except Exception as e:
        health["metrics"] = {}

    return health
```

---

## Cost Estimation

### Monthly AWS Costs (Estimated)

| Service | Usage | Cost |
|---------|-------|------|
| Lambda | 1M requests, 500ms avg | $5 |
| EC2 (t3.medium) | 1 instance, on-demand | $30 |
| RDS (db.t3.small) | Single-AZ | $25 |
| S3 | 100GB storage, 10k requests | $3 |
| API Gateway | 1M requests | $4 |
| CloudWatch | Logs + metrics | $10 |
| **Total** | | **~$77/month** |

**Optimization strategies:**
- Use Lambda for most operations (cheaper than EC2)
- Reserved instances for RDS (save 40%)
- S3 lifecycle policies (move old packages to Glacier)
- EC2 auto-scaling (only run when needed)

---

## Summary

This implementation plan provides a comprehensive blueprint for CRUD operations using:

1. **FastAPI** for REST API development with automatic OpenAPI docs
2. **PostgreSQL (RDS)** for structured metadata with ACID compliance
3. **AWS S3** for scalable object storage
4. **Lambda + EC2** for compute (lightweight + heavy tasks)
5. **API Gateway** for routing and rate limiting
6. **React** for modern, accessible frontend
7. **GitHub Actions** for CI/CD automation
8. **CloudWatch** for monitoring and observability

The architecture separates concerns:
- **Lambda**: Fast, stateless operations (auth, search, metadata)
- **EC2**: CPU-intensive tasks (metrics, JS execution)
- **PostgreSQL**: Structured queries (lineage, search)
- **S3**: Binary storage (packages, weights)

This design ensures:
- **Scalability**: Lambda auto-scales, EC2 can be scaled
- **Security**: Token-based auth, permission system, JS sandboxing
- **Performance**: Pagination, caching, signed URLs
- **Cost-efficiency**: Pay-per-use Lambda, reserved RDS
- **Observability**: CloudWatch metrics, logs, dashboards