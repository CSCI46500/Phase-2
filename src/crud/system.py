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
    Uses TRUNCATE for fast, guaranteed deletion.
    """
    from sqlalchemy import text

    logger.warning("Resetting system...")

    # Use TRUNCATE for guaranteed immediate deletion
    # TRUNCATE is faster and ensures immediate visibility across all connections
    try:
        # Disable foreign key checks temporarily for clean truncation
        db.execute(text("SET session_replication_role = 'replica';"))

        # Truncate tables in correct order (respecting foreign keys)
        db.execute(text("TRUNCATE TABLE download_history CASCADE;"))
        db.execute(text("TRUNCATE TABLE ratings CASCADE;"))
        db.execute(text("TRUNCATE TABLE lineage CASCADE;"))
        db.execute(text("TRUNCATE TABLE metrics CASCADE;"))
        db.execute(text("TRUNCATE TABLE package_confusion_audit CASCADE;"))
        db.execute(text("TRUNCATE TABLE system_metrics CASCADE;"))
        db.execute(text("TRUNCATE TABLE packages CASCADE;"))

        # Truncate users table but keep admin
        if keep_admin:
            admin_username = "ece30861defaultadminuser"
            # Delete non-admin users
            db.execute(text(f"DELETE FROM users WHERE username != '{admin_username}';"))
        else:
            db.execute(text("TRUNCATE TABLE users CASCADE;"))

        # Re-enable foreign key checks
        db.execute(text("SET session_replication_role = 'origin';"))

        # Commit immediately
        db.commit()

    except Exception as e:
        logger.error(f"Reset failed: {e}")
        db.rollback()
        # Re-enable foreign key checks even on failure
        db.execute(text("SET session_replication_role = 'origin';"))
        db.commit()
        raise

    # Verify the reset worked
    count = db.execute(text("SELECT COUNT(*) FROM packages")).scalar()
    if count != 0:
        logger.error(f"Reset verification failed: {count} packages still exist!")
        raise Exception(f"Reset failed: {count} packages still exist after deletion")

    logger.info(f"System reset completed and verified (0 packages remain)")