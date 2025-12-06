#!/bin/bash
# Docker entrypoint script to initialize database before starting the application
set -e

echo "=== Model Registry Startup ==="
echo "Initializing database tables..."

# Run Python script to create tables
python3 -c "
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info('Creating database tables...')
from src.core.database import init_db
init_db()
logger.info('Database tables created successfully')
"

echo "Starting application..."
exec python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
