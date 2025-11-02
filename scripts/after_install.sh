#!/bin/bash
# Run after installing new application version

echo "Installing dependencies..."

cd /home/ec2-user/app

# Make run script executable
chmod +x run

# Install dependencies
python3.11 -m pip install --user -r dependencies.txt

echo "Dependencies installed"

exit 0