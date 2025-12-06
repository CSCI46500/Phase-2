#!/bin/bash
#
# Complete AWS Deployment Script for Phase 2 Model Registry
# This script sets up the entire AWS infrastructure and deploys the application
#
# Prerequisites:
# 1. AWS CLI installed and configured (aws configure)
# 2. Docker installed and running
# 3. .env.aws file configured with your settings
#
# Usage:
#   ./deploy-to-aws-complete.sh
#

set -e  # Exit on any error

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Load environment variables
if [ ! -f .env.aws ]; then
    echo -e "${RED}Error: .env.aws file not found${NC}"
    echo "Please copy .env.aws.template to .env.aws and configure it"
    exit 1
fi

source .env.aws

echo -e "${BLUE}=================================================="
echo "Phase 2 Model Registry - Complete AWS Deployment"
echo "==================================================${NC}"
echo ""

# Verify AWS credentials
echo -e "${YELLOW}Step 1: Verifying AWS credentials...${NC}"
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}Error: AWS credentials not configured${NC}"
    echo "Run: aws configure"
    exit 1
fi

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✓ AWS Account ID: $AWS_ACCOUNT_ID${NC}"
echo ""

# Create ECR repositories
echo -e "${YELLOW}Step 2: Creating ECR repositories...${NC}"

for REPO in $ECR_BACKEND_REPO $ECR_FRONTEND_REPO; do
    if aws ecr describe-repositories --repository-names $REPO &> /dev/null; then
        echo -e "${GREEN}✓ ECR repository $REPO already exists${NC}"
    else
        aws ecr create-repository \
            --repository-name $REPO \
            --image-scanning-configuration scanOnPush=true \
            --region $AWS_REGION
        echo -e "${GREEN}✓ Created ECR repository: $REPO${NC}"
    fi
done
echo ""

# Create S3 bucket
echo -e "${YELLOW}Step 3: Creating S3 bucket...${NC}"

if aws s3 ls "s3://$S3_BUCKET_NAME" &> /dev/null; then
    echo -e "${GREEN}✓ S3 bucket $S3_BUCKET_NAME already exists${NC}"
else
    aws s3 mb "s3://$S3_BUCKET_NAME" --region $AWS_REGION

    # Enable versioning (optional but recommended)
    aws s3api put-bucket-versioning \
        --bucket $S3_BUCKET_NAME \
        --versioning-configuration Status=Enabled

    # Enable encryption
    aws s3api put-bucket-encryption \
        --bucket $S3_BUCKET_NAME \
        --server-side-encryption-configuration '{
            "Rules": [{
                "ApplyServerSideEncryptionByDefault": {
                    "SSEAlgorithm": "AES256"
                }
            }]
        }'

    echo -e "${GREEN}✓ Created S3 bucket: $S3_BUCKET_NAME${NC}"
fi
echo ""

# Create RDS database
echo -e "${YELLOW}Step 4: Creating RDS PostgreSQL database...${NC}"

RDS_INSTANCE_ID="${PROJECT_NAME}-db"

if aws rds describe-db-instances --db-instance-identifier $RDS_INSTANCE_ID &> /dev/null; then
    echo -e "${GREEN}✓ RDS instance $RDS_INSTANCE_ID already exists${NC}"

    # Get endpoint
    DB_ENDPOINT=$(aws rds describe-db-instances \
        --db-instance-identifier $RDS_INSTANCE_ID \
        --query 'DBInstances[0].Endpoint.Address' \
        --output text)

    echo -e "${GREEN}  Endpoint: $DB_ENDPOINT${NC}"
