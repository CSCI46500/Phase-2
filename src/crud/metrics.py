"""
Metrics CRUD operations.
Handles all database operations related to the Metrics model.
"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from uuid import UUID
import logging

from src.core.models import Metrics

logger = logging.getLogger(__name__)


# ========== CREATE Operations ==========

def create_metrics(
    db: Session,
    package_id: UUID,
    metrics_data: Dict[str, Any]
) -> Metrics:
    """Create metrics entry for a package."""
    metrics = Metrics(
        package_id=package_id,
        **metrics_data
    )

    db.add(metrics)
    db.commit()
    db.refresh(metrics)

    logger.info(f"Created metrics for package_id={package_id}")
    return metrics


# ========== READ Operations ==========

def get_package_metrics(db: Session, package_id: UUID) -> Optional[Metrics]:
    """Get metrics for a package."""
    return db.query(Metrics).filter(Metrics.package_id == package_id).first()