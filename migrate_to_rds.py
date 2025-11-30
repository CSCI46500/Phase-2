#!/usr/bin/env python3
"""
Migration script to create tables in AWS RDS PostgreSQL database.
This script connects to RDS and creates all tables from SQLAlchemy models.
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import after loading env to avoid Settings validation issues
from src.core.models import Base, User
from src.core.auth import hash_password

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_rds_url():
    """Get RDS database URL from environment variable."""
    rds_url = os.getenv("RDS_DATABASE_URL")
    if not rds_url:
        raise ValueError(
            "RDS_DATABASE_URL environment variable not set!\n"
            "Please set it in your .env file:\n"
            "RDS_DATABASE_URL=postgresql://username:password@endpoint:5432/dbname"
        )
    return rds_url


def test_connection(engine):
    """Test database connection."""
    logger.info("Testing database connection...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            logger.info(f"Connected successfully! PostgreSQL version: {version}")
            return True
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        return False


def create_tables(engine):
    """Create all tables from SQLAlchemy models."""
    logger.info("Creating tables...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Tables created successfully!")
        return True
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        return False


def verify_tables(engine):
    """Verify that tables were created."""
    logger.info("Verifying tables...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
                """
            ))
            tables = [row[0] for row in result.fetchall()]

            logger.info(f"Found {len(tables)} tables:")
            for table in tables:
                logger.info(f"  - {table}")

            expected_tables = [
                'users', 'tokens', 'packages', 'metrics', 'lineage',
                'ratings', 'download_history', 'package_confusion_audit', 'system_metrics'
            ]

            missing_tables = set(expected_tables) - set(tables)
            if missing_tables:
                logger.warning(f"Missing tables: {missing_tables}")
                return False

            logger.info("All expected tables are present!")
            return True

    except Exception as e:
        logger.error(f"Failed to verify tables: {e}")
        return False


def create_admin_user(engine):
    """Create default admin user."""
    logger.info("Creating default admin user...")

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Check if admin already exists
        admin_username = os.getenv("ADMIN_USERNAME", "ece30861defaultadminuser")
        existing_admin = db.query(User).filter(User.username == admin_username).first()

        if existing_admin:
            logger.info(f"Admin user '{admin_username}' already exists. Skipping creation.")
            return True

        # Create admin user
        admin_password = os.getenv("ADMIN_PASSWORD", "correcthorsebatterystaple123(!__+@**(A;DROP TABLE packages")
        password_hash, salt = hash_password(admin_password)

        admin = User(
            username=admin_username,
            password_hash=password_hash,
            salt=salt,
            is_admin=True,
            permissions=["upload", "download", "search", "admin"]
        )

        db.add(admin)
        db.commit()

        logger.info(f"Admin user created successfully!")
        logger.info(f"  Username: {admin_username}")
        logger.info(f"  Password: {admin_password}")
        logger.info("  Permissions: upload, download, search, admin")

        return True

    except Exception as e:
        logger.error(f"Failed to create admin user: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def main():
    """Main migration function."""
    print("=" * 60)
    print("AWS RDS PostgreSQL Migration Script")
    print("=" * 60)

    try:
        # Get RDS URL
        rds_url = get_rds_url()
        logger.info(f"Using RDS endpoint: {rds_url.split('@')[1].split('/')[0]}")

        # Create engine
        engine = create_engine(rds_url, echo=False)

        # Test connection
        if not test_connection(engine):
            print("\n[ERROR] Failed to connect to RDS. Please check your credentials and security group settings.")
            return 1

        print("\n[SUCCESS] Connection successful!")

        # Create tables
        print("\nCreating tables...")
        if not create_tables(engine):
            print("\n[ERROR] Failed to create tables.")
            return 1

        print("[SUCCESS] Tables created successfully!")

        # Verify tables
        print("\nVerifying tables...")
        if not verify_tables(engine):
            print("\n[WARNING] Some tables may be missing.")
        else:
            print("[SUCCESS] All tables verified!")

        # Create admin user
        print("\nCreating admin user...")
        if not create_admin_user(engine):
            print("\n[WARNING] Failed to create admin user. You may need to create it manually.")
        else:
            print("[SUCCESS] Admin user created!")

        print("\n" + "=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Update your .env file to use RDS_DATABASE_URL for production")
        print("2. Update your application to use the RDS database")
        print("3. Test the connection from your application")
        print("\nIMPORTANT: Keep your RDS credentials secure!")
        print("=" * 60)

        return 0

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        print(f"\n[ERROR] Migration failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
