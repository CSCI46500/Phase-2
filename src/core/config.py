"""
Configuration management for the Model Registry API.
"""
import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Environment
    environment: str = "production"  # "local", "development", "staging", "production"

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/model_registry"

    # AWS S3
    s3_bucket_name: str = "model-registry-packages"
    s3_region: str = "us-east-1"
    s3_endpoint_url: Optional[str] = None  # For MinIO or localstack (e.g., http://minio:9000)
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

    # Security - Use ACME default admin credentials (from OpenAPI spec)
    admin_username: str = "ece30861defaultadminuser"
    admin_password: str = "correcthorsebatterystaple123(!__+@**(A'\"`;DROP TABLE artifacts;"

    # Logging
    log_level: str = "INFO"

    # SQL Echo (for debugging SQL queries)
    sql_echo: bool = False

    # Rate Limiting (DoS protection)
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 100  # Max requests per minute per IP
    rate_limit_search_per_minute: int = 30  # Lower limit for expensive search operations

    @property
    def is_local(self) -> bool:
        """Check if running in local environment."""
        return self.environment.lower() in ("local", "development")

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()