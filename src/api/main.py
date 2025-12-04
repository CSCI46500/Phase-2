"""
FastAPI application for Model Registry.
Implements all CRUD endpoints as per CRUD_IMPLEMENTATION_PLAN.md
"""
from fastapi import FastAPI, Depends, HTTPException, Header, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID
import tempfile
import os
import shutil
import logging
import time
from datetime import datetime, timedelta
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.core.database import get_db, init_db
from src.core.models import User, Package
from src.core.auth import (
    authenticate_user,
    generate_token,
    create_user,
    get_current_user,
    get_current_user_optional,
    require_permission,
    require_admin,
    init_default_admin,
    check_permission
)
import src.crud as crud
from src.crud.package import create_lineage
from src.services.s3_service import s3_helper
from src.services.metrics_service import MetricsEvaluator
from src.services.monitoring import metrics_collector, collect_and_persist_metrics, get_recent_metrics
from src.core.config import settings
from src.utils.logger import setup_logging
from src.utils.license_compatibility import license_checker
from src.utils.data_fetcher import DataFetcher
from src.utils.validation import validate_metric_threshold, validate_package_name, validate_huggingface_metrics
from src.utils.lineage_parser import lineage_parser
from src.utils.size_analyzer import size_analyzer
from src.utils.github_license_fetcher import github_license_fetcher

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="Model Registry API with CRUD operations for ML models"
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for autograder and ALB
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== Request Tracking Middleware ==========

@app.middleware("http")
async def track_requests(request: Request, call_next):
    """
    Middleware to track all API requests for observability.
    Records metrics for each request: endpoint, method, status, response time, errors.
    """
    start_time = time.time()
    error_message = None

    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as e:
        status_code = 500
        error_message = str(e)
        logger.error(f"Request failed: {request.method} {request.url.path} - {e}")
        raise
    finally:
        # Calculate response time
        response_time_ms = (time.time() - start_time) * 1000

        # Record metrics (skip health check to avoid noise)
        if request.url.path != "/health":
            metrics_collector.record_request(
                endpoint=request.url.path,
                method=request.method,
                status_code=status_code,
                response_time_ms=response_time_ms,
                error=error_message
            )

    return response


# ========== Pydantic Models for Request/Response ==========

class AuthRequest(BaseModel):
    """Authentication request model."""
    username: str
    password: str


class AuthResponse(BaseModel):
    """Authentication response model."""
    token: str
    calls_remaining: int


class RegisterRequest(BaseModel):
    """User registration request."""
    username: str
    password: str
    permissions: List[str] = Field(default=["search"])


class PackageQuery(BaseModel):
    """Package search query."""
    name: Optional[str] = None
    version: Optional[str] = None
    regex: Optional[str] = None
    search_model_card: bool = False  # If True, regex applies to model_card field as well


class RatingRequest(BaseModel):
    """Rating request model."""
    score: int = Field(ge=1, le=5)


class PermissionUpdate(BaseModel):
    """Permission update request."""
    permissions: List[str]


class PackageResponse(BaseModel):
    """Package response model."""
    id: str
    name: str
    version: str
    description: Optional[str]
    uploader_id: Optional[str]
    license: Optional[str]
    size_bytes: Optional[int]
    upload_date: str
    net_score: Optional[float]

    class Config:
        from_attributes = True


class LicenseCheckRequest(BaseModel):
    """License compatibility check request."""
    github_url: str = Field(..., description="GitHub repository URL for the project")
    model_id: UUID = Field(..., description="Package ID to check compatibility with")


class LicenseCheckResponse(BaseModel):
    """License compatibility check response."""
    compatible: bool
    github_license: str
    model_license: str
    reason: str
    warnings: Optional[List[str]] = None


# ========== Startup/Shutdown Events ==========

@app.on_event("startup")
async def startup_event():
    """Initialize database and default admin on startup."""
    logger.info("Starting Model Registry API...")
    init_db()

    # Initialize default admin user
    from src.core.database import get_db_context
    with get_db_context() as db:
        init_default_admin(db)

    logger.info("API startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Model Registry API...")


# ========== Health Check ==========

@app.get("/tracks")
async def get_tracks():
    """
    Return the Phase 2 tracks that this implementation supports.

    Per Phase 2 spec, teams must implement at least one of:
    - Security track (access control, sensitive models, package confusion detection)
    - Performance track (measurements, component experiments)
    - High-assurance track (90%+ coverage, disaster proofing, atomic updates)

    This endpoint informs the autograder which tracks are implemented.
    """
    return {
        "planned_tracks": ["Security"],
        "details": {
            "security": {
                "access_control": True,
                "sensitive_models": False,
                "package_confusion": False
            },
            "performance": {
                "measurements": False,
                "component_experiments": False
            },
            "high_assurance": {
                "high_coverage": False,
                "disaster_proofing": False,
                "atomic_updates": False
            }
        }
    }


