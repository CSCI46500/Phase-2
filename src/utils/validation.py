"""
Validation utilities for package ingestion.
"""
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)


def validate_metric_threshold(metrics_result: Dict[str, Any], threshold: float = 0.5) -> Tuple[bool, str]:
    """
    Validate that all non-latency metrics meet the minimum threshold.

    As per Phase 2 requirements: Models must score at least 0.5 on each non-latency metric
    to be ingestible.

    Args:
        metrics_result: Dictionary containing metric scores from MetricsEvaluator
        threshold: Minimum required score (default: 0.5)

    Returns:
        Tuple of (is_valid, message)
        - is_valid: True if all metrics meet threshold, False otherwise
        - message: Explanation of validation result
    """
    # Non-latency metrics to check
    metrics_to_check = {
        "license": "License",
        "size_score": "Size Score",
        "ramp_up_time": "Ramp-Up Time",
        "bus_factor": "Bus Factor",
        "performance_claims": "Performance Claims",
        "dataset_and_code_score": "Dataset/Code Score",
        "dataset_quality": "Dataset Quality",
        "code_quality": "Code Quality",
    }

    failed_metrics = []

    for metric_key, metric_name in metrics_to_check.items():
        score = metrics_result.get(metric_key)

        # Handle size_score which might be a dict
        if isinstance(score, dict):
            # For size_score, take the minimum value
            score = min(score.values()) if score else 0.0

        if score is None:
            failed_metrics.append(f"{metric_name} (missing)")
            continue

        if score < threshold:
            failed_metrics.append(f"{metric_name} ({score:.2f} < {threshold})")

    if failed_metrics:
        message = f"Package does not meet minimum quality threshold. Failed metrics: {', '.join(failed_metrics)}"
        logger.warning(f"Metric validation failed: {message}")
        return False, message

    logger.info("All metrics passed validation threshold")
    return True, "All metrics meet minimum quality threshold"


def validate_package_name(name: str) -> Tuple[bool, str]:
    """
    Validate package name format.

    Args:
        name: Package name to validate

    Returns:
        Tuple of (is_valid, message)
    """
    import re

    # Package name should be alphanumeric with hyphens, underscores, and slashes allowed
    pattern = r'^[a-zA-Z0-9_\-\/\.]+$'

    if not name:
        return False, "Package name cannot be empty"

    if len(name) < 2:
        return False, "Package name must be at least 2 characters"

    if len(name) > 255:
        return False, "Package name must be less than 255 characters"

    if not re.match(pattern, name):
        return False, "Package name contains invalid characters. Only alphanumeric, hyphens, underscores, dots, and slashes are allowed"

    return True, "Package name is valid"


def validate_version(version: str) -> Tuple[bool, str]:
    """
    Validate package version format.

    Args:
        version: Version string to validate

    Returns:
        Tuple of (is_valid, message)
    """
    import re

    # Simple semantic versioning pattern
    pattern = r'^\d+\.\d+\.\d+([a-zA-Z0-9\-\.]*)?$'

    if not version:
        return False, "Version cannot be empty"

    if not re.match(pattern, version):
        return False, "Version must follow semantic versioning format (e.g., 1.0.0, 1.2.3-beta)"

    return True, "Version is valid"