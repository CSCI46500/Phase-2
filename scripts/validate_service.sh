#!/bin/bash
# Validate that the application is running correctly

echo "Validating service..."

# Wait a few seconds for application to start
sleep 5

# Check if application is running
if pgrep -f "python main.py" > /dev/null; then
    echo "✅ Application is running"
    exit 0
else
    echo "❌ Application is not running"
    exit 1
fi