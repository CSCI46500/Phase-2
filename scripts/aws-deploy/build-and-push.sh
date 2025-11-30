#!/bin/bash

# Build and Push Docker Images to ECR
# Usage: ./build-and-push.sh <backend|autograder|all> [tag]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
PROJECT_NAME="model-registry"
ENVIRONMENT="${ENVIRONMENT:-prod}"
TAG="${2:-latest}"

# ECR Repository names
BACKEND_REPO="${PROJECT_NAME}-${ENVIRONMENT}-backend"
AUTOGRADER_REPO="${PROJECT_NAME}-${ENVIRONMENT}-autograder"

# Full ECR URLs
BACKEND_ECR="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${BACKEND_REPO}"
AUTOGRADER_ECR="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${AUTOGRADER_REPO}"

echo -e "${GREEN}=== AWS ECR Docker Build and Push ===${NC}"
echo -e "${YELLOW}AWS Region: ${AWS_REGION}${NC}"
echo -e "${YELLOW}AWS Account: ${AWS_ACCOUNT_ID}${NC}"
echo -e "${YELLOW}Tag: ${TAG}${NC}"
echo ""

# Function to login to ECR
ecr_login() {
    echo -e "${GREEN}Logging in to Amazon ECR...${NC}"
    aws ecr get-login-password --region "${AWS_REGION}" | \
        docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
}

# Function to build and push backend
build_backend() {
    echo -e "${GREEN}Building backend Docker image...${NC}"
    docker build -f Dockerfile.backend -t "${BACKEND_REPO}:${TAG}" .

    echo -e "${GREEN}Tagging backend image...${NC}"
    docker tag "${BACKEND_REPO}:${TAG}" "${BACKEND_ECR}:${TAG}"
    docker tag "${BACKEND_REPO}:${TAG}" "${BACKEND_ECR}:latest"

    echo -e "${GREEN}Pushing backend image to ECR...${NC}"
    docker push "${BACKEND_ECR}:${TAG}"
    docker push "${BACKEND_ECR}:latest"

    echo -e "${GREEN}✓ Backend image pushed successfully!${NC}"
    echo -e "${YELLOW}Image: ${BACKEND_ECR}:${TAG}${NC}"
}

# Function to build and push autograder
build_autograder() {
    echo -e "${GREEN}Building autograder Docker image...${NC}"
    docker build -f Dockerfile.autograder -t "${AUTOGRADER_REPO}:${TAG}" .

    echo -e "${GREEN}Tagging autograder image...${NC}"
    docker tag "${AUTOGRADER_REPO}:${TAG}" "${AUTOGRADER_ECR}:${TAG}"
    docker tag "${AUTOGRADER_REPO}:${TAG}" "${AUTOGRADER_ECR}:latest"

    echo -e "${GREEN}Pushing autograder image to ECR...${NC}"
    docker push "${AUTOGRADER_ECR}:${TAG}"
    docker push "${AUTOGRADER_ECR}:latest"

    echo -e "${GREEN}✓ Autograder image pushed successfully!${NC}"
    echo -e "${YELLOW}Image: ${AUTOGRADER_ECR}:${TAG}${NC}"
}

# Main logic
TARGET="${1:-all}"

case $TARGET in
    backend)
        ecr_login
        build_backend
        ;;
    autograder)
        ecr_login
        build_autograder
        ;;
    all)
        ecr_login
        build_backend
        echo ""
        build_autograder
        ;;
    *)
        echo -e "${RED}Error: Invalid target '${TARGET}'${NC}"
        echo "Usage: $0 <backend|autograder|all> [tag]"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}=== Build and Push Complete ===${NC}"
