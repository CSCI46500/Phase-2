#!/bin/bash
set -e

# AWS Deployment Script for Model Registry
# This script automates the deployment of the Model Registry to AWS

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    command -v aws >/dev/null 2>&1 || { log_error "AWS CLI is required but not installed. Aborting."; exit 1; }
    command -v docker >/dev/null 2>&1 || { log_error "Docker is required but not installed. Aborting."; exit 1; }
    command -v jq >/dev/null 2>&1 || { log_error "jq is required but not installed. Aborting."; exit 1; }

    log_info "All prerequisites met."
}

load_config() {
    log_info "Loading configuration..."

    if [ ! -f ".env.aws" ]; then
        log_error ".env.aws file not found. Please create it from .env.aws.template"
        exit 1
    fi

    source .env.aws

    # Validate required variables
    if [ -z "$AWS_REGION" ] || [ -z "$PROJECT_NAME" ]; then
        log_error "Required environment variables not set in .env.aws"
        exit 1
    fi

    # Get AWS account ID
    export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    log_info "AWS Account ID: $AWS_ACCOUNT_ID"
    log_info "AWS Region: $AWS_REGION"
    log_info "Project Name: $PROJECT_NAME"
}

create_ecr_repositories() {
    log_info "Creating ECR repositories..."

    # Backend repository
    if aws ecr describe-repositories --repository-names ${ECR_BACKEND_REPO} --region ${AWS_REGION} 2>/dev/null; then
        log_warn "Backend ECR repository already exists"
    else
        aws ecr create-repository \
            --repository-name ${ECR_BACKEND_REPO} \
            --region ${AWS_REGION} \
            --image-scanning-configuration scanOnPush=true
        log_info "Created backend ECR repository"
    fi

    # Frontend repository
    if aws ecr describe-repositories --repository-names ${ECR_FRONTEND_REPO} --region ${AWS_REGION} 2>/dev/null; then
        log_warn "Frontend ECR repository already exists"
    else
        aws ecr create-repository \
            --repository-name ${ECR_FRONTEND_REPO} \
            --region ${AWS_REGION} \
            --image-scanning-configuration scanOnPush=true
        log_info "Created frontend ECR repository"
    fi

    # Get repository URIs
    export BACKEND_REPO_URI=$(aws ecr describe-repositories \
        --repository-names ${ECR_BACKEND_REPO} \
        --region ${AWS_REGION} \
        --query 'repositories[0].repositoryUri' \
        --output text)

    export FRONTEND_REPO_URI=$(aws ecr describe-repositories \
        --repository-names ${ECR_FRONTEND_REPO} \
        --region ${AWS_REGION} \
        --query 'repositories[0].repositoryUri' \
        --output text)

    log_info "Backend URI: $BACKEND_REPO_URI"
    log_info "Frontend URI: $FRONTEND_REPO_URI"
}

create_s3_bucket() {
    log_info "Creating S3 bucket for model storage..."

    if aws s3 ls "s3://${S3_BUCKET_NAME}" 2>/dev/null; then
        log_warn "S3 bucket already exists"
    else
        aws s3 mb "s3://${S3_BUCKET_NAME}" --region ${AWS_REGION}

        # Enable versioning
        aws s3api put-bucket-versioning \
            --bucket ${S3_BUCKET_NAME} \
            --versioning-configuration Status=Enabled

        # Block public access
        aws s3api put-public-access-block \
            --bucket ${S3_BUCKET_NAME} \
            --public-access-block-configuration \
            "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

        # Enable encryption
        aws s3api put-bucket-encryption \
            --bucket ${S3_BUCKET_NAME} \
            --server-side-encryption-configuration \
            '{"Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]}'

        log_info "Created and configured S3 bucket: ${S3_BUCKET_NAME}"
    fi
}

