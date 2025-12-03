#!/bin/bash
# Run the Model Registry API server

echo "Starting Model Registry API..."
python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload