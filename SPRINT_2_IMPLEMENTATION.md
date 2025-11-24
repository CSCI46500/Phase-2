# Sprint 2 Implementation Guide - Developer A

## Task 1: Download Sub-Aspects (Component Downloads)

### Step 1: Update GET /package/{id} endpoint

**File:** `src/api/main.py` (around line 536)

**Changes needed:**
1. Add `component: str = "full"` parameter
2. Add validation for component types
3. Call new S3 helper method for component downloads

```python
@app.get("/package/{package_id}")
async def get_package(
    package_id: UUID,
    component: str = "full",  # NEW: Options: "full", "weights", "datasets", "code"
    user: User = Depends(require_permission("download")),
    db: Session = Depends(get_db),
    request: Request = None
):
    """
    Download a package or specific components.
    
    Query Parameters:
    - component: "full" (default), "weights", "datasets", or "code"
    """
    # Validate component parameter
    valid_components = ["full", "weights", "datasets", "code"]
    if component not in valid_components:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid component. Must be one of: {', '.join(valid_components)}"
        )
    
    package = crud.get_package_by_id(db, package_id)
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    # Log download
    ip_address = request.client.host if request else None
    user_agent = request.headers.get("user-agent") if request else None
    crud.log_download(db, package_id, user.id, ip_address, user_agent)
    
    # Extract S3 key from s3:// URL
    s3_key = package.s3_path.replace(f"s3://{s3_helper.bucket_name}/", "")
    
    # For full package, return direct presigned URL
    if component == "full":
        presigned_url = s3_helper.generate_presigned_url(s3_key, expiration=300)
    else:
        # For component downloads, create a filtered zip
        presigned_url = s3_helper.generate_component_download_url(
            s3_key,
            component,
            package.name,
            package.version,
            expiration=300
        )
    
    if not presigned_url:
        raise HTTPException(status_code=500, detail="Failed to generate download URL")
    
    return {
        "package_id": str(package_id),
        "name": package.name,
        "version": package.version,
        "component": component,  # NEW
        "download_url": presigned_url,
        "expires_in_seconds": 300
    }
```

### Step 2: Add component download methods to S3 service

**File:** `src/services/s3_service.py`

**Add these imports at the top:**
```python
import zipfile
import tempfile
import io
from typing import List
```

**Add these new methods to S3Helper class:**

