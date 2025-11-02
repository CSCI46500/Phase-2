#!/bin/bash
# Stop the running application

echo "Stopping application..."

# Check if application is running and stop it
if pgrep -f "python main.py" > /dev/null; then
    pkill -f "python main.py"
    echo "Application stopped"
else
    echo "Application was not running"
fi

exit 0