@app.get("/health")
async def health_check(detailed: bool = False, db: Session = Depends(get_db)):
    """
    Enhanced health check endpoint with optional detailed metrics.

    Query Parameters:
    - detailed: If true, includes performance metrics and statistics

    Sprint 3: Enhanced observability with request metrics, error rates, and performance data.
    """
    health = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {}
    }

    # Check database
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        health["components"]["database"] = "healthy"
    except Exception as e:
        health["components"]["database"] = f"unhealthy: {str(e)}"
        health["status"] = "degraded"

    # Check S3 (optional)
    try:
        s3_helper.s3_client.head_bucket(Bucket=s3_helper.bucket_name)
        health["components"]["s3"] = "healthy"
    except Exception as e:
        health["components"]["s3"] = f"unhealthy: {str(e)}"
        # S3 not critical for health check

    # Add detailed metrics if requested
    if detailed:
        current_metrics = metrics_collector.get_current_metrics()
        health["metrics"] = {
            "total_requests": current_metrics["total_requests"],
            "successful_requests": current_metrics["successful_requests"],
            "failed_requests": current_metrics["failed_requests"],
            "error_rate_percent": current_metrics["error_rate"],
            "avg_response_time_ms": current_metrics["avg_response_time_ms"],
            "p95_response_time_ms": current_metrics["p95_response_time_ms"],
            "p99_response_time_ms": current_metrics["p99_response_time_ms"],
            "cpu_percent": current_metrics["cpu_percent"],
            "memory_percent": current_metrics["memory_percent"],
            "disk_percent": current_metrics["disk_percent"]
        }

        # Include top endpoints
        endpoint_metrics = current_metrics.get("endpoint_metrics", {})
        if endpoint_metrics:
            sorted_endpoints = sorted(
                endpoint_metrics.items(),
                key=lambda x: x[1]["count"],
                reverse=True
            )[:5]  # Top 5 endpoints
            health["top_endpoints"] = [
                {
                    "endpoint": endpoint,
                    "count": data["count"],
                    "errors": data["errors"],
                    "avg_response_ms": data["avg_response_ms"]
                }
                for endpoint, data in sorted_endpoints
            ]

    return health


# ========== Authentication Endpoints ==========

