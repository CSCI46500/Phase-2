#!/bin/bash
set -e

# Load config
source .env.aws

# Get AWS account ID
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "Building and deploying frontend..."
echo "Account: $AWS_ACCOUNT_ID"
echo "Region: $AWS_REGION"

# Login to ECR
aws ecr get-login-password --region ${AWS_REGION} | \
    docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Get frontend repo URI
FRONTEND_REPO_URI=$(aws ecr describe-repositories \
    --repository-names ${ECR_FRONTEND_REPO} \
    --region ${AWS_REGION} \
    --query 'repositories[0].repositoryUri' \
    --output text)

echo "Frontend URI: $FRONTEND_REPO_URI"

# Build frontend image
echo "Building frontend image..."
cd front-end/model-registry-frontend
docker build -f Dockerfile.production -t ${ECR_FRONTEND_REPO}:latest .

# Tag the image
docker tag ${ECR_FRONTEND_REPO}:latest ${FRONTEND_REPO_URI}:latest
docker tag ${ECR_FRONTEND_REPO}:latest ${FRONTEND_REPO_URI}:$(date +%Y%m%d-%H%M%S)

# Push to ECR
echo "Pushing to ECR..."
docker push ${FRONTEND_REPO_URI}:latest

cd ../..

echo "Frontend image pushed successfully!"
echo ""
echo "Next steps:"
echo "1. Create ECS task definition for frontend"
echo "2. Create ECS service for frontend"
echo "3. Update ALB to route traffic to frontend"