```python
def _get_component_file_patterns(self, component: str) -> List[str]:
    """
    Get file patterns for each component type.
    Returns list of patterns to match files in the zip.
    """
    patterns = {
        "weights": [
            "*.pth", "*.pt", "*.bin", "*.safetensors", "*.ckpt",
            "*.h5", "*.pb", "*.onnx", "*.tflite",  
            "pytorch_model.bin", "model.safetensors",
            "**/pytorch_model*.bin", "**/model*.safetensors"
        ],
        "datasets": [
            "*.csv", "*.json", "*.jsonl", "*.parquet", "*.arrow",
            "*.txt", "data/*", "dataset/*", "datasets/*",
            "**/data/**", "**/dataset/**", "**/datasets/**"
        ],
        "code": [
            "*.py", "*.ipynb", "*.sh", "*.yaml", "*.yml",
            "*.md", "README*", "requirements.txt", "setup.py",
            "*.cfg", "*.ini", "*.toml"
        ]
    }
    return patterns.get(component, [])

def _matches_component_pattern(self, filename: str, component: str) -> bool:
    """Check if filename matches component patterns."""
    import fnmatch
    patterns = self._get_component_file_patterns(component)
    
    for pattern in patterns:
        if fnmatch.fnmatch(filename.lower(), pattern.lower()):
            return True
        # Also check just the basename
        if fnmatch.fnmatch(os.path.basename(filename).lower(), pattern.lower()):
            return True
    return False

def generate_component_download_url(
    self,
    s3_key: str,
    component: str,
    package_name: str,
    version: str,
    expiration: int = 300
) -> Optional[str]:
    """
    Generate presigned URL for component-specific download.
    Downloads the full zip, extracts matching files, creates new zip, uploads temporarily.
    
    Args:
        s3_key: S3 object key for full package
        component: Component type ("weights", "datasets", "code")
        package_name: Package name for temp file naming
        version: Package version
        expiration: URL expiration time in seconds
        
    Returns:
        Presigned URL or None if failed
    """
    try:
        # Download the full package to memory
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_download:
            self.s3_client.download_fileobj(
                self.bucket_name,
                s3_key,
                temp_download
            )
            temp_download_path = temp_download.name
        
        # Create filtered zip with only component files
        temp_component_path = tempfile.mktemp(suffix=f"_{component}.zip")
        
        with zipfile.ZipFile(temp_download_path, 'r') as source_zip:
            with zipfile.ZipFile(temp_component_path, 'w', zipfile.ZIP_DEFLATED) as target_zip:
                # Filter and copy matching files
                matched_files = []
                for file_info in source_zip.filelist:
                    if self._matches_component_pattern(file_info.filename, component):
                        data = source_zip.read(file_info.filename)
                        target_zip.writestr(file_info, data)
                        matched_files.append(file_info.filename)
                
                logger.info(f"Component '{component}': matched {len(matched_files)} files")
                
                if not matched_files:
                    logger.warning(f"No files matched component '{component}'")
                    # Still create zip with a note
                    target_zip.writestr(
                        "README.txt",
                        f"No {component} files found in this package.\\n"
                    )
        
        # Upload component zip to temporary S3 location
        component_s3_key = f"temp/{package_name}/{version}/{component}.zip"
        
        with open(temp_component_path, 'rb') as f:
            self.s3_client.upload_fileobj(f, self.bucket_name, component_s3_key)
        
        # Clean up temp files
        os.unlink(temp_download_path)
        os.unlink(temp_component_path)
        
        # Generate presigned URL for component zip
        url = self.s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket_name, 'Key': component_s3_key},
            ExpiresIn=expiration
        )
        
        logger.info(f"Generated component download URL for: {component_s3_key}")
        return url
        
    except Exception as e:
        logger.error(f"Failed to generate component download URL: {e}")
        return None
```

### Step 3: Test the implementation

**Test commands:**
```bash
# 1. Get auth token
curl -X POST http://localhost:8000/authenticate \
  -H "Content-Type: application/json" \
  -d @/tmp/auth_test.json

# 2. Upload a test package first (or use existing package ID)

# 3. Download full package
curl "http://localhost:8000/package/{PACKAGE_ID}?component=full" \
  -H "Authorization: Bearer {TOKEN}"

# 4. Download only weights
curl "http://localhost:8000/package/{PACKAGE_ID}?component=weights" \
  -H "Authorization: Bearer {TOKEN}"

# 5. Download only datasets
curl "http://localhost:8000/package/{PACKAGE_ID}?component=datasets" \
  -H "Authorization: Bearer {TOKEN}"

# 6. Download only code
curl "http://localhost:8000/package/{PACKAGE_ID}?component=code" \
  -H "Authorization: Bearer {TOKEN}"
```

---

## Task 2: License Compatibility Checker

### Step 1: Research ModelGo paper

**Quick summary** of license compatibility:
- **MIT, BSD, Apache 2.0:** Very permissive, compatible with almost everything
- **GPL v2/v3:** Restrictive, requires derivative works to also be GPL
- **LGPL:** Like GPL but allows dynamic linking
- **CC BY:** Attribution required
- **Proprietary:** Case-by-case analysis needed

**Compatibility matrix for fine-tuning + inference:**

| Model License | Code License | Compatible? | Notes |
|--------------|--------------|-------------|-------|
| MIT | Any | ✅ Yes | MIT is very permissive |
| Apache 2.0 | Any | ✅ Yes | Apache is permissive |
| BSD | Any | ✅ Yes | BSD is permissive |
| GPL v3 | GPL v3 | ✅ Yes | Must use GPL |
| GPL v3 | MIT/BSD/Apache | ❌ No | GPL requires GPL |
| MIT | GPL v3 | ⚠️ Depends | Can use but result is GPL |
| CC BY 4.0 | Any | ✅ Yes | Just need attribution |
| Proprietary | Any | ❌ Maybe | Check specific license |

