"""
Package CRUD operations.
Handles all database operations related to the Package model.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from uuid import UUID
import logging

from src.core.models import Package

logger = logging.getLogger(__name__)


# ========== CREATE Operations ==========

def create_package(
    db: Session,
    name: str,
    version: str,
    uploader_id: UUID,
    s3_path: str,
    description: Optional[str] = None,
    license: Optional[str] = None,
    model_card: Optional[str] = None,
    size_bytes: Optional[int] = None,
    size_breakdown: Optional[Dict[str, Any]] = None,
    is_sensitive: bool = False
) -> Package:
    """Create a new package entry."""
    package = Package(
        name=name,
        version=version,
        uploader_id=uploader_id,
        s3_path=s3_path,
        description=description,
        license=license,
        model_card=model_card,
        size_bytes=size_bytes,
        size_breakdown=size_breakdown,
        is_sensitive=is_sensitive
    )

    db.add(package)
    db.commit()
    db.refresh(package)

    logger.info(f"Created package: {name} v{version} (id={package.id})")
    return package


def create_lineage(
    db: Session,
    package_id: UUID,
    parent_id: UUID,
    relationship_type: str = "derived_from"
):
    """
    Create a lineage relationship between a package and its parent.

    Args:
        db: Database session
        package_id: ID of the child package
        parent_id: ID of the parent package
        relationship_type: Type of relationship (e.g., "derived_from", "forked_from")
    """
    from src.core.models import Lineage

    # Check if lineage already exists
    existing = db.query(Lineage).filter(
        Lineage.package_id == package_id,
        Lineage.parent_id == parent_id
    ).first()

    if existing:
        logger.debug(f"Lineage already exists: {package_id} -> {parent_id}")
        return existing

    lineage = Lineage(
        package_id=package_id,
        parent_id=parent_id,
        relationship_type=relationship_type
    )

    db.add(lineage)
    db.commit()
    db.refresh(lineage)

    logger.info(f"Created lineage: {package_id} -> {parent_id} ({relationship_type})")
    return lineage


# ========== READ Operations ==========

def get_package_by_id(db: Session, package_id: UUID) -> Optional[Package]:
    """Get package by ID."""
    return db.query(Package).filter(Package.id == package_id).first()


def get_package_by_name_version(db: Session, name: str, version: str) -> Optional[Package]:
    """Get package by name and version."""
    return db.query(Package).filter(
        Package.name == name,
        Package.version == version
    ).first()


def get_package_by_name(db: Session, name: str) -> Optional[Package]:
    """
    Get the latest version of a package by name.
    Returns the most recently uploaded package with the given name.
    """
    return db.query(Package).filter(
        Package.name == name
    ).order_by(Package.upload_date.desc()).first()


def search_packages(
    db: Session,
    name_query: Optional[str] = None,
    version: Optional[str] = None,
    regex: Optional[str] = None,
    search_model_card: bool = False,
    offset: int = 0,
    limit: int = 50
) -> tuple[List[Package], int]:
    """
    Search packages with pagination.
    Supports regex search on package names and optionally on model cards.
    Returns (packages, total_count).
    """
    from sqlalchemy import or_

    query = db.query(Package)

    # Apply filters
    if name_query:
        query = query.filter(Package.name.ilike(f"%{name_query}%"))

    if version:
        query = query.filter(Package.version == version)

    if regex:
        # If search_model_card is True, search both name and model_card fields
        if search_model_card:
            query = query.filter(
                or_(
                    Package.name.op('~')(regex),
                    Package.model_card.op('~')(regex)
                )
            )
        else:
            # Default: only search package name
            query = query.filter(Package.name.op('~')(regex))

    # Get total count
    total = query.count()

    # Apply pagination (max 100 per page for DoS protection)
    packages = query.offset(offset).limit(min(limit, 100)).all()

    logger.debug(f"Search found {total} packages, returning {len(packages)} (model_card_search={search_model_card})")
    return packages, total


def get_package_lineage(db: Session, package_id: UUID) -> List[Dict[str, Any]]:
    """
    Get lineage tree for a package (recursive parents).
    Returns list of packages in lineage with depth.
    """
    from sqlalchemy import text

    # Use raw SQL for recursive CTE as per plan
    query = text("""
    WITH RECURSIVE lineage_tree AS (
        -- Base case: current package
        SELECT id, name, version, NULL::uuid as parent_id, 0 as depth
        FROM packages
        WHERE id = :package_id

        UNION ALL

        -- Recursive case: parents
        SELECT p.id, p.name, p.version, l.parent_id, lt.depth + 1
        FROM packages p
        JOIN lineage l ON p.id = l.parent_id
        JOIN lineage_tree lt ON l.package_id = lt.id
    )
    SELECT * FROM lineage_tree ORDER BY depth;
    """)

    result = db.execute(query, {"package_id": str(package_id)})
    lineage = []

    for row in result:
        lineage.append({
            "id": str(row.id),
            "name": row.name,
            "version": row.version,
            "depth": row.depth
        })

    logger.debug(f"Retrieved lineage for package_id={package_id}, depth={len(lineage)}")
    return lineage


# ========== UPDATE Operations ==========

def update_package(
    db: Session,
    package_id: UUID,
    updates: Dict[str, Any]
) -> Optional[Package]:
    """Update package fields."""
    package = get_package_by_id(db, package_id)
    if not package:
        return None

    for key, value in updates.items():
        if hasattr(package, key):
            setattr(package, key, value)

    db.commit()
    db.refresh(package)

    logger.info(f"Updated package_id={package_id}")
    return package


# ========== DELETE Operations ==========

def delete_package(db: Session, package_id: UUID) -> bool:
    """Delete a package and all related data (cascades)."""
    package = get_package_by_id(db, package_id)
    if not package:
        return False

    db.delete(package)
    db.commit()

    logger.info(f"Deleted package_id={package_id}")
    return True