else
    echo -e "${BLUE}Creating RDS instance (this takes ~10 minutes)...${NC}"

    # Create DB subnet group
    aws rds create-db-subnet-group \
        --db-subnet-group-name "${PROJECT_NAME}-subnet-group" \
        --db-subnet-group-description "Subnet group for ${PROJECT_NAME}" \
        --subnet-ids $(aws ec2 describe-subnets --query 'Subnets[0:2].SubnetId' --output text) \
        || echo "Subnet group may already exist"

    # Create RDS instance
    aws rds create-db-instance \
        --db-instance-identifier $RDS_INSTANCE_ID \
        --db-instance-class $DB_INSTANCE_CLASS \
        --engine postgres \
        --engine-version 17.6 \
        --master-username $DB_USERNAME \
        --master-user-password "$DB_PASSWORD" \
        --allocated-storage $DB_ALLOCATED_STORAGE \
        --db-name $DB_NAME \
        --publicly-accessible \
        --backup-retention-period 0 \
        --no-storage-encrypted \
        --region $AWS_REGION

    echo -e "${BLUE}Waiting for RDS instance to be available...${NC}"
    aws rds wait db-instance-available --db-instance-identifier $RDS_INSTANCE_ID

    DB_ENDPOINT=$(aws rds describe-db-instances \
        --db-instance-identifier $RDS_INSTANCE_ID \
        --query 'DBInstances[0].Endpoint.Address' \
        --output text)

    echo -e "${GREEN}✓ Created RDS instance: $RDS_INSTANCE_ID${NC}"
    echo -e "${GREEN}  Endpoint: $DB_ENDPOINT${NC}"
fi
echo ""

# Build and push Docker images
echo -e "${YELLOW}Step 5: Building and pushing Docker images...${NC}"

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Build backend image
echo -e "${BLUE}Building backend image...${NC}"
docker build -f Dockerfile.production -t $ECR_BACKEND_REPO .

# Tag and push backend
docker tag $ECR_BACKEND_REPO:latest ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/$ECR_BACKEND_REPO:latest
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/$ECR_BACKEND_REPO:latest

echo -e "${GREEN}✓ Pushed backend image${NC}"

# Build frontend image
echo -e "${BLUE}Building frontend image...${NC}"
cd front-end/model-registry-frontend
docker build -f Dockerfile.production -t $ECR_FRONTEND_REPO .

# Tag and push frontend
docker tag $ECR_FRONTEND_REPO:latest ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/$ECR_FRONTEND_REPO:latest
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/$ECR_FRONTEND_REPO:latest

cd ../..
echo -e "${GREEN}✓ Pushed frontend image${NC}"
echo ""

# Create ECS cluster
echo -e "${YELLOW}Step 6: Creating ECS cluster...${NC}"

CLUSTER_STATUS=$(aws ecs describe-clusters --clusters $ECS_CLUSTER_NAME --region $AWS_REGION --query 'clusters[0].status' --output text 2>/dev/null)

if [ "$CLUSTER_STATUS" == "ACTIVE" ]; then
    echo -e "${GREEN}✓ ECS cluster $ECS_CLUSTER_NAME already exists${NC}"
else
    aws ecs create-cluster --cluster-name $ECS_CLUSTER_NAME --region $AWS_REGION
    echo -e "${GREEN}✓ Created ECS cluster: $ECS_CLUSTER_NAME${NC}"
fi
echo ""

# Create task execution role
echo -e "${YELLOW}Step 7: Creating ECS task execution role...${NC}"

ROLE_NAME="ecsTaskExecutionRole-${PROJECT_NAME}"

if aws iam get-role --role-name $ROLE_NAME &> /dev/null; then
    echo -e "${GREEN}✓ IAM role $ROLE_NAME already exists${NC}"
else
    # Create trust policy
    cat > /tmp/trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Service": "ecs-tasks.amazonaws.com"
    },
    "Action": "sts:AssumeRole"
  }]
}
EOF

    aws iam create-role \
        --role-name $ROLE_NAME \
        --assume-role-policy-document file:///tmp/trust-policy.json

    # Attach policies
    aws iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

    aws iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess

    aws iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly

    echo -e "${GREEN}✓ Created IAM role: $ROLE_NAME${NC}"
fi

TASK_ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)
echo ""

# Create CloudWatch log group
echo -e "${YELLOW}Step 8: Creating CloudWatch log groups...${NC}"

for LOG_GROUP in "/ecs/${PROJECT_NAME}-backend" "/ecs/${PROJECT_NAME}-frontend"; do
    if aws logs describe-log-groups --log-group-name-prefix $LOG_GROUP &> /dev/null; then
        echo -e "${GREEN}✓ Log group $LOG_GROUP already exists${NC}"
    else
        aws logs create-log-group --log-group-name $LOG_GROUP --region $AWS_REGION
        aws logs put-retention-policy \
            --log-group-name $LOG_GROUP \
            --retention-in-days $LOG_RETENTION_DAYS
        echo -e "${GREEN}✓ Created log group: $LOG_GROUP${NC}"
    fi
