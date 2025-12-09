"""
Logging configuration module.
Configures logging based on environment variables.
"""

import logging
import os
import sys


def setup_logging():
    """
    Configure logging based on environment variables.

    Environment variables:
        LOG_LEVEL: 0 (silent), 1 (info), 2 (debug)
        LOG_FILE: Optional file path for log output
    """
    log_level_env = int(os.environ.get("LOG_LEVEL", "0"))

    # Map log level to Python logging levels
    level_mapping = {
        0: logging.CRITICAL + 10,  # Effectively silent
        1: logging.INFO,
        2: logging.DEBUG,
    }

    log_level = level_mapping.get(log_level_env, logging.CRITICAL + 10)

    # Get log file path from environment
    log_file = os.environ.get("LOG_FILE")

    # Configure root logger with appropriate handler
    if log_file:
        # Configure with file output
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            filename=log_file,
            filemode="a",
        )
    else:
        # Configure with stderr output (basicConfig defaults to stderr)
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            stream=sys.stderr,
        )

    logger = logging.getLogger(__name__)
    if log_level_env > 0:
        logger.info(f"Logging configured at level {log_level_env}")
