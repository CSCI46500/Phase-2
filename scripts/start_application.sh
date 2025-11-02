#!/bin/bash
# Start the application

echo "Starting application..."

cd /home/ec2-user/app

# Start application in background
nohup python3.11 main.py > /home/ec2-user/app/app.log 2>&1 &

echo "Application started"

exit 0