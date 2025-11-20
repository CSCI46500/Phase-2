"""
Package confusion detection operations.
Handles detection of similar package names to prevent confusion attacks.
"""
from typing import List, Dict, Any
from sqlalchemy.orm import Session
import logging

from src.core.models import Package

logger = logging.getLogger(__name__)


def detect_package_confusion(db: Session, package_name: str) -> List[Dict[str, Any]]:
    """
    Detect similar package names for confusion detection.
    Returns list of similar packages.
    """
    # Get all package names
    all_packages = db.query(Package.name).distinct().all()

    similar = []
    for (existing_name,) in all_packages:
        # Calculate Levenshtein-like similarity (simple version)
        if _is_similar(package_name, existing_name):
            similar.append({
                "name": existing_name,
                "similarity": "high"
            })

    return similar


def _is_similar(name1: str, name2: str) -> bool:
    """Simple similarity check (can be improved with Levenshtein distance)."""
    if name1 == name2:
        return False

    name1_lower = name1.lower()
    name2_lower = name2.lower()

    # Check if one is substring of other
    if name1_lower in name2_lower or name2_lower in name1_lower:
        return True

    # Check character similarity (simple method)
    if len(name1) > 3 and len(name2) > 3:
        shared = sum(1 for c in name1_lower if c in name2_lower)
        similarity_ratio = shared / max(len(name1), len(name2))
        return similarity_ratio > 0.8

    return False