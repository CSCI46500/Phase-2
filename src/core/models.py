"""
Database models for the Model Registry system.
Based on the schema defined in CRUD_IMPLEMENTATION_PLAN.md
"""
from sqlalchemy import Column, String, Float, Integer, Boolean, Text, DateTime, ForeignKey, BigInteger, TIMESTAMP, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


class User(Base):
    """User table for authentication and authorization."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    salt = Column(String(32), nullable=False)
    is_admin = Column(Boolean, default=False)
    permissions = Column(JSONB, default=["search"])  # ['upload', 'download', 'search', 'admin']
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    tokens = relationship("Token", back_populates="user", cascade="all, delete-orphan")
    packages = relationship("Package", back_populates="uploader")
    ratings = relationship("Rating", back_populates="user", cascade="all, delete-orphan")
    downloads = relationship("DownloadHistory", back_populates="user")


class Token(Base):
    """API token table for tracking usage."""
    __tablename__ = "tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(255), nullable=False, index=True)
    api_calls_remaining = Column(Integer, default=1000)
    created_at = Column(TIMESTAMP, server_default=func.now())
    expires_at = Column(TIMESTAMP, nullable=True)

    # Relationships
    user = relationship("User", back_populates="tokens")


class Package(Base):
    """Package table storing model/dataset metadata."""
    __tablename__ = "packages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    version = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=True)
    uploader_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    s3_path = Column(String(500), nullable=False)  # s3://bucket/name/version/package.zip
    is_sensitive = Column(Boolean, default=False)
    js_policy_path = Column(String(500), nullable=True)
    size_bytes = Column(BigInteger, nullable=True)
    license = Column(String(100), nullable=True)
    model_card = Column(Text, nullable=True)  # Extracted from README
    upload_date = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    uploader = relationship("User", back_populates="packages")
    metrics = relationship("Metrics", back_populates="package", uselist=False, cascade="all, delete-orphan")
    lineage_as_child = relationship("Lineage", foreign_keys="Lineage.package_id", back_populates="package", cascade="all, delete-orphan")
    lineage_as_parent = relationship("Lineage", foreign_keys="Lineage.parent_id", back_populates="parent", cascade="all, delete-orphan")
    ratings = relationship("Rating", back_populates="package", cascade="all, delete-orphan")
    downloads = relationship("DownloadHistory", back_populates="package", cascade="all, delete-orphan")
    audit_logs = relationship("PackageConfusionAudit", back_populates="package", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint('name ~ \'^[a-zA-Z0-9_-]+$\'', name='valid_package_name'),
    )


class Metrics(Base):
    """Metrics table storing evaluation scores."""
    __tablename__ = "metrics"

    package_id = Column(UUID(as_uuid=True), ForeignKey("packages.id", ondelete="CASCADE"), primary_key=True)
    bus_factor = Column(Float, nullable=True)
    correctness = Column(Float, nullable=True)
    ramp_up = Column(Float, nullable=True)
    responsive_maintainer = Column(Float, nullable=True)
    license_score = Column(Float, nullable=True)
    good_pinning_practice = Column(Float, nullable=True)
    pull_request = Column(Float, nullable=True)
    net_score = Column(Float, nullable=True)
    # New metrics from Phase 2
    reproducibility = Column(Float, nullable=True)
    reviewedness = Column(Float, nullable=True)
    tree_score = Column(Float, nullable=True)
    # Additional Phase 2 metrics
    size_score = Column(JSONB, nullable=True)  # Dict with platform-specific scores
    performance_claims = Column(Float, nullable=True)
    dataset_and_code_score = Column(Float, nullable=True)
    dataset_quality = Column(Float, nullable=True)
    code_quality = Column(Float, nullable=True)
    calculated_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    package = relationship("Package", back_populates="metrics")


class Lineage(Base):
    """Lineage table tracking package relationships."""
    __tablename__ = "lineage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    package_id = Column(UUID(as_uuid=True), ForeignKey("packages.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("packages.id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_type = Column(String(50), default="derived_from")  # 'derived_from', 'forked_from', etc.

    # Relationships
    package = relationship("Package", foreign_keys=[package_id], back_populates="lineage_as_child")
    parent = relationship("Package", foreign_keys=[parent_id], back_populates="lineage_as_parent")


class Rating(Base):
    """Rating table for user ratings of packages."""
    __tablename__ = "ratings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    package_id = Column(UUID(as_uuid=True), ForeignKey("packages.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    score = Column(Integer, CheckConstraint('score >= 1 AND score <= 5'), nullable=False)
    timestamp = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    package = relationship("Package", back_populates="ratings")
    user = relationship("User", back_populates="ratings")


class DownloadHistory(Base):
    """Download history tracking."""
    __tablename__ = "download_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    package_id = Column(UUID(as_uuid=True), ForeignKey("packages.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    timestamp = Column(TIMESTAMP, server_default=func.now(), index=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 support
    user_agent = Column(Text, nullable=True)

    # Relationships
    package = relationship("Package", back_populates="downloads")
    user = relationship("User", back_populates="downloads")


class PackageConfusionAudit(Base):
    """Audit log for package confusion detection."""
    __tablename__ = "package_confusion_audit"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    package_id = Column(UUID(as_uuid=True), ForeignKey("packages.id", ondelete="CASCADE"), nullable=False, index=True)
    suspicious_pattern = Column(String(255), nullable=True)
    detected_at = Column(TIMESTAMP, server_default=func.now())
    severity = Column(String(20), nullable=True, index=True)  # 'low', 'medium', 'high'
    details = Column(JSONB, nullable=True)

    # Relationships
    package = relationship("Package", back_populates="audit_logs")