create_rds_database() {
    log_info "Creating RDS PostgreSQL database..."

    # Check if RDS instance already exists
    if aws rds describe-db-instances --db-instance-identifier ${PROJECT_NAME}-db 2>/dev/null | grep -q "DBInstanceIdentifier"; then
        log_warn "RDS instance already exists"
        export DB_ENDPOINT=$(aws rds describe-db-instances \
            --db-instance-identifier ${PROJECT_NAME}-db \
            --query 'DBInstances[0].Endpoint.Address' \
            --output text)
        log_info "RDS Endpoint: $DB_ENDPOINT"
        return
    fi

    # Get default VPC
    export VPC_ID=$(aws ec2 describe-vpcs \
        --filters "Name=isDefault,Values=true" \
        --query 'Vpcs[0].VpcId' \
        --output text)

    log_info "Using VPC: $VPC_ID"

    # Create security group for RDS
    if aws ec2 describe-security-groups --filters "Name=group-name,Values=${PROJECT_NAME}-rds-sg" 2>/dev/null | grep -q "GroupId"; then
        log_warn "RDS security group already exists"
        export RDS_SG_ID=$(aws ec2 describe-security-groups \
            --filters "Name=group-name,Values=${PROJECT_NAME}-rds-sg" \
            --query 'SecurityGroups[0].GroupId' \
            --output text)
    else
        aws ec2 create-security-group \
            --group-name ${PROJECT_NAME}-rds-sg \
            --description "Security group for RDS PostgreSQL" \
            --vpc-id ${VPC_ID}

        export RDS_SG_ID=$(aws ec2 describe-security-groups \
            --filters "Name=group-name,Values=${PROJECT_NAME}-rds-sg" \
            --query 'SecurityGroups[0].GroupId' \
            --output text)

        # Allow PostgreSQL access (will be restricted to ECS later)
        aws ec2 authorize-security-group-ingress \
            --group-id ${RDS_SG_ID} \
            --protocol tcp \
            --port 5432 \
            --cidr 0.0.0.0/0

        log_info "Created RDS security group: $RDS_SG_ID"
    fi

    # Create RDS instance
    log_info "Creating RDS instance (this will take 5-10 minutes)..."
    aws rds create-db-instance \
        --db-instance-identifier ${PROJECT_NAME}-db \
        --db-instance-class ${DB_INSTANCE_CLASS} \
        --engine postgres \
        --engine-version 16.3 \
        --master-username ${DB_USERNAME} \
        --master-user-password ${DB_PASSWORD} \
        --allocated-storage ${DB_ALLOCATED_STORAGE} \
        --vpc-security-group-ids ${RDS_SG_ID} \
        --publicly-accessible \
        --backup-retention-period 1 \
        --region ${AWS_REGION}

    # Wait for RDS to be available
    log_info "Waiting for RDS instance to be available..."
    aws rds wait db-instance-available --db-instance-identifier ${PROJECT_NAME}-db

    # Get RDS endpoint
    export DB_ENDPOINT=$(aws rds describe-db-instances \
        --db-instance-identifier ${PROJECT_NAME}-db \
        --query 'DBInstances[0].Endpoint.Address' \
        --output text)

    log_info "RDS instance created. Endpoint: $DB_ENDPOINT"
}

create_ecs_cluster() {
    log_info "Creating ECS cluster..."

    if aws ecs describe-clusters --clusters ${ECS_CLUSTER_NAME} --region ${AWS_REGION} 2>/dev/null | grep -q "ACTIVE"; then
        log_warn "ECS cluster already exists"
    else
        aws ecs create-cluster \
            --cluster-name ${ECS_CLUSTER_NAME} \
            --region ${AWS_REGION}
        log_info "Created ECS cluster: ${ECS_CLUSTER_NAME}"
    fi
}

