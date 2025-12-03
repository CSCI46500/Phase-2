"""
CRUD operations for the Model Registry.
Organized by entity/domain for better maintainability.

This module maintains backward compatibility with the original crud.py
by re-exporting all functions at the package level.
"""

# Package operations
from .package import (
    create_package,
    get_package_by_id,
    get_package_by_name_version,
    search_packages,
    get_package_lineage,
    update_package,
    delete_package
)

# User operations
from .user import (
    update_user_permissions,
    delete_user
)

# Metrics operations
from .metrics import (
    create_metrics,
    get_package_metrics
)

# Rating operations
from .rating import (
    create_rating,
    get_average_rating
)

# Download operations
from .download import (
    log_download,
    get_download_history
)

# Package confusion detection
from .confusion import (
    detect_package_confusion
)

# System operations
from .system import (
    reset_system
)

__all__ = [
    # Package
    "create_package",
    "get_package_by_id",
    "get_package_by_name_version",
    "search_packages",
    "get_package_lineage",
    "update_package",
    "delete_package",
    # User
    "update_user_permissions",
    "delete_user",
    # Metrics
    "create_metrics",
    "get_package_metrics",
    # Rating
    "create_rating",
    "get_average_rating",
    # Download
    "log_download",
    "get_download_history",
    # Confusion
    "detect_package_confusion",
    # System
    "reset_system",
]