-- PostgreSQL initialization script for Phase 2 Model Registry

-- This script runs automatically when the PostgreSQL container starts for the first time
-- It creates the necessary database extensions if needed

-- Enable UUID extension (if your models use UUIDs)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create any additional extensions you might need
-- CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text similarity searches

-- The actual table creation will be handled by SQLAlchemy/Alembic
-- This file just sets up the database environment
