"""
System monitoring and metrics collection service.
Tracks API performance, errors, and system health for observability.
"""

import time
import logging
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict, deque
from sqlalchemy.orm import Session
import statistics

from src.core.models import SystemMetrics
from src.core.database import get_db_context

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Collects and aggregates system metrics for observability.
    Thread-safe in-memory storage with periodic database persistence.
    """

    def __init__(self):
        """Initialize metrics collector with in-memory storage."""
        # Request tracking
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0

        # Response time tracking (sliding window)
        self.response_times = deque(maxlen=1000)  # Last 1000 requests

        # Endpoint-specific metrics
        self.endpoint_counts = defaultdict(int)
        self.endpoint_errors = defaultdict(int)
        self.endpoint_response_times = defaultdict(lambda: deque(maxlen=100))

        # Error details
        self.recent_errors = deque(maxlen=100)

        # Last collection time
        self.last_collection = datetime.now()

    def record_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: float,
        error: Optional[str] = None
    ):
        """
        Record a single API request with its metrics.

        Args:
            endpoint: API endpoint path
            method: HTTP method (GET, POST, etc.)
            status_code: HTTP status code
            response_time_ms: Response time in milliseconds
            error: Optional error message
        """
        self.request_count += 1

        # Track success/failure
        if 200 <= status_code < 400:
            self.success_count += 1
        else:
            self.error_count += 1
            if error:
                self.recent_errors.append({
                    "timestamp": datetime.now().isoformat(),
                    "endpoint": endpoint,
                    "method": method,
                    "status_code": status_code,
                    "error": error
                })

        # Track response times
        self.response_times.append(response_time_ms)

        # Track endpoint-specific metrics
        endpoint_key = f"{method} {endpoint}"
        self.endpoint_counts[endpoint_key] += 1
        self.endpoint_response_times[endpoint_key].append(response_time_ms)

        if status_code >= 400:
            self.endpoint_errors[endpoint_key] += 1

    def get_current_metrics(self) -> Dict:
        """
        Get current in-memory metrics snapshot.

        Returns:
            Dictionary with current metrics
        """
        # Calculate response time percentiles
        if self.response_times:
            sorted_times = sorted(self.response_times)
            avg_response = statistics.mean(sorted_times)
            p95_response = self._percentile(sorted_times, 95)
            p99_response = self._percentile(sorted_times, 99)
        else:
            avg_response = 0.0
            p95_response = 0.0
            p99_response = 0.0

        # Calculate error rate
        error_rate = (
            (self.error_count / self.request_count * 100)
            if self.request_count > 0
            else 0.0
        )

        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # Build endpoint metrics
        endpoint_metrics = {}
        for endpoint, count in self.endpoint_counts.items():
            times = list(self.endpoint_response_times[endpoint])
            endpoint_metrics[endpoint] = {
                "count": count,
                "errors": self.endpoint_errors.get(endpoint, 0),
                "avg_response_ms": statistics.mean(times) if times else 0.0
            }

        return {
            "timestamp": datetime.now(),
            "total_requests": self.request_count,
            "successful_requests": self.success_count,
            "failed_requests": self.error_count,
            "avg_response_time_ms": round(avg_response, 2),
            "p95_response_time_ms": round(p95_response, 2),
            "p99_response_time_ms": round(p99_response, 2),
            "error_count": self.error_count,
            "error_rate": round(error_rate, 2),
            "endpoint_metrics": endpoint_metrics,
            "cpu_percent": round(cpu_percent, 2),
            "memory_percent": round(memory.percent, 2),
            "disk_percent": round(disk.percent, 2),
            "db_connections": None,  # Would need DB pool monitoring
            "db_query_time_ms": None  # Would need query instrumentation
        }

    def persist_to_database(self, db: Session):
        """
        Persist current metrics to database.

        Args:
            db: Database session
        """
        try:
            metrics_data = self.get_current_metrics()

            # Create SystemMetrics record
            metric_record = SystemMetrics(
                timestamp=metrics_data["timestamp"],
                total_requests=metrics_data["total_requests"],
                successful_requests=metrics_data["successful_requests"],
                failed_requests=metrics_data["failed_requests"],
                avg_response_time_ms=metrics_data["avg_response_time_ms"],
                p95_response_time_ms=metrics_data["p95_response_time_ms"],
                p99_response_time_ms=metrics_data["p99_response_time_ms"],
                error_count=metrics_data["error_count"],
                error_rate=metrics_data["error_rate"],
                endpoint_metrics=metrics_data["endpoint_metrics"],
                cpu_percent=metrics_data["cpu_percent"],
                memory_percent=metrics_data["memory_percent"],
                disk_percent=metrics_data["disk_percent"],
                db_connections=metrics_data["db_connections"],
                db_query_time_ms=metrics_data["db_query_time_ms"]
            )

            db.add(metric_record)
            db.commit()

            logger.info(
                f"Persisted metrics: {metrics_data['total_requests']} requests, "
                f"{metrics_data['error_rate']}% error rate"
            )

        except Exception as e:
            logger.error(f"Failed to persist metrics to database: {e}")
            db.rollback()

    def reset_counters(self):
        """Reset cumulative counters (called after persistence)."""
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        self.endpoint_counts.clear()
        self.endpoint_errors.clear()
        self.endpoint_response_times.clear()
        # Keep response_times and recent_errors for rolling window

    @staticmethod
    def _percentile(sorted_list: List[float], percentile: int) -> float:
        """Calculate percentile from sorted list."""
        if not sorted_list:
            return 0.0

        index = (len(sorted_list) - 1) * (percentile / 100.0)
        lower = int(index)
        upper = lower + 1

        if upper >= len(sorted_list):
            return sorted_list[-1]

        weight = index - lower
        return sorted_list[lower] * (1 - weight) + sorted_list[upper] * weight


# Global metrics collector instance
metrics_collector = MetricsCollector()


def collect_and_persist_metrics():
    """
    Background task to persist metrics to database.
    Should be called periodically (e.g., every 1-5 minutes).
    """
    try:
        with get_db_context() as db:
            metrics_collector.persist_to_database(db)
            # Don't reset counters - keep cumulative for the session
            logger.debug("Metrics collection cycle completed")
    except Exception as e:
        logger.error(f"Error in metrics collection cycle: {e}")


def get_recent_metrics(db: Session, minutes: int = 60) -> List[SystemMetrics]:
    """
    Get recent system metrics from database.

    Args:
        db: Database session
        minutes: Number of minutes to look back

    Returns:
        List of SystemMetrics records
    """
    cutoff = datetime.now() - timedelta(minutes=minutes)

    metrics = db.query(SystemMetrics).filter(
        SystemMetrics.timestamp >= cutoff
    ).order_by(SystemMetrics.timestamp.desc()).all()

    return metrics