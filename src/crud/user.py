"""
User CRUD operations.
Handles all database operations related to the User model.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from uuid import UUID
import logging

from src.core.models import User

logger = logging.getLogger(__name__)


# ========== UPDATE Operations ==========

def update_user_permissions(
    db: Session,
    user_id: UUID,
    permissions: List[str]
) -> Optional[User]:
    """Update user permissions (admin only operation)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None

    user.permissions = permissions
    db.commit()
    db.refresh(user)

    logger.info(f"Updated permissions for user_id={user_id}")
    return user


# ========== DELETE Operations ==========

def delete_user(db: Session, user_id: UUID) -> bool:
    """Delete a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False

    db.delete(user)
    db.commit()

    logger.info(f"Deleted user_id={user_id}")
    return True