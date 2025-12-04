"""
System-wide operations.
Handles system-level database operations that affect multiple entities.
"""
from sqlalchemy.orm import Session
import logging

from src.core.models import User, Package

logger = logging.getLogger(__name__)


def reset_system(db: Session, keep_admin: bool = True) -> None:
    """
    Reset system by truncating all tables.
    Optionally keeps default admin user.
    """
    logger.warning("Resetting system...")

    if keep_admin:
        # Delete all users except the default admin (required by autograder spec)
        admin_username = "ece30861defaultadminuser"
        db.query(User).filter(User.username != admin_username).delete()
    else:
        db.query(User).delete()

    # Delete all packages (cascades to related tables)
    db.query(Package).delete()

    db.commit()

    # Ensure changes are flushed and visible immediately
    db.flush()
    db.expire_all()

    logger.info("System reset completed")