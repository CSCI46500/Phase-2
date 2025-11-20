"""
Rating CRUD operations.
Handles all database operations related to the Rating model.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import UUID
import logging

from src.core.models import Rating

logger = logging.getLogger(__name__)


# ========== CREATE Operations ==========

def create_rating(
    db: Session,
    package_id: UUID,
    user_id: UUID,
    score: int
) -> Rating:
    """Create or update a rating for a package."""
    # Check if rating already exists
    existing = db.query(Rating).filter(
        Rating.package_id == package_id,
        Rating.user_id == user_id
    ).first()

    if existing:
        existing.score = score
        db.commit()
        db.refresh(existing)
        logger.info(f"Updated rating for package_id={package_id}, user_id={user_id}")
        return existing

    rating = Rating(
        package_id=package_id,
        user_id=user_id,
        score=score
    )

    db.add(rating)
    db.commit()
    db.refresh(rating)

    logger.info(f"Created rating for package_id={package_id}, user_id={user_id}, score={score}")
    return rating


# ========== READ Operations ==========

def get_average_rating(db: Session, package_id: UUID) -> float:
    """Calculate average rating for a package."""
    result = db.query(func.avg(Rating.score)).filter(
        Rating.package_id == package_id
    ).scalar()

    return float(result) if result else 0.0