### Step 2: Create license compatibility module

**Create new file:** `src/utils/license_compatibility.py`

```python
"""
License compatibility checker for model fine-tuning and inference.
Based on ModelGo paper and common open-source license interactions.
"""
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class LicenseCompatibilityChecker:
    """Check compatibility between model and code licenses."""
    
    # License categories
    PERMISSIVE = {"mit", "bsd", "bsd-2-clause", "bsd-3-clause", "apache-2.0", "apache"}
    COPYLEFT_WEAK = {"lgpl", "lgpl-2.1", "lgpl-3.0", "mpl", "mpl-2.0"}
    COPYLEFT_STRONG = {"gpl", "gpl-2.0", "gpl-3.0", "agpl", "agpl-3.0"}
    CREATIVE_COMMONS = {"cc-by", "cc-by-4.0", "cc-by-sa", "cc-by-sa-4.0", "cc0"}
    PROPRIETARY = {"proprietary", "commercial", "custom"}
    
    def __init__(self):
        """Initialize the compatibility checker."""
        pass
    
    def normalize_license(self, license_str: str) -> str:
        """Normalize license string to standard format."""
        if not license_str:
            return "unknown"
        
        # Convert to lowercase and remove common variations
        license_str = license_str.lower().strip()
        license_str = license_str.replace("license", "").replace("licence", "").strip()
        license_str = license_str.replace(" ", "-")
        license_str = license_str.replace("_", "-")
        
        # Map common variations
        mappings = {
            "apache2": "apache-2.0",
            "apache-2": "apache-2.0",
            "gpl2": "gpl-2.0",
            "gpl3": "gpl-3.0",
            "lgpl2.1": "lgpl-2.1",
            "lgpl3": "lgpl-3.0",
            "bsd2": "bsd-2-clause",
            "bsd3": "bsd-3-clause",
            "ccby": "cc-by-4.0",
            "cc-by": "cc-by-4.0",
        }
        
        return mappings.get(license_str, license_str)
    
    def get_license_category(self, license_str: str) -> str:
        """Categorize a license."""
        normalized = self.normalize_license(license_str)
        
        if normalized in self.PERMISSIVE:
            return "permissive"
        elif normalized in self.COPYLEFT_WEAK:
            return "copyleft_weak"
        elif normalized in self.COPYLEFT_STRONG:
            return "copyleft_strong"
        elif normalized in self.CREATIVE_COMMONS:
            return "creative_commons"
        elif normalized in self.PROPRIETARY:
            return "proprietary"
        else:
            return "unknown"
    
    def check_compatibility(
        self,
        model_license: str,
        code_license: str,
        use_case: str = "fine-tune+inference"
    ) -> Tuple[bool, str]:
        """
        Check if model and code licenses are compatible.
        
        Args:
            model_license: License of the model
            code_license: License of the fine-tuning code
            use_case: Type of use (default: "fine-tune+inference")
            
        Returns:
            Tuple of (is_compatible: bool, explanation: str)
        """
        model_norm = self.normalize_license(model_license)
        code_norm = self.normalize_license(code_license)
        
        model_cat = self.get_license_category(model_norm)
        code_cat = self.get_license_category(code_norm)
        
        logger.info(f"Checking compatibility: model={model_norm} ({model_cat}) "
                   f"vs code={code_norm} ({code_cat})")
        
        # Unknown licenses - conservative approach
        if model_cat == "unknown" or code_cat == "unknown":
            return (False, 
                   f"Cannot determine compatibility: model license '{model_license}' "
                   f"or code license '{code_license}' is unknown. "
                   f"Please review licenses manually.")
        
        # Both permissive - always compatible
        if model_cat == "permissive" and code_cat == "permissive":
            return (True,
                   f"Both licenses are permissive ({model_norm} and {code_norm}). "
                   f"Fully compatible for {use_case}.")
        
        # Permissive model with any code - compatible
        if model_cat == "permissive":
            return (True,
                   f"Model uses permissive license ({model_norm}), compatible with "
                   f"code license ({code_norm}) for {use_case}.")
        
        # Strong copyleft model requires strong copyleft code
        if model_cat == "copyleft_strong":
            if code_cat == "copyleft_strong" and model_norm == code_norm:
                return (True,
                       f"Both use same copyleft license ({model_norm}). Compatible.")
            elif code_cat == "permissive":
                return (False,
                       f"Model uses copyleft license ({model_norm}) which requires "
                       f"derivative works to use the same license. Code license "
                       f"({code_norm}) is permissive. Result must be {model_norm}.")
            else:
                return (False,
                       f"License mismatch: model ({model_norm}) and code ({code_norm}) "
                       f"are incompatible. Copyleft licenses require matching licenses.")
        
        # Weak copyleft (LGPL) - allows dynamic linking with permissive
        if model_cat == "copyleft_weak":
            if code_cat in ["permissive", "copyleft_weak"]:
                return (True,
                       f"Model uses weak copyleft ({model_norm}), compatible with "
                       f"code license ({code_norm}) for {use_case}.")
            else:
                return (False,
                       f"Model license ({model_norm}) incompatible with code license "
                       f"({code_norm}).")
        
        # Creative Commons licenses
        if model_cat == "creative_commons":
            if "sa" in model_norm:  # Share-Alike
                return (False,
                       f"Model uses Creative Commons Share-Alike ({model_norm}), "
                       f"which may require derivative works to use compatible license. "
                       f"Review compatibility with code license ({code_norm}) manually.")
            else:
                return (True,
                       f"Model uses Creative Commons ({model_norm}). Generally compatible "
                       f"with proper attribution. Verify code license ({code_norm}) allows this.")
        
        # Proprietary licenses
        if model_cat == "proprietary" or code_cat == "proprietary":
            return (False,
                   f"Proprietary licenses detected. Model: {model_license}, "
                   f"Code: {code_license}. Manual review required.")
        
        # Default: conservative
        return (False,
               f"Cannot automatically determine compatibility between model license "
               f"({model_license}) and code license ({code_license}). Manual review recommended.")


# Global instance
license_checker = LicenseCompatibilityChecker()
```