build_and_push_images() {
    log_info "Building and pushing Docker images..."

    # Authenticate Docker to ECR
    aws ecr get-login-password --region ${AWS_REGION} | \
        docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

    # Generate timestamp once
    TIMESTAMP=$(date +%Y%m%d-%H%M%S)

    # Build backend image
    log_info "Building backend image..."
    docker build -t ${ECR_BACKEND_REPO}:latest -f Dockerfile.production .

    # Tag and push backend
    docker tag ${ECR_BACKEND_REPO}:latest ${BACKEND_REPO_URI}:latest
    docker tag ${ECR_BACKEND_REPO}:latest ${BACKEND_REPO_URI}:${TIMESTAMP}

    log_info "Pushing backend image to ECR..."
    docker push ${BACKEND_REPO_URI}:latest
    docker push ${BACKEND_REPO_URI}:${TIMESTAMP}

    # Build frontend image
    log_info "Building frontend image..."
    cd front-end/model-registry-frontend
    docker build -t ${ECR_FRONTEND_REPO}:latest -f Dockerfile.production .

    # Tag and push frontend
    docker tag ${ECR_FRONTEND_REPO}:latest ${FRONTEND_REPO_URI}:latest
    docker tag ${ECR_FRONTEND_REPO}:latest ${FRONTEND_REPO_URI}:${TIMESTAMP}

    log_info "Pushing frontend image to ECR..."
    docker push ${FRONTEND_REPO_URI}:latest
    docker push ${FRONTEND_REPO_URI}:${TIMESTAMP}

    cd ../..

    log_info "Docker images built and pushed successfully"
}

create_iam_roles() {
    log_info "Creating IAM roles..."

    # Create trust policy
    cat > /tmp/ecs-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

    # Create execution role
    if aws iam get-role --role-name ${PROJECT_NAME}-ecs-execution-role 2>/dev/null; then
        log_warn "ECS execution role already exists"
    else
        aws iam create-role \
            --role-name ${PROJECT_NAME}-ecs-execution-role \
            --assume-role-policy-document file:///tmp/ecs-trust-policy.json

        aws iam attach-role-policy \
            --role-name ${PROJECT_NAME}-ecs-execution-role \
            --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

        log_info "Created ECS execution role"
    fi

    # Create task role
    if aws iam get-role --role-name ${PROJECT_NAME}-ecs-task-role 2>/dev/null; then
        log_warn "ECS task role already exists"
    else
        aws iam create-role \
            --role-name ${PROJECT_NAME}-ecs-task-role \
            --assume-role-policy-document file:///tmp/ecs-trust-policy.json

        # Create task policy
        cat > /tmp/ecs-task-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::${S3_BUCKET_NAME}",
        "arn:aws:s3:::${S3_BUCKET_NAME}/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
EOF

        aws iam put-role-policy \
            --role-name ${PROJECT_NAME}-ecs-task-role \
            --policy-name ${PROJECT_NAME}-task-permissions \
            --policy-document file:///tmp/ecs-task-policy.json

        log_info "Created ECS task role"
    fi

    export EXECUTION_ROLE_ARN=$(aws iam get-role \
        --role-name ${PROJECT_NAME}-ecs-execution-role \
        --query 'Role.Arn' \
        --output text)

    export TASK_ROLE_ARN=$(aws iam get-role \
        --role-name ${PROJECT_NAME}-ecs-task-role \
        --query 'Role.Arn' \
        --output text)

    log_info "IAM roles configured"
}

