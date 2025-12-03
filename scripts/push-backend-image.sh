#!/bin/bash
set -e

# Quick script to push the already-built backend image

# Load config
source .env.aws

# Get AWS account ID
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "Tagging and pushing backend image..."
echo "Account: $AWS_ACCOUNT_ID"
echo "Region: $AWS_REGION"

# Login to ECR
aws ecr get-login-password --region ${AWS_REGION} | \
    docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Get backend repo URI
BACKEND_REPO_URI=$(aws ecr describe-repositories \
    --repository-names ${ECR_BACKEND_REPO} \
    --region ${AWS_REGION} \
    --query 'repositories[0].repositoryUri' \
    --output text)

echo "Backend URI: $BACKEND_REPO_URI"

# Tag the local image
docker tag 187641964754.dkr.ecr.us-east-1.amazonaws.com/model-registry-backend:latest ${BACKEND_REPO_URI}:latest
docker tag 187641964754.dkr.ecr.us-east-1.amazonaws.com/model-registry-backend:latest ${BACKEND_REPO_URI}:$(date +%Y%m%d-%H%M%S)

# Push to ECR
echo "Pushing to ECR..."
docker push ${BACKEND_REPO_URI}:latest

# Force redeploy the service
echo "Forcing service redeployment..."
aws ecs update-service \
    --cluster ${ECS_CLUSTER_NAME} \
    --service ${ECS_BACKEND_SERVICE} \
    --force-new-deployment \
    --region ${AWS_REGION}

echo "Done! Waiting for deployment to stabilize (this may take 2-3 minutes)..."
echo "Monitor logs with: aws logs tail /ecs/model-registry-backend --follow --region ${AWS_REGION}"
