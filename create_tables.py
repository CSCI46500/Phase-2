#!/usr/bin/env python3
"""
Script to manually create database tables.
"""
import os
import sys


os.environ['DATABASE_URL'] = f"postgresql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}"

# Now import and run init_db
from src.core.database import init_db, engine
from sqlalchemy import inspect

print("Connecting to database...")
print(f"Database URL: postgresql://{DB_USERNAME}:***@{DB_HOST}:5432/{DB_NAME}")

print("\nChecking existing tables...")
inspector = inspect(engine)
tables_before = inspector.get_table_names()
print(f"Tables before: {tables_before}")

print("\nRunning init_db()...")
init_db()

print("\nChecking tables after creation...")
inspector = inspect(engine)
tables_after = inspector.get_table_names()
print(f"Tables after: {tables_after}")

print("\nDone!")
