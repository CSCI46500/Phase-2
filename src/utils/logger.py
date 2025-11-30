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

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Get log file path from environment
    log_file = os.environ.get("LOG_FILE")

    if log_file:
        # Add file handler
        file_handler = logging.FileHandler(log_file, mode="a")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logging.getLogger().addHandler(file_handler)
    else:
        # Default to stderr for console output
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(log_level)
        logging.getLogger().addHandler(console_handler)

    logger = logging.getLogger(__name__)
    if log_level_env > 0:
        logger.info(f"Logging configured at level {log_level_env}")
