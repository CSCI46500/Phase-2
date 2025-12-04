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

    # Flush changes to database before commit
    db.flush()

    # Commit the transaction
    db.commit()

    # Expire all cached objects to force fresh reads
    db.expire_all()

    # Verify the reset worked by counting packages using raw SQL
    # This ensures we're reading fresh data, not cached
    from sqlalchemy import text
    count = db.execute(text("SELECT COUNT(*) FROM packages")).scalar()
    if count != 0:
        logger.error(f"Reset verification failed: {count} packages still exist!")
        raise Exception(f"Reset failed: {count} packages still exist after deletion")

    logger.info(f"System reset completed and verified (0 packages remain)")