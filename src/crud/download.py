"""
Download history CRUD operations.
Handles all database operations related to the DownloadHistory model.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from uuid import UUID
import logging

from src.core.models import DownloadHistory

logger = logging.getLogger(__name__)


# ========== CREATE Operations ==========

def log_download(
    db: Session,
    package_id: UUID,
    user_id: Optional[UUID] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> DownloadHistory:
    """Log a package download."""
    download = DownloadHistory(
        package_id=package_id,
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent
    )

    db.add(download)
    db.commit()

    logger.info(f"Logged download for package_id={package_id}")
    return download


# ========== READ Operations ==========

def get_download_history(db: Session, package_id: UUID) -> List[DownloadHistory]:
    """Get download history for a package."""
    return db.query(DownloadHistory).filter(
        DownloadHistory.package_id == package_id
    ).order_by(DownloadHistory.timestamp.desc()).all()