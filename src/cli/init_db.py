#!/usr/bin/env python3
"""
Database initialization script.
Creates all tables and default admin user.
"""
import sys
from src.core.database import init_db, get_db_context
from src.core.auth import init_default_admin
from src.utils.logger import setup_logging
import logging

setup_logging()
logger = logging.getLogger(__name__)


def main():
    """Initialize database."""
    try:
        logger.info("Initializing database...")

        # Create all tables
        init_db()

        # Create default admin
        with get_db_context() as db:
            init_default_admin(db)

        logger.info("Database initialization completed successfully!")
        print("\nDatabase initialized successfully!")
        print("Default admin user created:")
        print("  Username: admin")
        print("  Password: admin123")
        print("\nIMPORTANT: Change the default admin password in production!")

        return 0

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        print(f"\nERROR: Database initialization failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())