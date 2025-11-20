"""
Configuration management for the Model Registry API.
"""
import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/model_registry"

    # AWS S3
    s3_bucket_name: str = "model-registry-packages"
    s3_region: str = "us-east-1"
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_title: str = "Model Registry API"
    api_version: str = "1.0.0"

    # Authentication
    token_expiry_days: int = 30
    default_api_calls: int = 1000
    secret_key: str = "change-this-secret-key-in-production"

    # Security
    admin_username: str = "admin"
    admin_password: str = "admin123"  # Change in production!

    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()