done
echo ""

# Register task definitions
echo -e "${YELLOW}Step 9: Registering ECS task definitions...${NC}"

# Backend task definition
cat > /tmp/backend-task-def.json <<EOF
{
  "family": "${PROJECT_NAME}-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "${TASK_ROLE_ARN}",
  "taskRoleArn": "${TASK_ROLE_ARN}",
  "containerDefinitions": [{
    "name": "backend",
    "image": "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_BACKEND_REPO}:latest",
    "essential": true,
    "portMappings": [{
      "containerPort": 8000,
      "protocol": "tcp"
    }],
    "environment": [
      {"name": "DATABASE_URL", "value": "postgresql://${DB_USERNAME}:${DB_PASSWORD}@${DB_ENDPOINT}:5432/${DB_NAME}"},
      {"name": "S3_BUCKET_NAME", "value": "${S3_BUCKET_NAME}"},
      {"name": "AWS_REGION", "value": "${AWS_REGION}"},
      {"name": "ENVIRONMENT", "value": "${ENVIRONMENT}"},
      {"name": "SECRET_KEY", "value": "${SECRET_KEY}"},
      {"name": "ADMIN_USERNAME", "value": "${ADMIN_USERNAME}"},
      {"name": "ADMIN_PASSWORD", "value": "${ADMIN_PASSWORD}"}
    ],
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "/ecs/${PROJECT_NAME}-backend",
        "awslogs-region": "${AWS_REGION}",
        "awslogs-stream-prefix": "ecs"
      }
    },
    "healthCheck": {
      "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
      "interval": 30,
      "timeout": 5,
      "retries": 3,
      "startPeriod": 60
    }
  }]
}
EOF

aws ecs register-task-definition \
    --cli-input-json file:///tmp/backend-task-def.json \
    --region $AWS_REGION > /dev/null

echo -e "${GREEN}✓ Registered backend task definition${NC}"

# Frontend task definition
cat > /tmp/frontend-task-def.json <<EOF
{
  "family": "${PROJECT_NAME}-frontend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "${TASK_ROLE_ARN}",
  "containerDefinitions": [{
    "name": "frontend",
    "image": "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_FRONTEND_REPO}:latest",
    "essential": true,
    "portMappings": [{
      "containerPort": 80,
      "protocol": "tcp"
    }],
    "environment": [
      {"name": "VITE_API_URL", "value": "http://BACKEND_ALB_DNS"}
    ],
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "/ecs/${PROJECT_NAME}-frontend",
        "awslogs-region": "${AWS_REGION}",
        "awslogs-stream-prefix": "ecs"
      }
    }
  }]
}
EOF

aws ecs register-task-definition \
    --cli-input-json file:///tmp/frontend-task-def.json \
    --region $AWS_REGION > /dev/null

echo -e "${GREEN}✓ Registered frontend task definition${NC}"
echo ""

# Get default VPC and subnets
echo -e "${YELLOW}Step 10: Getting VPC configuration...${NC}"

VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query 'Vpcs[0].VpcId' --output text)
SUBNET_IDS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[*].SubnetId' --output text)
SUBNET_ARRAY=($SUBNET_IDS)

echo -e "${GREEN}✓ VPC ID: $VPC_ID${NC}"
echo -e "${GREEN}✓ Subnets: ${SUBNET_ARRAY[@]}${NC}"
echo ""

# Create security group
echo -e "${YELLOW}Step 11: Creating security group...${NC}"

SG_NAME="${PROJECT_NAME}-sg"

# Check if security group exists
SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=$SG_NAME" "Name=vpc-id,Values=$VPC_ID" \
    --query 'SecurityGroups[0].GroupId' \
    --output text 2>/dev/null || echo "")

if [ "$SG_ID" != "" ] && [ "$SG_ID" != "None" ]; then
    echo -e "${GREEN}✓ Security group $SG_NAME already exists (ID: $SG_ID)${NC}"