create_load_balancer() {
    log_info "Creating Application Load Balancer..."

    # Get VPC and subnets
    export VPC_ID=$(aws ec2 describe-vpcs \
        --filters "Name=isDefault,Values=true" \
        --query 'Vpcs[0].VpcId' \
        --output text)

    export SUBNET_IDS=$(aws ec2 describe-subnets \
        --filters "Name=vpc-id,Values=${VPC_ID}" \
        --query 'Subnets[0:2].SubnetId' \
        --output json | jq -r '.[]' | tr '\n' ' ')

    # Create ALB security group
    if aws ec2 describe-security-groups --filters "Name=group-name,Values=${PROJECT_NAME}-alb-sg" 2>/dev/null | grep -q "GroupId"; then
        log_warn "ALB security group already exists"
        export ALB_SG_ID=$(aws ec2 describe-security-groups \
            --filters "Name=group-name,Values=${PROJECT_NAME}-alb-sg" \
            --query 'SecurityGroups[0].GroupId' \
            --output text)
    else
        aws ec2 create-security-group \
            --group-name ${PROJECT_NAME}-alb-sg \
            --description "Security group for Application Load Balancer" \
            --vpc-id ${VPC_ID}

        export ALB_SG_ID=$(aws ec2 describe-security-groups \
            --filters "Name=group-name,Values=${PROJECT_NAME}-alb-sg" \
            --query 'SecurityGroups[0].GroupId' \
            --output text)

        aws ec2 authorize-security-group-ingress \
            --group-id ${ALB_SG_ID} \
            --protocol tcp \
            --port 80 \
            --cidr 0.0.0.0/0

        log_info "Created ALB security group"
    fi

    # Create ECS security group for backend
    if aws ec2 describe-security-groups --filters "Name=group-name,Values=${PROJECT_NAME}-ecs-backend-sg" 2>/dev/null | grep -q "GroupId"; then
        log_warn "ECS backend security group already exists"
        export ECS_BACKEND_SG_ID=$(aws ec2 describe-security-groups \
            --filters "Name=group-name,Values=${PROJECT_NAME}-ecs-backend-sg" \
            --query 'SecurityGroups[0].GroupId' \
            --output text)
    else
        aws ec2 create-security-group \
            --group-name ${PROJECT_NAME}-ecs-backend-sg \
            --description "Security group for ECS backend tasks" \
            --vpc-id ${VPC_ID}

        export ECS_BACKEND_SG_ID=$(aws ec2 describe-security-groups \
            --filters "Name=group-name,Values=${PROJECT_NAME}-ecs-backend-sg" \
            --query 'SecurityGroups[0].GroupId' \
            --output text)

        aws ec2 authorize-security-group-ingress \
            --group-id ${ECS_BACKEND_SG_ID} \
            --protocol tcp \
            --port 8000 \
            --source-group ${ALB_SG_ID}

        log_info "Created ECS backend security group"
    fi

    # Create ECS security group for frontend
    if aws ec2 describe-security-groups --filters "Name=group-name,Values=${PROJECT_NAME}-ecs-frontend-sg" 2>/dev/null | grep -q "GroupId"; then
        log_warn "ECS frontend security group already exists"
        export ECS_FRONTEND_SG_ID=$(aws ec2 describe-security-groups \
            --filters "Name=group-name,Values=${PROJECT_NAME}-ecs-frontend-sg" \
            --query 'SecurityGroups[0].GroupId' \
            --output text)
    else
        aws ec2 create-security-group \
            --group-name ${PROJECT_NAME}-ecs-frontend-sg \
            --description "Security group for ECS frontend tasks" \
            --vpc-id ${VPC_ID}

        export ECS_FRONTEND_SG_ID=$(aws ec2 describe-security-groups \
            --filters "Name=group-name,Values=${PROJECT_NAME}-ecs-frontend-sg" \
            --query 'SecurityGroups[0].GroupId' \
            --output text)

        aws ec2 authorize-security-group-ingress \
            --group-id ${ECS_FRONTEND_SG_ID} \
            --protocol tcp \
            --port 80 \
            --source-group ${ALB_SG_ID}

        log_info "Created ECS frontend security group"
    fi

    # Create load balancer
    if aws elbv2 describe-load-balancers --names ${PROJECT_NAME}-alb 2>/dev/null | grep -q "LoadBalancerArn"; then
        log_warn "Load balancer already exists"
        export ALB_ARN=$(aws elbv2 describe-load-balancers \
            --names ${PROJECT_NAME}-alb \
            --query 'LoadBalancers[0].LoadBalancerArn' \
            --output text)
        export ALB_DNS=$(aws elbv2 describe-load-balancers \
            --names ${PROJECT_NAME}-alb \
            --query 'LoadBalancers[0].DNSName' \
            --output text)
    else
        aws elbv2 create-load-balancer \
            --name ${PROJECT_NAME}-alb \
            --subnets ${SUBNET_IDS} \
            --security-groups ${ALB_SG_ID} \
            --scheme internet-facing \
            --type application

        export ALB_ARN=$(aws elbv2 describe-load-balancers \
            --names ${PROJECT_NAME}-alb \
            --query 'LoadBalancers[0].LoadBalancerArn' \
            --output text)

        export ALB_DNS=$(aws elbv2 describe-load-balancers \
            --names ${PROJECT_NAME}-alb \
            --query 'LoadBalancers[0].DNSName' \
            --output text)

        log_info "Created load balancer: $ALB_DNS"
    fi

    # Create backend target group
    if aws elbv2 describe-target-groups --names ${PROJECT_NAME}-backend-tg 2>/dev/null | grep -q "TargetGroupArn"; then
        log_warn "Backend target group already exists"
        export BACKEND_TG_ARN=$(aws elbv2 describe-target-groups \
            --names ${PROJECT_NAME}-backend-tg \
            --query 'TargetGroups[0].TargetGroupArn' \
            --output text)
    else
        aws elbv2 create-target-group \
            --name ${PROJECT_NAME}-backend-tg \
            --protocol HTTP \
            --port 8000 \
            --vpc-id ${VPC_ID} \
            --target-type ip \
            --health-check-path /health \
            --health-check-interval-seconds 30

        export BACKEND_TG_ARN=$(aws elbv2 describe-target-groups \
            --names ${PROJECT_NAME}-backend-tg \
            --query 'TargetGroups[0].TargetGroupArn' \
            --output text)

        log_info "Created backend target group"
    fi

    # Create frontend target group
    if aws elbv2 describe-target-groups --names ${PROJECT_NAME}-frontend-tg 2>/dev/null | grep -q "TargetGroupArn"; then
        log_warn "Frontend target group already exists"
        export FRONTEND_TG_ARN=$(aws elbv2 describe-target-groups \
            --names ${PROJECT_NAME}-frontend-tg \
            --query 'TargetGroups[0].TargetGroupArn' \
            --output text)
    else
        aws elbv2 create-target-group \
            --name ${PROJECT_NAME}-frontend-tg \
            --protocol HTTP \
            --port 80 \
            --vpc-id ${VPC_ID} \
            --target-type ip \
            --health-check-path / \
            --health-check-interval-seconds 30 \
            --matcher HttpCode=200,404

        export FRONTEND_TG_ARN=$(aws elbv2 describe-target-groups \
            --names ${PROJECT_NAME}-frontend-tg \
            --query 'TargetGroups[0].TargetGroupArn' \
            --output text)

        log_info "Created frontend target group"
    fi

    # Get or create listener
    export LISTENER_ARN=$(aws elbv2 describe-listeners --load-balancer-arn ${ALB_ARN} --query 'Listeners[0].ListenerArn' --output text 2>/dev/null)

    if [ "$LISTENER_ARN" != "None" ] && [ -n "$LISTENER_ARN" ]; then
        log_warn "Listener already exists"
    else
        # Create listener with frontend as default action
        aws elbv2 create-listener \
            --load-balancer-arn ${ALB_ARN} \
            --protocol HTTP \
            --port 80 \
            --default-actions Type=forward,TargetGroupArn=${FRONTEND_TG_ARN}

        export LISTENER_ARN=$(aws elbv2 describe-listeners --load-balancer-arn ${ALB_ARN} --query 'Listeners[0].ListenerArn' --output text)
        log_info "Created listener"
    fi

    # Create or update listener rules for API routing
    # Get existing rules to check priorities
    EXISTING_RULES=$(aws elbv2 describe-rules --listener-arn ${LISTENER_ARN} --query 'Rules[?Priority!=`default`].Priority' --output text 2>/dev/null || echo "")

    # Rule 1: Forward /api/* to backend
    if echo "$EXISTING_RULES" | grep -qw "1"; then
        log_warn "API routing rule priority 1 already exists, skipping"
    else
        aws elbv2 create-rule \
            --listener-arn ${LISTENER_ARN} \
            --priority 1 \
            --conditions Field=path-pattern,Values='/api/*' \
            --actions Type=forward,TargetGroupArn=${BACKEND_TG_ARN} 2>/dev/null || log_warn "Rule 1 creation failed (may already exist)"
        log_info "Created /api/* routing rule"
    fi

    # Rule 2: Forward /authenticate, /tracks, /health, /packages, /package, /reset, /logs, /user to backend
    if echo "$EXISTING_RULES" | grep -qw "2"; then
        log_warn "Root API routing rule priority 2 already exists, skipping"
    else
        aws elbv2 create-rule \
            --listener-arn ${LISTENER_ARN} \
            --priority 2 \
            --conditions Field=path-pattern,Values='/authenticate,/tracks,/health,/packages,/package/*,/reset,/logs,/user/*,/docs,/openapi.json' \
            --actions Type=forward,TargetGroupArn=${BACKEND_TG_ARN} 2>/dev/null || log_warn "Rule 2 creation failed (may already exist)"
        log_info "Created root API routing rule"
    fi
}

