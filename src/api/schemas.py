"""
Pydantic schemas for request/response models.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import UUID


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


class HuggingFaceIngestRequest(BaseModel):
    """Request model for ingesting HuggingFace models."""
    model_id: str = Field(..., description="HuggingFace model identifier (e.g., 'gpt2', 'facebook/bart-large')")
    version: Optional[str] = Field(None, description="Optional version override (defaults to 1.0.0)")
    description: Optional[str] = Field(None, description="Optional package description")


class HuggingFaceIngestResponse(BaseModel):
    """Response model for HuggingFace ingestion."""
    package_id: str
    name: str
    version: str
    model_id: str
    s3_path: str
    net_score: float
    size_bytes: int
    message: str
    metrics: Dict[str, Any] = Field(default_factory=dict)