else
    SG_ID=$(aws ec2 create-security-group \
        --group-name $SG_NAME \
        --description "Security group for ${PROJECT_NAME}" \
        --vpc-id $VPC_ID \
        --query 'GroupId' \
        --output text)

    # Allow HTTP traffic
    aws ec2 authorize-security-group-ingress \
        --group-id $SG_ID \
        --protocol tcp \
        --port 80 \
        --cidr 0.0.0.0/0

    # Allow backend API port
    aws ec2 authorize-security-group-ingress \
        --group-id $SG_ID \
        --protocol tcp \
        --port 8000 \
        --cidr 0.0.0.0/0

    # Allow all traffic within security group
    aws ec2 authorize-security-group-ingress \
        --group-id $SG_ID \
        --protocol -1 \
        --source-group $SG_ID

    echo -e "${GREEN}✓ Created security group: $SG_ID${NC}"
fi
echo ""

# Create Application Load Balancer
echo -e "${YELLOW}Step 12: Creating Application Load Balancer...${NC}"

ALB_NAME="${PROJECT_NAME}-alb"

# Check if ALB exists
ALB_ARN=$(aws elbv2 describe-load-balancers \
    --names $ALB_NAME \
    --query 'LoadBalancers[0].LoadBalancerArn' \
    --output text 2>/dev/null || echo "")

if [ "$ALB_ARN" != "" ] && [ "$ALB_ARN" != "None" ]; then
    echo -e "${GREEN}✓ ALB $ALB_NAME already exists${NC}"
else
    ALB_ARN=$(aws elbv2 create-load-balancer \
        --name $ALB_NAME \
        --subnets ${SUBNET_ARRAY[0]} ${SUBNET_ARRAY[1]} \
        --security-groups $SG_ID \
        --scheme internet-facing \
        --type application \
        --ip-address-type ipv4 \
        --query 'LoadBalancers[0].LoadBalancerArn' \
        --output text)

    echo -e "${GREEN}✓ Created ALB: $ALB_NAME${NC}"
fi

ALB_DNS=$(aws elbv2 describe-load-balancers \
    --load-balancer-arns $ALB_ARN \
    --query 'LoadBalancers[0].DNSName' \
    --output text)

echo -e "${GREEN}✓ ALB DNS: $ALB_DNS${NC}"
echo ""

# Create target groups
echo -e "${YELLOW}Step 13: Creating target groups...${NC}"

# Backend target group
BACKEND_TG_NAME="${PROJECT_NAME}-backend-tg"
BACKEND_TG_ARN=$(aws elbv2 describe-target-groups \
    --names $BACKEND_TG_NAME \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text 2>/dev/null || echo "")

if [ "$BACKEND_TG_ARN" != "" ] && [ "$BACKEND_TG_ARN" != "None" ]; then
    echo -e "${GREEN}✓ Backend target group already exists${NC}"
else
    BACKEND_TG_ARN=$(aws elbv2 create-target-group \
        --name $BACKEND_TG_NAME \
        --protocol HTTP \
        --port 8000 \
        --vpc-id $VPC_ID \
        --target-type ip \
        --health-check-path /health \
        --health-check-interval-seconds 30 \
        --health-check-timeout-seconds 5 \
        --healthy-threshold-count 2 \
        --unhealthy-threshold-count 3 \
        --query 'TargetGroups[0].TargetGroupArn' \
        --output text)

    echo -e "${GREEN}✓ Created backend target group${NC}"
fi

# Frontend target group
FRONTEND_TG_NAME="${PROJECT_NAME}-frontend-tg"
FRONTEND_TG_ARN=$(aws elbv2 describe-target-groups \
    --names $FRONTEND_TG_NAME \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text 2>/dev/null || echo "")

if [ "$FRONTEND_TG_ARN" != "" ] && [ "$FRONTEND_TG_ARN" != "None" ]; then
    echo -e "${GREEN}✓ Frontend target group already exists${NC}"
else
    FRONTEND_TG_ARN=$(aws elbv2 create-target-group \
        --name $FRONTEND_TG_NAME \
        --protocol HTTP \
        --port 80 \
        --vpc-id $VPC_ID \
        --target-type ip \
        --health-check-path / \
        --health-check-interval-seconds 30 \
        --query 'TargetGroups[0].TargetGroupArn' \
        --output text)

    echo -e "${GREEN}✓ Created frontend target group${NC}"
fi
echo ""

# Create ALB listeners
echo -e "${YELLOW}Step 14: Creating ALB listeners...${NC}"