deploy_ecs_service() {
    log_info "Deploying ECS services..."

    # ==== BACKEND SERVICE ====
    log_info "Deploying backend service..."

    # Create CloudWatch log group for backend
    if aws logs describe-log-groups --log-group-name-prefix "/ecs/${PROJECT_NAME}-backend" 2>/dev/null | grep -q "logGroupName"; then
        log_warn "Backend CloudWatch log group already exists"
    else
        aws logs create-log-group --log-group-name /ecs/${PROJECT_NAME}-backend
        aws logs put-retention-policy \
            --log-group-name /ecs/${PROJECT_NAME}-backend \
            --retention-in-days 7
        log_info "Created backend CloudWatch log group"
    fi

    # Register backend task definition
    # Use jq to properly escape the admin password for JSON
    ESCAPED_ADMIN_PASSWORD=$(echo -n "$ADMIN_PASSWORD" | jq -R .)

    cat > /tmp/backend-task-def.json <<EOF
{
  "family": "${PROJECT_NAME}-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "${EXECUTION_ROLE_ARN}",
  "taskRoleArn": "${TASK_ROLE_ARN}",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "${BACKEND_REPO_URI}:latest",
      "portMappings": [{"containerPort": 8000, "protocol": "tcp"}],
      "essential": true,
      "environment": [
        {"name": "PYTHONPATH", "value": "/app"},
        {"name": "DATABASE_URL", "value": "postgresql://${DB_USERNAME}:${DB_PASSWORD}@${DB_ENDPOINT}:5432/${DB_NAME}"},
        {"name": "S3_BUCKET_NAME", "value": "${S3_BUCKET_NAME}"},
        {"name": "AWS_REGION", "value": "${AWS_REGION}"},
        {"name": "ENVIRONMENT", "value": "aws"},
        {"name": "LOG_LEVEL", "value": "1"},
        {"name": "ADMIN_USERNAME", "value": "${ADMIN_USERNAME}"},
        {"name": "ADMIN_PASSWORD", "value": ${ESCAPED_ADMIN_PASSWORD}},
        {"name": "SECRET_KEY", "value": "${SECRET_KEY}"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/${PROJECT_NAME}-backend",
          "awslogs-region": "${AWS_REGION}",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
EOF

    aws ecs register-task-definition --cli-input-json file:///tmp/backend-task-def.json
    log_info "Registered backend task definition"

    # Create or update backend service
    SUBNET_ARRAY=$(echo ${SUBNET_IDS} | jq -R 'split(" ")')

    if aws ecs describe-services --cluster ${ECS_CLUSTER_NAME} --services ${ECS_BACKEND_SERVICE} 2>/dev/null | grep -q "ACTIVE"; then
        log_info "Updating existing backend ECS service..."
        aws ecs update-service \
            --cluster ${ECS_CLUSTER_NAME} \
            --service ${ECS_BACKEND_SERVICE} \
            --force-new-deployment
    else
        log_info "Creating backend ECS service..."
        aws ecs create-service \
            --cluster ${ECS_CLUSTER_NAME} \
            --service-name ${ECS_BACKEND_SERVICE} \
            --task-definition ${PROJECT_NAME}-backend \
            --desired-count 1 \
            --launch-type FARGATE \
            --network-configuration "awsvpcConfiguration={subnets=${SUBNET_ARRAY},securityGroups=[\"${ECS_BACKEND_SG_ID}\"],assignPublicIp=ENABLED}" \
            --load-balancers "targetGroupArn=${BACKEND_TG_ARN},containerName=backend,containerPort=8000" \
            --health-check-grace-period-seconds 60
    fi

    # ==== FRONTEND SERVICE ====
    log_info "Deploying frontend service..."

    # Create CloudWatch log group for frontend
    if aws logs describe-log-groups --log-group-name-prefix "/ecs/${PROJECT_NAME}-frontend" 2>/dev/null | grep -q "logGroupName"; then
        log_warn "Frontend CloudWatch log group already exists"
    else
        aws logs create-log-group --log-group-name /ecs/${PROJECT_NAME}-frontend
        aws logs put-retention-policy \
            --log-group-name /ecs/${PROJECT_NAME}-frontend \
            --retention-in-days 7
        log_info "Created frontend CloudWatch log group"
    fi

    # Register frontend task definition
    cat > /tmp/frontend-task-def.json <<EOF
{
  "family": "${PROJECT_NAME}-frontend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "${EXECUTION_ROLE_ARN}",
  "containerDefinitions": [
    {
      "name": "frontend",
      "image": "${FRONTEND_REPO_URI}:latest",
      "portMappings": [{"containerPort": 80, "protocol": "tcp"}],
      "essential": true,
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/${PROJECT_NAME}-frontend",
          "awslogs-region": "${AWS_REGION}",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
EOF

    aws ecs register-task-definition --cli-input-json file:///tmp/frontend-task-def.json
    log_info "Registered frontend task definition"

    # Create or update frontend service
    if aws ecs describe-services --cluster ${ECS_CLUSTER_NAME} --services ${ECS_FRONTEND_SERVICE} 2>/dev/null | grep -q "ACTIVE"; then
        log_info "Updating existing frontend ECS service..."
        aws ecs update-service \
            --cluster ${ECS_CLUSTER_NAME} \
            --service ${ECS_FRONTEND_SERVICE} \
            --force-new-deployment
    else
        log_info "Creating frontend ECS service..."
        aws ecs create-service \
            --cluster ${ECS_CLUSTER_NAME} \
            --service-name ${ECS_FRONTEND_SERVICE} \
            --task-definition ${PROJECT_NAME}-frontend \
            --desired-count 1 \
            --launch-type FARGATE \
            --network-configuration "awsvpcConfiguration={subnets=${SUBNET_ARRAY},securityGroups=[\"${ECS_FRONTEND_SG_ID}\"],assignPublicIp=ENABLED}" \
            --load-balancers "targetGroupArn=${FRONTEND_TG_ARN},containerName=frontend,containerPort=80" \
            --health-check-grace-period-seconds 60
    fi

    log_info "Waiting for services to stabilize..."
    aws ecs wait services-stable --cluster ${ECS_CLUSTER_NAME} --services ${ECS_BACKEND_SERVICE} ${ECS_FRONTEND_SERVICE}

    log_info "Deployment complete!"
}

print_summary() {
    echo ""
    echo "=========================================="
    echo "  AWS Deployment Summary"
    echo "=========================================="
    echo ""
    echo "Application URL: http://${ALB_DNS}"
    echo "API Endpoint: http://${ALB_DNS}"
    echo "API Docs: http://${ALB_DNS}/docs"
    echo "Health Check: http://${ALB_DNS}/health"
    echo "Tracks Endpoint: http://${ALB_DNS}/tracks"
    echo ""
    echo "AWS Resources Created:"
    echo "  - ECR Repositories: ${ECR_BACKEND_REPO}, ${ECR_FRONTEND_REPO}"
    echo "  - S3 Bucket: ${S3_BUCKET_NAME}"
    echo "  - RDS Instance: ${PROJECT_NAME}-db (${DB_ENDPOINT})"
    echo "  - ECS Cluster: ${ECS_CLUSTER_NAME}"
    echo "  - ECS Services: ${ECS_BACKEND_SERVICE}, ${ECS_FRONTEND_SERVICE}"
    echo "  - Load Balancer: ${PROJECT_NAME}-alb"
    echo ""
    echo "Test your deployment:"
    echo "  curl http://${ALB_DNS}/health"
    echo "  curl http://${ALB_DNS}/tracks"
    echo ""
    echo "Submit to autograder:"
    echo "  URL: http://${ALB_DNS}"
    echo ""
    echo "=========================================="
}

# Main execution
main() {
    log_info "Starting AWS deployment..."

    check_prerequisites
    load_config
    create_ecr_repositories
    create_s3_bucket
    create_rds_database
    create_ecs_cluster
    build_and_push_images
    create_iam_roles
    create_load_balancer
    deploy_ecs_service
    print_summary

    log_info "Deployment completed successfully!"
}

main "$@"