### Step 3: Add POST /package/license-check endpoint

**File:** `src/api/main.py`

**Add this import:**
```python
from src.utils.license_compatibility import license_checker
```

**Add this endpoint (around line 800+):**
```python
@app.post("/package/license-check")
async def check_license_compatibility(
    request: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check license compatibility between a model and GitHub project.
    
    Request body:
    {
        "model_id": "uuid-of-model",
        "github_url": "https://github.com/user/repo"
    }
    
    Returns compatibility status and explanation.
    """
    model_id = request.get("model_id")
    github_url = request.get("github_url")
    
    if not model_id or not github_url:
        raise HTTPException(
            status_code=400,
            detail="Both 'model_id' and 'github_url' are required"
        )
    
    # Get model package
    try:
        package_uuid = UUID(model_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid model_id format")
    
    package = crud.get_package_by_id(db, package_uuid)
    if not package:
        raise HTTPException(status_code=404, detail="Model not found")
    
    # Extract GitHub repo from URL
    # Expected format: https://github.com/owner/repo
    import re
    github_pattern = r'github\.com/([^/]+)/([^/]+)'
    match = re.search(github_pattern, github_url)
    
    if not match:
        raise HTTPException(
            status_code=400,
            detail="Invalid GitHub URL format. Expected: https://github.com/owner/repo"
        )
    
    owner, repo = match.groups()
    repo = repo.rstrip('.git')  # Remove .git if present
    
    # Fetch GitHub license using GitHub API
    try:
        import requests
        github_api_url = f"https://api.github.com/repos/{owner}/{repo}/license"
        headers = {}
        
        # Use GitHub token if available
        github_token = os.getenv("GITHUB_TOKEN")
        if github_token:
            headers["Authorization"] = f"token {github_token}"
        
        response = requests.get(github_api_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            license_data = response.json()
            github_license = license_data.get("license", {}).get("spdx_id", "Unknown")
        elif response.status_code == 404:
            github_license = "No license found"
        else:
            github_license = "Unknown (API error)"
            
    except Exception as e:
        logger.warning(f"Failed to fetch GitHub license: {e}")
        github_license = "Unknown (fetch failed)"
    
    # Check compatibility
    is_compatible, explanation = license_checker.check_compatibility(
        model_license=package.license or "Unknown",
        code_license=github_license,
        use_case="fine-tune+inference"
    )
    
    return {
        "model_id": str(package_uuid),
        "model_name": package.name,
        "model_license": package.license or "Unknown",
        "github_url": github_url,
        "github_license": github_license,
        "compatible": is_compatible,
        "explanation": explanation,
        "recommendation": (
            "Proceed with fine-tuning and inference." if is_compatible
            else "Manual license review required before proceeding."
        )
    }
```