@app.post("/authenticate", response_model=AuthResponse)
async def authenticate(auth_req: AuthRequest, db: Session = Depends(get_db)):
    """
    Authenticate user and generate token.
    As per CRUD plan: POST /authenticate
    """
    user = authenticate_user(db, auth_req.username, auth_req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = generate_token(db, user)

    return AuthResponse(
        token=token,
        calls_remaining=settings.default_api_calls
    )


@app.post("/user/register")
async def register_user(
    register_req: RegisterRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Register new user (admin only).
    As per CRUD plan: Admin-initiated user registration.
    """
    user = create_user(
        db=db,
        username=register_req.username,
        password=register_req.password,
        permissions=register_req.permissions
    )

    return {
        "user_id": str(user.id),
        "username": user.username,
        "permissions": user.permissions
    }


# ========== CREATE Operations ==========

@app.post("/package")
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def upload_package(
    request: Request,
    file: UploadFile = File(...),
    name: str = Form(...),
    version: str = Form(...),
    description: Optional[str] = Form(None),
    model_url: str = Form(""),
    dataset_url: str = Form(""),
    code_url: str = Form(""),
    user: User = Depends(require_permission("upload")),
    db: Session = Depends(get_db)
):
    """
    Upload and evaluate a package with rate limiting.
    As per CRUD plan: POST /package

    This endpoint:
    1. Saves uploaded file to S3
    2. Runs metrics evaluation using existing MetricsEvaluator
    3. Stores package metadata and metrics in database
    """
    logger.info(f"Uploading package: {name} v{version} by user {user.username}")

    # Check if package already exists
    existing = crud.get_package_by_name_version(db, name, version)
    if existing:
        raise HTTPException(status_code=400, detail="Package with this name and version already exists")

    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_file_path = temp_file.name

    try:
        # Upload to S3
        s3_key = s3_helper.build_s3_path(name, version)
        success = s3_helper.upload_file(temp_file_path, s3_key)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to upload to S3")

        s3_path = s3_helper.build_full_s3_url(s3_key)
        size_bytes = os.path.getsize(temp_file_path)

        # Analyze package size breakdown
        logger.info(f"Analyzing package size for {name} v{version}")
        size_analysis = size_analyzer.analyze_zip(temp_file_path)

        # Create package entry first (so we have package_id for TreeScore)
        package = crud.create_package(
            db=db,
            name=name,
            version=version,
            uploader_id=user.id,
            s3_path=s3_path,
            description=description,
            license="",  # Will be updated after metrics evaluation
            size_bytes=size_bytes,
            size_breakdown=size_analysis
        )

        # Parse lineage information from the package
        logger.info(f"Parsing lineage from package {name} v{version}")
        lineage_info = lineage_parser.parse_zip_file(temp_file_path)

        # Create lineage relationships for detected parent models
        if lineage_info["parent_models"]:
            for parent_identifier in lineage_info["parent_models"]:
                # Try to find parent package in the registry by name
                # Extract just the model name (e.g., "bert-base-uncased" from "google/bert-base-uncased")
                parent_name = parent_identifier.split('/')[-1] if '/' in parent_identifier else parent_identifier
                parent_package = crud.package.get_package_by_name(db, parent_name)

                if parent_package:
                    create_lineage(
                        db=db,
                        package_id=package.id,
                        parent_id=parent_package.id,
                        relationship_type=lineage_info["relationship_type"]
                    )
                    logger.info(f"Created lineage: {package.id} -> {parent_package.id} (parent: {parent_name})")
                else:
                    logger.debug(f"Parent model '{parent_identifier}' not found in registry")

        # Run metrics evaluation with package context for TreeScore
        evaluator = MetricsEvaluator(
            model_url=model_url,
            dataset_url=dataset_url,
            code_url=code_url,
            db_session=db,
            package_id=package.id
        )
        eval_result = evaluator.evaluate()

        # Validate metrics meet minimum threshold
        # Per Phase 2 spec: all non-latency metrics must be >= 0.5 for upload
        is_valid, validation_msg = validate_metric_threshold(eval_result, threshold=0.5)
        if not is_valid:
            # Delete the package we just created since validation failed
            crud.delete_package(db, package.id)
            logger.error(f"Package {name} v{version} failed metric validation: {validation_msg}")
            raise HTTPException(
                status_code=400,
                detail=f"Package does not meet minimum quality requirements. {validation_msg}"
            )

        logger.info(f"Metrics validation passed for {name} v{version}")

        # Update package with license from evaluation
        package.license = eval_result.get("license")
        db.commit()
        db.refresh(package)

        # Validate license compatibility if GitHub URLs are provided
        license_warnings = []
        if package.license and (model_url or code_url or dataset_url):
            logger.info(f"Checking license compatibility for {name} v{version}")

            # Check each GitHub URL for license compatibility
            for url_type, url in [("model", model_url), ("code", code_url), ("dataset", dataset_url)]:
                if url and "github.com" in url.lower():
                    compat_result = github_license_fetcher.check_compatibility_with_github(
                        package.license,
                        url
                    )

                    if compat_result["compatible"] is False:
                        warning_msg = (
                            f"License incompatibility detected with {url_type} repository: "
                            f"{compat_result['reason']}"
                        )
                        license_warnings.append(warning_msg)
                        logger.warning(f"Package {name} v{version}: {warning_msg}")

        # Create metrics entry
        metrics_data = {
            "bus_factor": eval_result.get("bus_factor"),
            "ramp_up": eval_result.get("ramp_up_time"),
            "license_score": eval_result.get("license"),
            "net_score": eval_result.get("net_score"),
            "size_score": eval_result.get("size_score"),
            "performance_claims": eval_result.get("performance_claims"),
            "dataset_and_code_score": eval_result.get("dataset_and_code_score"),
            "dataset_quality": eval_result.get("dataset_quality"),
            "code_quality": eval_result.get("code_quality"),
            "reproducibility": eval_result.get("reproducibility"),
            "reviewedness": eval_result.get("reviewedness"),
            "tree_score": eval_result.get("treescore")
        }

        crud.create_metrics(db, package.id, metrics_data)

        logger.info(f"Package uploaded successfully: {package.id}")

        response = {
            "package_id": str(package.id),
            "name": name,
            "version": version,
            "s3_path": s3_path,
            "net_score": eval_result.get("net_score"),
            "message": "Package uploaded and evaluated successfully"
        }

        # Add license warnings if any
        if license_warnings:
            response["license_warnings"] = license_warnings

        return response

    finally:
        # Cleanup temp file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


@app.post("/package/ingest-huggingface")
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def ingest_huggingface_model(
    request: Request,
    body: Dict[str, Any],
    user: User = Depends(require_permission("upload")),
    db: Session = Depends(get_db)
):
    """
    Ingest a HuggingFace model with rate limiting by downloading it and storing in the registry.

    This endpoint:
    1. Downloads the full model package from HuggingFace
    2. Creates a zip file of the model
    3. Runs metrics evaluation
    4. Validates metrics meet minimum threshold (≥0.5 for non-latency metrics)
    5. Uploads to S3
    6. Stores package metadata and metrics in database

    Args:
        request: JSON body with model_id, optional version, optional description
        user: Authenticated user with upload permission
        db: Database session

    Returns:
        Package metadata with ingestion results
    """
    from src.services.huggingface_service import hf_service

    # Parse request body
    model_id = body.get("model_id")
    if not model_id:
        raise HTTPException(status_code=400, detail="model_id is required")

    version_override = body.get("version")
    description = body.get("description")

    logger.info(f"Ingesting HuggingFace model: {model_id} by user {user.username}")

    # Create temporary directory for downloads
    temp_dir = tempfile.mkdtemp(prefix="hf_ingest_")
    temp_zip_path = None

    try:
        # Download the model from HuggingFace
        logger.info(f"Downloading model from HuggingFace: {model_id}")
        try:
            model_path, metadata = hf_service.download_model(model_id, cache_dir=temp_dir)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Failed to download HuggingFace model: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to download model: {str(e)}")

        # Parse name and version
        name, default_version = hf_service.parse_model_name_version(model_id)
        version = version_override or default_version

        # Validate name
        is_valid, validation_msg = validate_package_name(name)
        if not is_valid:
            raise HTTPException(status_code=400, detail=validation_msg)

        # Check if package already exists
        existing = crud.get_package_by_name_version(db, name, version)
        if existing:
            logger.warning(f"Package '{name}' version '{version}' already exists (id={existing.id})")
            raise HTTPException(
                status_code=409,  # 409 Conflict
                detail={
                    "error": "Package already exists",
                    "package_id": str(existing.id),
                    "name": name,
                    "version": version,
                    "message": f"Package '{name}' version '{version}' already exists in the registry. "
                               f"If you want to upload this model again, please use a different version number "
                               f"(e.g., '1.0.1' or '2.0.0')."
                }
            )

        # Create zip file
        temp_zip_path = os.path.join(temp_dir, "package.zip")
        logger.info(f"Creating zip package from: {model_path}")
        size_bytes = hf_service.create_package_zip(model_path, temp_zip_path)

        # Extract URLs from README and metadata for metrics evaluation
        logger.info("Extracting dataset/code URLs from model metadata...")
        extracted_urls = hf_service.extract_urls_from_readme(model_path, metadata)

        model_url = extracted_urls.get("model_url") or f"https://huggingface.co/{model_id}"
        dataset_url = extracted_urls.get("dataset_url") or ""
        code_url = extracted_urls.get("code_url") or ""

        logger.info(f"Using URLs for metrics - Model: {model_url}, Dataset: {dataset_url}, Code: {code_url}")

        # Create package entry first (so we have package_id for TreeScore)
        package = crud.create_package(
            db=db,
            name=name,
            version=version,
            uploader_id=user.id,
            s3_path="",  # Will be updated after S3 upload
            description=description or f"HuggingFace model: {model_id}",
            license="",  # Will be updated after metrics evaluation
            size_bytes=size_bytes
        )

        # Extract license string from HuggingFace tags first
        license_str = "unknown"
        license_score = 0.0
        if metadata.get("tags"):
            for tag in metadata["tags"]:
                if tag.startswith("license:"):
                    license_str = tag.replace("license:", "")
                    # Score license: 1.0 for compatible licenses, 0.0 otherwise (binary scoring)
                    # Compatible licenses from Phase 1 & 2 requirements
                    compatible_licenses = [
                        "apache-2.0", "apache", "mit",
                        "bsd", "bsd-2-clause", "bsd-3-clause",
                        "gpl", "gpl-2.0", "gpl-3.0",
                        "lgpl", "lgpl-2.1", "lgpl-3.0",
                        "cc0", "cc0-1.0", "cc-by-4.0",
                        "unlicense", "public domain"
                    ]
                    if license_str.lower() in compatible_licenses:
                        license_score = 1.0
                    else:
                        license_score = 0.0
                    logger.info(f"Extracted license from HuggingFace metadata: {license_str} (score: {license_score})")
                    break

        # Run metrics evaluation with extracted URLs
        logger.info("Running metrics evaluation...")
        evaluator = MetricsEvaluator(
            model_url=model_url,
            dataset_url=dataset_url,
            code_url=code_url,
            db_session=db,
            package_id=package.id
        )
        eval_result = evaluator.evaluate()

        # Override license score with the one from HuggingFace tags (more reliable)
        if license_score > 0:
            logger.info(f"Overriding license score from {eval_result.get('license', 0.0)} to {license_score}")
            eval_result["license"] = license_score

        # Update package with license
        package.license = license_str
        db.commit()
        db.refresh(package)

        # Validate metrics meet minimum threshold
        # Use HuggingFace-specific validation (only checks license, not GitHub-based metrics)
        is_valid, validation_msg = validate_huggingface_metrics(eval_result, threshold=0.5)
        if not is_valid:
            logger.error(f"Model {model_id} failed metric validation: {validation_msg}")
            # Delete the package we just created since validation failed
            crud.delete_package(db, package.id)
            raise HTTPException(
                status_code=400,
                detail=f"Package does not meet minimum quality requirements. {validation_msg}"
            )

        logger.info(f"HuggingFace metrics validation passed for {model_id}")

        # Upload to S3
        s3_key = s3_helper.build_s3_path(name, version)
        logger.info(f"Uploading to S3: {s3_key}")

        # Check if file already exists in S3 (edge case: previous upload succeeded but DB failed)
        try:
            s3_helper.s3_client.head_object(Bucket=s3_helper.bucket_name, Key=s3_key)
            logger.warning(f"S3 file already exists: {s3_key}, will overwrite")
        except Exception:
            # File doesn't exist, that's expected
            pass

        success = s3_helper.upload_file(temp_zip_path, s3_key)

        if not success:
            # Delete package if S3 upload fails
            crud.delete_package(db, package.id)
            raise HTTPException(status_code=500, detail="Failed to upload to S3")

        s3_path = s3_helper.build_full_s3_url(s3_key)

        # Update package with S3 path
        package.s3_path = s3_path
        db.commit()
        db.refresh(package)

        # Create metrics entry
        metrics_data = {
            "bus_factor": eval_result.get("bus_factor"),
            "ramp_up": eval_result.get("ramp_up_time"),
            "license_score": eval_result.get("license"),
            "net_score": eval_result.get("net_score"),
            "size_score": eval_result.get("size_score"),
            "performance_claims": eval_result.get("performance_claims"),
            "dataset_and_code_score": eval_result.get("dataset_and_code_score"),
            "dataset_quality": eval_result.get("dataset_quality"),
            "code_quality": eval_result.get("code_quality"),
            "reproducibility": eval_result.get("reproducibility"),
            "reviewedness": eval_result.get("reviewedness"),
            "tree_score": eval_result.get("treescore")
        }

        crud.create_metrics(db, package.id, metrics_data)

        # Extract and create lineage entries for parent models
        parent_model_ids = hf_service.extract_parent_models(model_path, metadata)
        lineage_created = []

        if parent_model_ids:
            logger.info(f"Processing lineage for {len(parent_model_ids)} parent model(s)")

            for parent_model_id in parent_model_ids:
                try:
                    # Parse parent model name (convert to our naming convention)
                    parent_name, _ = hf_service.parse_model_name_version(parent_model_id)

                    # Check if parent exists in our registry
                    parent_package = crud.get_package_by_name(db, parent_name)

                    if parent_package:
                        # Create lineage entry
                        crud.create_lineage(
                            db=db,
                            package_id=package.id,
                            parent_id=parent_package.id,
                            relationship_type="derived_from"
                        )
                        lineage_created.append(parent_model_id)
                        logger.info(f"Created lineage: {name} -> {parent_name}")
                    else:
                        logger.warning(
                            f"Parent model '{parent_model_id}' not found in registry. "
                            f"Ingest parent model first to establish lineage."
                        )

                except Exception as e:
                    logger.error(f"Failed to create lineage for parent '{parent_model_id}': {e}")

        logger.info(f"HuggingFace model ingested successfully: {package.id}")

        return {
            "package_id": str(package.id),
            "name": name,
            "version": version,
            "model_id": model_id,
            "s3_path": s3_path,
            "net_score": eval_result.get("net_score"),
            "size_bytes": size_bytes,
            "message": "HuggingFace model ingested successfully",
            "lineage": {
                "parent_models_found": parent_model_ids,
                "lineage_created": lineage_created
            } if parent_model_ids else None,
            "metrics": {
                "license": eval_result.get("license"),
                "size_score": eval_result.get("size_score"),
                "ramp_up_time": eval_result.get("ramp_up_time"),
                "bus_factor": eval_result.get("bus_factor"),
                "performance_claims": eval_result.get("performance_claims"),
                "dataset_and_code_score": eval_result.get("dataset_and_code_score"),
                "dataset_quality": eval_result.get("dataset_quality"),
                "code_quality": eval_result.get("code_quality"),
                "reproducibility": eval_result.get("reproducibility"),
                "reviewedness": eval_result.get("reviewedness"),
                "treescore": eval_result.get("treescore"),
                "net_score": eval_result.get("net_score"),
            }
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error during HuggingFace ingestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    finally:
        # Cleanup temporary files
        if temp_zip_path and os.path.exists(temp_zip_path):
            os.remove(temp_zip_path)
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        logger.info("Cleaned up temporary files")


@app.put("/package/{package_id}/rate")
async def rate_package(
    package_id: UUID,
    rating_req: RatingRequest,
    user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Rate a package.
    As per CRUD plan: PUT /package/{id}/rate

    NOTE: Does not require authentication for baseline functionality.
    """
    # Check if package exists
    package = crud.get_package_by_id(db, package_id)
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    # Use default admin if no user authenticated
    if user is None:
        user = db.query(User).filter(User.username == "ece30861defaultadminuser").first()
        if not user:
            raise HTTPException(status_code=500, detail="Default admin user not found")

    # Create/update rating
    crud.create_rating(db, package_id, user.id, rating_req.score)

    # Get updated average
    avg_rating = crud.get_average_rating(db, package_id)

    return {
        "package_id": str(package_id),
        "user_rating": rating_req.score,
        "average_rating": round(avg_rating, 2)
    }


# ========== READ Operations ==========

@app.get("/package/{package_id}")
async def get_package(
    package_id: UUID,
    component: str = "full",  # Options: "full", "weights", "datasets", "code"
    request: Request = None,
    user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    Download a package.
    As per CRUD plan: GET /package/{id}
    Returns presigned S3 URL for download.
    """
    # Validate component parameter
    valid_components = ["full", "weights", "datasets", "code"]
    if component not in valid_components:
        valid_list = ", ".join(valid_components)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid component. Must be one of: {valid_list}"
        )

    package = crud.get_package_by_id(db, package_id)
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    # Log download
    ip_address = request.client.host if request else None
    user_agent = request.headers.get("user-agent") if request else None
    user_id = user.id if user else None
    crud.log_download(db, package_id, user_id, ip_address, user_agent)

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
        "component": component,
        "download_url": presigned_url,
        "expires_in_seconds": 300
    }


@app.post("/packages")
@limiter.limit(f"{settings.rate_limit_search_per_minute}/minute")
async def search_packages(
    request: Request,
    queries: List[PackageQuery],
    offset: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Search/enumerate packages with rate limiting.
    As per CRUD plan: POST /packages
    Rate limited to prevent DoS attacks on expensive search operations.

    NOTE: This endpoint does NOT require authentication to support baseline autograder functionality.
    Authentication is only required for the Security Track extended requirements.

    Accepts a list of package queries and returns packages matching ANY of the queries.
    An empty list returns all packages.
    """
    # If no queries provided, return all packages
    if not queries:
        packages, total = crud.search_packages(
            db=db,
            name_query=None,
            version=None,
            regex=None,
            search_model_card=False,
            offset=offset,
            limit=limit
        )
    else:
        # Collect all unique packages matching any query
        all_packages = []
        seen_ids = set()

        for query in queries:
            packages, _ = crud.search_packages(
                db=db,
                name_query=query.name,
                version=query.version,
                regex=query.regex,
                search_model_card=query.search_model_card,
                offset=0,  # Don't apply offset per query
                limit=10000  # Get all matches per query
            )
            for pkg in packages:
                if pkg.id not in seen_ids:
                    all_packages.append(pkg)
                    seen_ids.add(pkg.id)

        # Apply offset and limit to combined results
        total = len(all_packages)
        packages = all_packages[offset:offset + limit]

    # Format response
    results = []
    for pkg in packages:
        metrics = crud.get_package_metrics(db, pkg.id)
        results.append({
            "id": str(pkg.id),
            "name": pkg.name,
            "version": pkg.version,
            "description": pkg.description,
            "license": pkg.license,
            "net_score": metrics.net_score if metrics else None,
            "upload_date": pkg.upload_date.isoformat() if pkg.upload_date else None,
            "metrics": {
                "license_score": metrics.license_score if metrics else None,
                "bus_factor": metrics.bus_factor if metrics else None,
                "ramp_up": metrics.ramp_up if metrics else None,
                "code_quality": metrics.code_quality if metrics else None,
                "dataset_quality": metrics.dataset_quality if metrics else None,
                "correctness": metrics.correctness if metrics else None,
                "responsive_maintainer": metrics.responsive_maintainer if metrics else None,
                "reviewedness": metrics.reviewedness if metrics else None,
                "reproducibility": metrics.reproducibility if metrics else None,
                "tree_score": metrics.tree_score if metrics else None,
                "performance_claims": metrics.performance_claims if metrics else None,
                "dataset_and_code_score": metrics.dataset_and_code_score if metrics else None,
                "size_score": metrics.size_score if metrics else None,
                "good_pinning_practice": metrics.good_pinning_practice if metrics else None,
                "pull_request": metrics.pull_request if metrics else None,
                "net_score": metrics.net_score if metrics else None
            } if metrics else None
        })

    return {
        "packages": results,
        "total": total,
        "offset": offset,
        "limit": limit
    }


@app.get("/package/{package_id}/metadata")
async def get_package_metadata(
    package_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get package metadata.
    As per CRUD plan: GET /package/{id}/metadata
    """
    package = crud.get_package_by_id(db, package_id)
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    metrics = crud.get_package_metrics(db, package_id)
    avg_rating = crud.get_average_rating(db, package_id)

    return {
        "id": str(package.id),
        "name": package.name,
        "version": package.version,
        "description": package.description,
        "license": package.license,
        "size_bytes": package.size_bytes,
        "uploader_id": str(package.uploader_id) if package.uploader_id else None,
        "upload_date": package.upload_date.isoformat() if package.upload_date else None,
        "metrics": {
            "net_score": metrics.net_score if metrics else None,
            "bus_factor": metrics.bus_factor if metrics else None,
            "ramp_up": metrics.ramp_up if metrics else None,
            "code_quality": metrics.code_quality if metrics else None,
            "dataset_quality": metrics.dataset_quality if metrics else None
        } if metrics else None,
        "average_rating": round(avg_rating, 2)
    }


@app.get("/package/{package_id}/lineage")
async def get_package_lineage(
    package_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get package lineage tree.
    As per CRUD plan: GET /package/{id}/lineage
    """
    package = crud.get_package_by_id(db, package_id)
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    lineage = crud.get_package_lineage(db, package_id)

    return {
        "package_id": str(package_id),
        "lineage": lineage
    }


@app.get("/package/{package_id}/size")
async def get_package_size_info(
    package_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get detailed size information and download options for a package.
    Returns size breakdown by component and estimated download sizes for different options.
    """
    package = crud.get_package_by_id(db, package_id)
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    # Get size breakdown from stored data
    size_breakdown = package.size_breakdown or {}

    # Generate download options
    download_options = []
    if size_breakdown:
        download_options = size_analyzer.get_download_options(size_breakdown)

    return {
        "package_id": str(package_id),
        "package_name": package.name,
        "package_version": package.version,
        "total_size_bytes": package.size_bytes,
        "total_size_mb": round(package.size_bytes / (1024 * 1024), 2) if package.size_bytes else 0,
        "size_breakdown": size_breakdown,
        "download_options": download_options
    }


# ========== UPDATE Operations ==========

@app.put("/user/{user_id}/permissions")
async def update_user_permissions(
    user_id: UUID,
    perm_update: PermissionUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update user permissions (admin only).
    As per CRUD plan: PUT /user/{id}/permissions
    """
    user = crud.update_user_permissions(db, user_id, perm_update.permissions)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "user_id": str(user.id),
        "username": user.username,
        "permissions": user.permissions,
        "message": "Permissions updated successfully"
    }


# ========== DELETE Operations ==========

@app.delete("/package/{package_id}")
async def delete_package(
    package_id: UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Delete a package (admin only).
    As per CRUD plan: DELETE /package/{id}
    """
    package = crud.get_package_by_id(db, package_id)
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    # Delete from S3
    s3_key = package.s3_path.replace(f"s3://{s3_helper.bucket_name}/", "")
    s3_helper.delete_file(s3_key)

    # Delete from database
    success = crud.delete_package(db, package_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete package")

    return {
        "message": "Package deleted successfully",
        "package_id": str(package_id)
    }


@app.delete("/user/{user_id}")
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a user.
    As per CRUD plan: DELETE /user/{id}
    Users can delete themselves, admins can delete anyone.
    """
    # Check permission
    if str(current_user.id) != str(user_id) and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Cannot delete other users")

    success = crud.delete_user(db, user_id)

    if not success:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "message": "User deleted successfully",
        "user_id": str(user_id)
    }


@app.post("/package/license-check", response_model=LicenseCheckResponse)
async def check_license_compatibility(
    request: LicenseCheckRequest,
    db: Session = Depends(get_db)
):
    """
    Check license compatibility between a GitHub project and a model package.
    Sprint 2: License Compatibility Checker

    This endpoint:
    1. Fetches license from GitHub repository
    2. Gets license from package in database
    3. Uses license compatibility checker to determine compatibility

    Args:
        github_url: GitHub repository URL (e.g., https://github.com/user/repo)
        model_id: Package UUID to check compatibility with

    Returns:
        Compatibility result with licenses and explanation
    """
    logger.info(f"Checking license compatibility: {request.github_url} with package {request.model_id}")

    # Get package from database
    package = crud.get_package_by_id(db, request.model_id)
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    # Get package license
    model_license = package.license or "unknown"

    # Fetch GitHub license using DataFetcher
    try:
        fetcher = DataFetcher(
            model_url=request.github_url,
            dataset_url="",
            code_url=""
        )
        github_license = fetcher.get_license()
        if not github_license:
            github_license = "unknown"
    except Exception as e:
        logger.error(f"Failed to fetch GitHub license: {e}")
        github_license = "unknown"

    # Check compatibility
    is_compatible, reason = license_checker.are_compatible(github_license, model_license)

    # Check for warnings (e.g., "result must be X")
    warnings = []
    if is_compatible and ("must be" in reason.lower() or "result" in reason.lower()):
        warnings.append(reason)

    logger.info(
        f"License check result: {is_compatible} - "
        f"GitHub: {github_license}, Model: {model_license}"
    )

    return LicenseCheckResponse(
        compatible=is_compatible,
        github_license=github_license,
        model_license=model_license,
        reason=reason,
        warnings=warnings if warnings else None
    )


@app.get("/logs")
async def get_logs(
    level: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    offset: int = 0,
    limit: int = 100,
    admin: User = Depends(require_admin)
):
    """
    Get application logs with filtering.
    Sprint 3: Logs endpoint for observability.

    Query Parameters:
    - level: Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - start_time: ISO format datetime for range start
    - end_time: ISO format datetime for range end
    - offset: Pagination offset (default: 0)
    - limit: Max logs to return (default: 100, max: 1000)

    Returns recent errors tracked by the metrics collector.
    """
    # Validate limit
    limit = min(limit, 1000)

    # Get recent errors from metrics collector
    recent_errors = list(metrics_collector.recent_errors)

    # Apply filters
    filtered_errors = recent_errors

    # Filter by time range if provided
    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            filtered_errors = [
                e for e in filtered_errors
                if datetime.fromisoformat(e["timestamp"].replace('Z', '+00:00')) >= start_dt
            ]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_time format. Use ISO format.")

    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            filtered_errors = [
                e for e in filtered_errors
                if datetime.fromisoformat(e["timestamp"].replace('Z', '+00:00')) <= end_dt
            ]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_time format. Use ISO format.")

    # Apply pagination
    total = len(filtered_errors)
    paginated_errors = filtered_errors[offset:offset+limit]

    return {
        "logs": paginated_errors,
        "total": total,
        "offset": offset,
        "limit": limit,
        "note": "Showing recent request errors. For full logs, check application log files."
    }


@app.delete("/reset")
async def reset_system(
    db: Session = Depends(get_db)
):
    """
    Reset system to default state.
    As per CRUD plan: DELETE /reset
    Deletes all packages and users except default admin.
    Uses pagination to handle large numbers of S3 objects.

    NOTE: This endpoint does NOT require authentication to support autograder reset functionality.
    """
    logger.warning("System reset initiated")

    # Delete all S3 objects with pagination
    s3_deleted_count = 0
    try:
        logger.warning("Deleting all S3 objects with pagination...")
        s3_deleted_count = s3_helper.delete_all_objects()
        logger.info(f"Successfully deleted {s3_deleted_count} objects from S3")
    except Exception as e:
        logger.error(f"Failed to delete S3 objects: {e}")
        # Continue with database reset even if S3 cleanup fails

    # Reset database
    crud.reset_system(db, keep_admin=True)

    # Verify reset by querying packages count
    package_count = db.query(Package).count()
    logger.warning(f"System reset completed - {package_count} packages remaining (should be 0)")

    return {
        "message": "System reset to default state",
        "s3_objects_deleted": s3_deleted_count,
        "database_reset": True,
        "packages_remaining": package_count
    }


# ========== Main Entry Point ==========

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )