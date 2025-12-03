#!/bin/bash

# AWS Environment Setup Helper Script
# This script helps you set up your .env.aws file with the correct values

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  AWS Environment Setup Helper${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}ERROR: AWS CLI is not installed!${NC}"
    echo "Please install it from: https://aws.amazon.com/cli/"
    exit 1
fi

# Check if AWS is configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}ERROR: AWS CLI is not configured!${NC}"
    echo "Please run: aws configure"
    exit 1
fi

echo -e "${GREEN}✓ AWS CLI is installed and configured${NC}"
echo ""

# Get AWS Account ID
echo "Getting your AWS Account ID..."
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✓ AWS Account ID: $AWS_ACCOUNT_ID${NC}"
echo ""

# Get AWS Region
AWS_REGION=$(aws configure get region)
if [ -z "$AWS_REGION" ]; then
    AWS_REGION="us-east-1"
    echo -e "${YELLOW}! No default region set, using us-east-1${NC}"
else
    echo -e "${GREEN}✓ AWS Region: $AWS_REGION${NC}"
fi
echo ""

# Generate secure passwords
echo "Generating secure passwords..."
DB_PASSWORD=$(openssl rand -base64 32)
SECRET_KEY=$(openssl rand -hex 32)
echo -e "${GREEN}✓ Secure passwords generated${NC}"
echo ""

# Create .env.aws file
if [ -f ".env.aws" ]; then
    echo -e "${YELLOW}! .env.aws already exists${NC}"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Keeping existing .env.aws file"
        exit 0
    fi
fi

echo "Creating .env.aws file..."

cat > .env.aws <<EOF
# AWS Configuration
# Generated on $(date)

# AWS Settings
AWS_REGION=$AWS_REGION
PROJECT_NAME=model-registry
ENVIRONMENT=production

# ECR Repository Names
ECR_BACKEND_REPO=model-registry-backend
ECR_FRONTEND_REPO=model-registry-frontend

# RDS Database Configuration
DB_NAME=modelregistry
DB_USERNAME=admin
DB_PASSWORD=$DB_PASSWORD
DB_INSTANCE_CLASS=db.t3.micro
DB_ALLOCATED_STORAGE=20

# S3 Bucket Configuration
S3_BUCKET_NAME=model-registry-models-$AWS_ACCOUNT_ID

# ECS Configuration
ECS_CLUSTER_NAME=model-registry-cluster
ECS_BACKEND_SERVICE=model-registry-backend-service
ECS_FRONTEND_SERVICE=model-registry-frontend-service

# Admin User (Required by specification)
ADMIN_USERNAME=ece30861defaultadminuser
ADMIN_PASSWORD='correcthorsebatterystaple123(!__+@**(A;DROP TABLE packages'

# Security
SECRET_KEY=$SECRET_KEY

# Optional: API Keys for external services
# ANTHROPIC_API_KEY=
# GITHUB_TOKEN=

# CloudWatch Configuration
LOG_RETENTION_DAYS=7

# Auto-scaling Configuration
ECS_MIN_TASKS=1
ECS_MAX_TASKS=4
ECS_TARGET_CPU_PERCENT=70
EOF

echo -e "${GREEN}✓ .env.aws file created${NC}"
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Your .env.aws file has been created with:"
echo "  • AWS Account ID: $AWS_ACCOUNT_ID"
echo "  • AWS Region: $AWS_REGION"
echo "  • S3 Bucket: model-registry-models-$AWS_ACCOUNT_ID"
echo "  • Secure database password (32 bytes)"
echo "  • Secure secret key (32 bytes)"
echo ""
echo -e "${YELLOW}IMPORTANT:${NC}"
echo "  • Never commit .env.aws to Git!"
echo "  • Keep your passwords secure"
echo "  • Set up billing alerts in AWS Console"
echo ""
echo "Next steps:"
echo "  1. Review the .env.aws file"
echo "  2. Run: ./scripts/deploy-to-aws.sh"
echo "  3. Wait ~30 minutes for deployment"
echo ""
echo "For help: See docs/AWS_QUICK_START.md"
echo ""