# Backend listener (port 8000)
BACKEND_LISTENER=$(aws elbv2 describe-listeners \
    --load-balancer-arn $ALB_ARN \
    --query "Listeners[?Port==\`8000\`].ListenerArn" \
    --output text)

if [ -z "$BACKEND_LISTENER" ] || [ "$BACKEND_LISTENER" == "None" ]; then
    aws elbv2 create-listener \
        --load-balancer-arn $ALB_ARN \
        --protocol HTTP \
        --port 8000 \
        --default-actions Type=forward,TargetGroupArn=$BACKEND_TG_ARN

    echo -e "${GREEN}✓ Created backend listener (port 8000)${NC}"
else
    echo -e "${GREEN}✓ Backend listener already exists${NC}"
fi

# Frontend listener (port 80)
FRONTEND_LISTENER=$(aws elbv2 describe-listeners \
    --load-balancer-arn $ALB_ARN \
    --query "Listeners[?Port==\`80\`].ListenerArn" \
    --output text)

if [ -z "$FRONTEND_LISTENER" ] || [ "$FRONTEND_LISTENER" == "None" ]; then
    aws elbv2 create-listener \
        --load-balancer-arn $ALB_ARN \
        --protocol HTTP \
        --port 80 \
        --default-actions Type=forward,TargetGroupArn=$FRONTEND_TG_ARN

    echo -e "${GREEN}✓ Created frontend listener (port 80)${NC}"
else
    echo -e "${GREEN}✓ Frontend listener already exists${NC}"
fi
echo ""

# Create ECS services
echo -e "${YELLOW}Step 15: Creating ECS services...${NC}"

# Backend service
if aws ecs describe-services \
    --cluster $ECS_CLUSTER_NAME \
    --services $ECS_BACKEND_SERVICE \
    --query 'services[0].serviceName' \
    --output text 2>/dev/null | grep -q "$ECS_BACKEND_SERVICE"; then

    echo -e "${GREEN}✓ Backend service already exists${NC}"

    # Update service with new task definition
    aws ecs update-service \
        --cluster $ECS_CLUSTER_NAME \
        --service $ECS_BACKEND_SERVICE \
        --force-new-deployment \
        --region $AWS_REGION > /dev/null

    echo -e "${GREEN}✓ Triggered backend service update${NC}"
else
    aws ecs create-service \
        --cluster $ECS_CLUSTER_NAME \
        --service-name $ECS_BACKEND_SERVICE \
        --task-definition ${PROJECT_NAME}-backend \
        --desired-count 1 \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[${SUBNET_ARRAY[0]},${SUBNET_ARRAY[1]}],securityGroups=[$SG_ID],assignPublicIp=ENABLED}" \
        --load-balancers "targetGroupArn=$BACKEND_TG_ARN,containerName=backend,containerPort=8000" \
        --region $AWS_REGION > /dev/null

    echo -e "${GREEN}✓ Created backend service${NC}"
fi

# Frontend service
if aws ecs describe-services \
    --cluster $ECS_CLUSTER_NAME \
    --services $ECS_FRONTEND_SERVICE \
    --query 'services[0].serviceName' \
    --output text 2>/dev/null | grep -q "$ECS_FRONTEND_SERVICE"; then

    echo -e "${GREEN}✓ Frontend service already exists${NC}"

    # Update service
    aws ecs update-service \
        --cluster $ECS_CLUSTER_NAME \
        --service $ECS_FRONTEND_SERVICE \
        --force-new-deployment \
        --region $AWS_REGION > /dev/null

    echo -e "${GREEN}✓ Triggered frontend service update${NC}"
else
    aws ecs create-service \
        --cluster $ECS_CLUSTER_NAME \
        --service-name $ECS_FRONTEND_SERVICE \
        --task-definition ${PROJECT_NAME}-frontend \
        --desired-count 1 \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[${SUBNET_ARRAY[0]},${SUBNET_ARRAY[1]}],securityGroups=[$SG_ID],assignPublicIp=ENABLED}" \
        --load-balancers "targetGroupArn=$FRONTEND_TG_ARN,containerName=frontend,containerPort=80" \
        --region $AWS_REGION > /dev/null

    echo -e "${GREEN}✓ Created frontend service${NC}"
fi
echo ""

# Wait for services to stabilize
echo -e "${YELLOW}Step 16: Waiting for services to stabilize...${NC}"
echo -e "${BLUE}This may take 5-10 minutes...${NC}"

