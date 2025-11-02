#!/bin/bash
# Run before installing new application version

echo "Preparing for installation..."

# Install Python 3.11 if not present
if ! command -v python3.11 &> /dev/null; then
    echo "Installing Python 3.11..."
    sudo yum update -y
    sudo yum install python3.11 python3.11-pip -y
fi

# Create application directory if it doesn't exist
mkdir -p /home/ec2-user/app

exit 0