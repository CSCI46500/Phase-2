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

from src.core.database import get_db, init_db
from src.core.models import User, Package
from src.core.auth import (
    authenticate_user,
    generate_token,
    create_user,
    get_current_user,
    require_permission,
    require_admin,
    init_default_admin,
    check_permission
)
import src.crud as crud
from src.services.s3_service import s3_helper
from src.services.metrics_service import MetricsEvaluator
from src.core.config import settings
from src.utils.logger import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="Model Registry API with CRUD operations for ML models"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative dev port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint.
    Returns system health status.
    """
    health = {
        "status": "healthy",
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
async def upload_package(
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
    Upload and evaluate a package.
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

        # Run metrics evaluation
        evaluator = MetricsEvaluator(
            model_url=model_url,
            dataset_url=dataset_url,
            code_url=code_url
        )
        eval_result = evaluator.evaluate()

        # Create package entry
        package = crud.create_package(
            db=db,
            name=name,
            version=version,
            uploader_id=user.id,
            s3_path=s3_path,
            description=description,
            license=eval_result.get("license"),
            size_bytes=size_bytes
        )

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

        return {
            "package_id": str(package.id),
            "name": name,
            "version": version,
            "s3_path": s3_path,
            "net_score": eval_result.get("net_score"),
            "message": "Package uploaded and evaluated successfully"
        }

    finally:
        # Cleanup temp file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


@app.post("/package/ingest-huggingface")
async def ingest_huggingface_model(
    request: Dict[str, Any],
    user: User = Depends(require_permission("upload")),
    db: Session = Depends(get_db)
):
    """
    Ingest a HuggingFace model by downloading it and storing in the registry.

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
    from src.utils.validation import validate_metric_threshold, validate_package_name

    # Parse request
    model_id = request.get("model_id")
    if not model_id:
        raise HTTPException(status_code=400, detail="model_id is required")

    version_override = request.get("version")
    description = request.get("description")

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
            raise HTTPException(
                status_code=400,
                detail=f"Package '{name}' version '{version}' already exists. Use a different version."
            )

        # Create zip file
        temp_zip_path = os.path.join(temp_dir, "package.zip")
        logger.info(f"Creating zip package from: {model_path}")
        size_bytes = hf_service.create_package_zip(model_path, temp_zip_path)

        # Generate URLs for metrics evaluation
        model_url = hf_service.get_model_url(model_id)
        dataset_url = ""  # Optional: could be extracted from model metadata
        code_url = ""  # Optional: could be extracted from model metadata

        # Run metrics evaluation
        logger.info("Running metrics evaluation")
        evaluator = MetricsEvaluator(
            model_url=model_url,
            dataset_url=dataset_url,
            code_url=code_url
        )
        eval_result = evaluator.evaluate()

        # Validate metrics meet minimum threshold
        is_valid, validation_msg = validate_metric_threshold(eval_result, threshold=0.5)
        if not is_valid:
            logger.warning(f"Model {model_id} failed metric validation: {validation_msg}")
            raise HTTPException(
                status_code=400,
                detail=f"Model does not meet quality requirements. {validation_msg}"
            )

        logger.info(f"Metrics validation passed for {model_id}")

        # Upload to S3
        s3_key = s3_helper.build_s3_path(name, version)
        logger.info(f"Uploading to S3: {s3_key}")
        success = s3_helper.upload_file(temp_zip_path, s3_key)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to upload to S3")

        s3_path = s3_helper.build_full_s3_url(s3_key)

        # Prepare description
        if not description:
            description = f"HuggingFace model: {model_id}"
            if metadata.get("pipeline_tag"):
                description += f" ({metadata['pipeline_tag']})"

        # Create package entry
        package = crud.create_package(
            db=db,
            name=name,
            version=version,
            uploader_id=user.id,
            s3_path=s3_path,
            description=description,
            license=eval_result.get("license"),
            size_bytes=size_bytes
        )

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
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Rate a package.
    As per CRUD plan: PUT /package/{id}/rate
    """
    # Check if package exists
    package = crud.get_package_by_id(db, package_id)
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

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
    user: User = Depends(require_permission("download")),
    db: Session = Depends(get_db),
    request: Request = None
):
    """
    Download a package.
    As per CRUD plan: GET /package/{id}
    Returns presigned S3 URL for download.
    """
    package = crud.get_package_by_id(db, package_id)
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")

    # Log download
    ip_address = request.client.host if request else None
    user_agent = request.headers.get("user-agent") if request else None
    crud.log_download(db, package_id, user.id, ip_address, user_agent)

    # Extract S3 key from s3:// URL
    s3_key = package.s3_path.replace(f"s3://{s3_helper.bucket_name}/", "")

    # Generate presigned URL (expires in 5 minutes)
    presigned_url = s3_helper.generate_presigned_url(s3_key, expiration=300)

    if not presigned_url:
        raise HTTPException(status_code=500, detail="Failed to generate download URL")

    return {
        "package_id": str(package_id),
        "name": package.name,
        "version": package.version,
        "download_url": presigned_url,
        "expires_in_seconds": 300
    }


@app.post("/packages")
async def search_packages(
    query: PackageQuery,
    offset: int = 0,
    limit: int = 50,
    user: User = Depends(require_permission("search")),
    db: Session = Depends(get_db)
):
    """
    Search/enumerate packages.
    As per CRUD plan: POST /packages
    """
    packages, total = crud.search_packages(
        db=db,
        name_query=query.name,
        version=query.version,
        regex=query.regex,
        offset=offset,
        limit=limit
    )

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
            "upload_date": pkg.upload_date.isoformat() if pkg.upload_date else None
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
    user: User = Depends(get_current_user),
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
    user: User = Depends(get_current_user),
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


@app.delete("/reset")
async def reset_system(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Reset system (admin only).
    As per CRUD plan: DELETE /reset
    Deletes all packages and users except default admin.
    """
    # Delete all S3 objects
    try:
        # Note: This is a simplified version. In production, you'd want to paginate through objects
        logger.warning("Deleting all S3 objects...")
        # Implementation depends on AWS SDK pagination
    except Exception as e:
        logger.error(f"Failed to delete S3 objects: {e}")

    # Reset database
    crud.reset_system(db, keep_admin=True)

    return {
        "message": "System reset to default state"
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