aws ecs wait services-stable \
    --cluster $ECS_CLUSTER_NAME \
    --services $ECS_BACKEND_SERVICE \
    --region $AWS_REGION

echo -e "${GREEN}✓ Backend service is stable${NC}"

aws ecs wait services-stable \
    --cluster $ECS_CLUSTER_NAME \
    --services $ECS_FRONTEND_SERVICE \
    --region $AWS_REGION

echo -e "${GREEN}✓ Frontend service is stable${NC}"
echo ""

# Test endpoints
echo -e "${YELLOW}Step 17: Testing endpoints...${NC}"

BACKEND_URL="http://${ALB_DNS}:8000"
FRONTEND_URL="http://${ALB_DNS}"

echo -e "${BLUE}Testing backend health endpoint...${NC}"
if curl -f -s "${BACKEND_URL}/health" > /dev/null; then
    echo -e "${GREEN}✓ Backend is healthy!${NC}"
else
    echo -e "${RED}⚠ Backend health check failed (may need more time)${NC}"
fi

echo -e "${BLUE}Testing frontend...${NC}"
if curl -f -s "${FRONTEND_URL}" > /dev/null; then
    echo -e "${GREEN}✓ Frontend is accessible!${NC}"
else
    echo -e "${RED}⚠ Frontend not accessible yet (may need more time)${NC}"
fi
echo ""

# Summary
echo "=================================================="
echo -e "${GREEN}DEPLOYMENT COMPLETE!${NC}"
echo "=================================================="
echo ""
echo "📋 Deployment Summary:"
echo ""
echo "AWS Resources Created:"
echo "  ✓ ECR Repositories: $ECR_BACKEND_REPO, $ECR_FRONTEND_REPO"
echo "  ✓ S3 Bucket: $S3_BUCKET_NAME"
echo "  ✓ RDS Instance: $RDS_INSTANCE_ID"
echo "  ✓ ECS Cluster: $ECS_CLUSTER_NAME"
echo "  ✓ ECS Services: $ECS_BACKEND_SERVICE, $ECS_FRONTEND_SERVICE"
echo "  ✓ Application Load Balancer: $ALB_NAME"
echo "  ✓ CloudWatch Log Groups: /ecs/${PROJECT_NAME}-backend, /ecs/${PROJECT_NAME}-frontend"
echo ""
echo "🌐 Your Application URLs:"
echo ""
echo "  Backend API:  $BACKEND_URL"
echo "  Frontend UI:  $FRONTEND_URL"
echo ""
echo "📝 For Autograder Registration:"
echo ""
echo "  endpoint:     $BACKEND_URL"
echo "  fe_endpoint:  $FRONTEND_URL"
echo ""
echo "🔍 Useful Commands:"
echo ""
echo "  # View backend logs"
echo "  aws logs tail /ecs/${PROJECT_NAME}-backend --follow"
echo ""
echo "  # View frontend logs"
echo "  aws logs tail /ecs/${PROJECT_NAME}-frontend --follow"
echo ""
echo "  # Check service status"
echo "  aws ecs describe-services --cluster $ECS_CLUSTER_NAME --services $ECS_BACKEND_SERVICE"
echo ""
echo "  # Update backend service"
echo "  aws ecs update-service --cluster $ECS_CLUSTER_NAME --service $ECS_BACKEND_SERVICE --force-new-deployment"
echo ""
echo "=================================================="
echo ""

# Save URLs to file
cat > DEPLOYMENT_URLS.txt <<EOF
Phase 2 Model Registry - Deployment URLs
Generated: $(date)

Backend API:  $BACKEND_URL
Frontend UI:  $FRONTEND_URL

For Autograder Registration:
  endpoint:     $BACKEND_URL
  fe_endpoint:  $FRONTEND_URL

ALB DNS: $ALB_DNS
RDS Endpoint: $DB_ENDPOINT
S3 Bucket: $S3_BUCKET_NAME
EOF

echo -e "${GREEN}✓ Saved deployment URLs to DEPLOYMENT_URLS.txt${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Test your API: curl $BACKEND_URL/health"
echo "2. Visit frontend: open $FRONTEND_URL"
echo "3. Register with autograder using the URLs above"
echo ""