### Step 4: Add tests

**Create:** `tests/test_license_compatibility.py`

```python
"""Tests for license compatibility checker."""
import pytest
from src.utils.license_compatibility import LicenseCompatibilityChecker


def test_normalize_license():
    """Test license normalization."""
    checker = LicenseCompatibilityChecker()
    
    assert checker.normalize_license("MIT") == "mit"
    assert checker.normalize_license("Apache 2.0") == "apache-2.0"
    assert checker.normalize_license("GPL-3.0") == "gpl-3.0"
    assert checker.normalize_license("BSD 3-Clause") == "bsd-3-clause"


def test_permissive_licenses_compatible():
    """Test that permissive licenses are compatible."""
    checker = LicenseCompatibilityChecker()
    
    compatible, explanation = checker.check_compatibility("MIT", "Apache 2.0")
    assert compatible == True
    
    compatible, explanation = checker.check_compatibility("BSD", "MIT")
    assert compatible == True


def test_gpl_incompatible_with_permissive():
    """Test that GPL is incompatible with permissive licenses."""
    checker = LicenseCompatibilityChecker()
    
    compatible, explanation = checker.check_compatibility("GPL-3.0", "MIT")
    assert compatible == False
    assert "copyleft" in explanation.lower()


def test_same_gpl_compatible():
    """Test that same GPL versions are compatible."""
    checker = LicenseCompatibilityChecker()
    
    compatible, explanation = checker.check_compatibility("GPL-3.0", "GPL-3.0")
    assert compatible == True


def test_unknown_license_not_compatible():
    """Test that unknown licenses are not automatically compatible."""
    checker = LicenseCompatibilityChecker()
    
    compatible, explanation = checker.check_compatibility("CustomLicense", "MIT")
    assert compatible == False
    assert "unknown" in explanation.lower()
```

---

## Task 3: TreeScore Real Implementation

### Step 1: Update TreescoreMetric class

**File:** `src/utils/metric_calculators.py`

**Find the TreescoreMetric class and update:**

