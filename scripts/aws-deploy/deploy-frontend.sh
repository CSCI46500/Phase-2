#!/bin/bash

# Deploy Frontend to S3 and Invalidate CloudFront Cache
# Usage: ./deploy-frontend.sh

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
PROJECT_NAME="model-registry"
ENVIRONMENT="${ENVIRONMENT:-prod}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# S3 Bucket name (must match Terraform output)
S3_BUCKET="${PROJECT_NAME}-${ENVIRONMENT}-frontend-${AWS_ACCOUNT_ID}"

# CloudFront Distribution ID (get from Terraform output)
DISTRIBUTION_ID=$(aws cloudfront list-distributions \
    --query "DistributionList.Items[?Comment=='${PROJECT_NAME}-${ENVIRONMENT} Frontend Distribution'].Id" \
    --output text)

FRONTEND_DIR="front-end/model-registry-frontend"

echo -e "${GREEN}=== Deploying Frontend to AWS ===${NC}"
echo -e "${YELLOW}S3 Bucket: ${S3_BUCKET}${NC}"
echo -e "${YELLOW}CloudFront Distribution: ${DISTRIBUTION_ID}${NC}"
echo ""

# Build the frontend
echo -e "${GREEN}Building frontend...${NC}"
cd "${FRONTEND_DIR}"
npm install
npm run build
cd ../..

# Sync to S3
echo -e "${GREEN}Uploading to S3...${NC}"
aws s3 sync "${FRONTEND_DIR}/dist" "s3://${S3_BUCKET}" \
    --delete \
    --cache-control "public, max-age=31536000, immutable" \
    --exclude "index.html"

# Upload index.html with no-cache
aws s3 cp "${FRONTEND_DIR}/dist/index.html" "s3://${S3_BUCKET}/index.html" \
    --cache-control "public, max-age=0, must-revalidate"

echo -e "${GREEN}✓ Files uploaded to S3${NC}"

# Invalidate CloudFront cache
if [ -n "$DISTRIBUTION_ID" ]; then
    echo -e "${GREEN}Invalidating CloudFront cache...${NC}"
    aws cloudfront create-invalidation \
        --distribution-id "${DISTRIBUTION_ID}" \
        --paths "/*"
    echo -e "${GREEN}✓ CloudFront cache invalidated${NC}"
else
    echo -e "${YELLOW}Warning: CloudFront distribution not found, skipping cache invalidation${NC}"
fi

echo ""
echo -e "${GREEN}=== Frontend Deployment Complete ===${NC}"
echo -e "${YELLOW}Access your frontend at: https://$(aws cloudfront get-distribution --id ${DISTRIBUTION_ID} --query 'Distribution.DomainName' --output text)${NC}"