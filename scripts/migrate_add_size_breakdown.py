#!/usr/bin/env python3
"""
Migration script to add size_breakdown column to packages table.
This script can be run directly to update the database schema.
"""
import sys
import os

# Add parent directory to path so we can import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import text
from src.core.database import engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate():
    """Add size_breakdown column to packages table if it doesn't exist."""

    logger.info("Starting migration: add size_breakdown column")

    # Check if column already exists
    check_column_sql = """
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name='packages' AND column_name='size_breakdown';
    """

    with engine.connect() as conn:
        result = conn.execute(text(check_column_sql))
        exists = result.fetchone() is not None

        if exists:
            logger.info("Column 'size_breakdown' already exists. Skipping migration.")
            return

        # Add the column
        logger.info("Adding 'size_breakdown' column to packages table...")
        add_column_sql = """
        ALTER TABLE packages
        ADD COLUMN size_breakdown JSONB;
        """

        conn.execute(text(add_column_sql))
        conn.commit()

        logger.info("✅ Migration completed successfully!")
        logger.info("Column 'size_breakdown' added to packages table")


if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        sys.exit(1)
