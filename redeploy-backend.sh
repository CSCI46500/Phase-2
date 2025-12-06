#!/bin/bash
# Quick script to rebuild and redeploy only the backend

set -e

echo "Building backend image..."
docker build -f Dockerfile.production -t model-registry-backend .

echo "Tagging image..."
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
docker tag model-registry-backend:latest ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/model-backend:latest

echo "Logging into ECR..."
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com

echo "Pushing image to ECR..."
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/model-backend:latest

echo "Updating ECS service..."
aws ecs update-service --cluster model-cluster --service model-backend-service --force-new-deployment --region us-east-1

echo "✓ Deployment initiated! Wait 60 seconds for the new task to start."
echo "Test with: curl http://model-registry-alb-1277815581.us-east-1.elb.amazonaws.com:8000/health"