```python
class TreescoreMetric:
    """Calculate average net score of parent models."""
    
    def calculate(self, fetcher: DataFetcher) -> Tuple[float, int]:
        """
        Calculate tree score as average of parent model scores.
        Requires database access to query lineage.
        """
        start_time = time.time()
        
        try:
            # Import here to avoid circular dependency
            from src.core.database import SessionLocal
            from src.crud import package as package_crud
            
            # Get current package ID from metadata
            metadata = fetcher.get_metadata()
            package_name = metadata.get("modelId", "")
            
            if not package_name:
                logger.warning("TreeScore: No package name in metadata")
                return 0.0, int((time.time() - start_time) * 1000)
            
            # Query database for parent packages
            db = SessionLocal()
            try:
                # Find package by name
                package = db.query(package_crud.Package).filter(
                    package_crud.Package.name == package_name
                ).first()
                
                if not package:
                    logger.info(f"TreeScore: Package '{package_name}' not in database yet")
                    return 0.5, int((time.time() - start_time) * 1000)
                
                # Get parent packages from lineage
                parent_scores = []
                lineage = package_crud.get_package_lineage(db, package.id)
                
                # Track visited to avoid cycles
                visited = set()
                
                def get_parent_scores(pkg_id, depth=0, max_depth=5):
                    """Recursively get parent scores, avoiding cycles."""
                    if depth > max_depth or pkg_id in visited:
                        return
                    
                    visited.add(pkg_id)
                    
                    # Get direct parents
                    parents = db.query(package_crud.Lineage).filter(
                        package_crud.Lineage.child_id == pkg_id
                    ).all()
                    
                    for parent_rel in parents:
                        parent_pkg = db.query(package_crud.Package).filter(
                            package_crud.Package.id == parent_rel.parent_id
                        ).first()
                        
                        if parent_pkg:
                            # Get metrics for parent
                            metrics = package_crud.get_package_metrics(db, parent_pkg.id)
                            if metrics and metrics.net_score is not None:
                                parent_scores.append(metrics.net_score)
                                logger.debug(f"TreeScore: Parent '{parent_pkg.name}' score: {metrics.net_score}")
                            
                            # Recursively get grandparents
                            get_parent_scores(parent_pkg.id, depth + 1, max_depth)
                
                # Start recursive collection
                get_parent_scores(package.id)
                
                if parent_scores:
                    avg_score = sum(parent_scores) / len(parent_scores)
                    logger.info(f"TreeScore: Averaged {len(parent_scores)} parent scores = {avg_score:.2f}")
                    return round(avg_score, 2), int((time.time() - start_time) * 1000)
                else:
                    logger.info("TreeScore: No parents found, using default 0.5")
                    return 0.5, int((time.time() - start_time) * 1000)
                    
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"TreeScore calculation failed: {e}")
            return 0.5, int((time.time() - start_time) * 1000)
```

### Step 2: Ensure lineage is captured during upload

**File:** `src/api/main.py`

**In the package upload endpoint, ensure parent_ids are captured:**

```python
# When uploading, check config.json for parent models
config = metadata.get("config", {})
parent_model = config.get("_name_or_path") or config.get("base_model")

if parent_model:
    # Try to find parent in database
    parent_pkg = crud.get_package_by_name(db, parent_model)
    if parent_pkg:
        # Create lineage relationship
        crud.create_lineage(db, package.id, parent_pkg.id)
        logger.info(f"Created lineage: {package.name} -> {parent_pkg.name}")
```

---

## Testing Sprint 2

### Test Component Downloads
```bash
# Upload a test package
curl -X POST http://localhost:8000/package \
  -H "Authorization: Bearer $TOKEN" \
  -F "package=@test_model.zip"

# Download different components
curl "http://localhost:8000/package/$PACKAGE_ID?component=weights" \
  -H "Authorization: Bearer $TOKEN" -o weights.zip

curl "http://localhost:8000/package/$PACKAGE_ID?component=code" \
  -H "Authorization: Bearer $TOKEN" -o code.zip
```

### Test License Compatibility
```bash
curl -X POST http://localhost:8000/package/license-check \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "your-model-uuid",
    "github_url": "https://github.com/huggingface/transformers"
  }'
```

### Test TreeScore
```bash
# Upload a parent model
# Upload a child model with parent reference in config.json
# Check that TreeScore reflects parent's net score
curl "http://localhost:8000/package/$CHILD_ID/metadata" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Estimated Time
- Component Downloads: 4-5 hours ✓
- License Compatibility: 6-8 hours ✓  
- TreeScore Implementation: 3-4 hours ✓

**Total: 13-17 hours**

Good luck with Sprint 2! 🚀
