# AWS Deployment Guide - Model Registry

This guide provides step-by-step instructions for deploying the Model Registry application to AWS using Docker containers.

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [AWS Services Setup](#aws-services-setup)
4. [Docker Configuration for AWS](#docker-configuration-for-aws)
5. [Deployment Steps](#deployment-steps)
6. [CI/CD with GitHub Actions](#cicd-with-github-actions)
7. [Monitoring and Logging](#monitoring-and-logging)
8. [Cost Management](#cost-management)
9. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### AWS Services Used (Meeting 2+ AWS Components Requirement)

1. **AWS ECR (Elastic Container Registry)** - Docker image storage
2. **AWS ECS (Elastic Container Service)** - Container orchestration
3. **AWS RDS (PostgreSQL)** - Managed database
4. **AWS S3** - Model/dataset storage
5. **AWS Application Load Balancer (ALB)** - Traffic distribution
6. **AWS CloudWatch** - Monitoring and logging
7. **AWS Secrets Manager** - Secure credentials storage

### Architecture Diagram

```
                           ┌─────────────────┐
                           │   GitHub Repo   │
                           └────────┬────────┘
                                    │
                        GitHub Actions CI/CD
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────┐
│                         AWS Cloud                            │
│                                                               │
│  ┌────────────────┐         ┌─────────────────┐             │
│  │  ECR Registry  │────────▶│   ECS Cluster   │             │
│  │  (Docker imgs) │         │                 │             │
│  └────────────────┘         │  ┌───────────┐  │             │
│                             │  │  Backend  │  │             │
│  ┌────────────────┐         │  │  Task     │──┼─┐           │
│  │ Application    │         │  └───────────┘  │ │           │
│  │ Load Balancer  │────────▶│                 │ │           │
│  │     (ALB)      │         │  ┌───────────┐  │ │           │
│  └────────────────┘         │  │ Frontend  │  │ │           │
│         │                   │  │   Task    │  │ │           │
│         │                   │  └───────────┘  │ │           │
│         │                   └─────────────────┘ │           │
│         │                                       │           │
│  ┌──────▼──────┐                    ┌───────────▼────────┐  │
│  │   Public    │                    │   RDS PostgreSQL   │  │
│  │  Internet   │                    │    (Database)      │  │
│  └─────────────┘                    └────────────────────┘  │
│                                                              │
│  ┌──────────────────┐              ┌────────────────────┐   │
│  │   S3 Bucket      │              │   CloudWatch       │   │
│  │  (Model Files)   │              │  (Logs/Metrics)    │   │
│  └──────────────────┘              └────────────────────┘   │
│                                                              │
│  ┌──────────────────┐                                        │
│  │ Secrets Manager  │                                        │
│  │  (Credentials)   │                                        │
│  └──────────────────┘                                        │
└──────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Local Requirements
- AWS CLI installed and configured
- Docker and Docker Compose installed
- Git installed
- jq (for JSON parsing in scripts)

### AWS Account Setup
1. Create an AWS account (if you don't have one)
2. Enable billing alerts to avoid unexpected charges
3. Create an IAM user with appropriate permissions (see below)

### Required IAM Permissions

Create an IAM user with these permissions:
- AmazonECS_FullAccess
- AmazonEC2ContainerRegistryFullAccess
- AmazonRDSFullAccess
- AmazonS3FullAccess
- CloudWatchLogsFullAccess
- SecretsManagerReadWrite
- IAMFullAccess (for creating service roles)
- ElasticLoadBalancingFullAccess

---

## AWS Services Setup

### Step 1: Configure AWS CLI

```bash
# Install AWS CLI (if not already installed)
# macOS
brew install awscli

# Linux
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Verify installation
aws --version

# Configure AWS CLI with your credentials
aws configure
# Enter:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region (e.g., us-east-1)
# - Default output format: json
```

### Step 2: Set Environment Variables

Create a `.env.aws` file (DO NOT commit this to Git):

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=<your-account-id>

# Project naming
PROJECT_NAME=model-registry
ENVIRONMENT=production

# ECR
ECR_BACKEND_REPO=${PROJECT_NAME}-backend
ECR_FRONTEND_REPO=${PROJECT_NAME}-frontend

# RDS
DB_NAME=modelregistry
DB_USERNAME=admin
DB_PASSWORD=<generate-strong-password>
DB_INSTANCE_CLASS=db.t3.micro  # Free tier eligible
DB_ALLOCATED_STORAGE=20

# S3
S3_BUCKET_NAME=${PROJECT_NAME}-models-${AWS_ACCOUNT_ID}

# ECS
ECS_CLUSTER_NAME=${PROJECT_NAME}-cluster
ECS_BACKEND_SERVICE=${PROJECT_NAME}-backend-service
ECS_FRONTEND_SERVICE=${PROJECT_NAME}-frontend-service

# Admin User
ADMIN_USERNAME=ece30861defaultadminuser
ADMIN_PASSWORD='correcthorsebatterystaple123(!__+@**(A;DROP TABLE packages'

# Security
SECRET_KEY=<generate-random-secret-key>

# Optional: API Keys
ANTHROPIC_API_KEY=<your-key>
GITHUB_TOKEN=<your-token>
```

**Generate secure passwords/keys:**
```bash
# Generate DB password
openssl rand -base64 32

# Generate secret key
openssl rand -hex 32
```

### Step 3: Get Your AWS Account ID

```bash
aws sts get-caller-identity --query Account --output text
```

---

## Docker Configuration for AWS

### Update Backend Dockerfile for Production

The existing Dockerfile is good, but let's create a production-optimized version:

Create `Dockerfile.production`:

```dockerfile
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Production image
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/logs && \
    chown -R appuser:appuser /app

USER appuser

# Update PATH
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Update Frontend Dockerfile for Production

The existing frontend Dockerfile is already production-ready, but we can optimize it:

Create `front-end/model-registry-frontend/Dockerfile.production`:

```dockerfile
# Build stage
FROM node:20-slim as build

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy application code
COPY . .

# Build the application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built assets from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s \
    CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
```

Create `front-end/model-registry-frontend/nginx.conf`:

```nginx
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy (if needed)
    location /api {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

---

## Deployment Steps

### Phase 1: Create AWS Resources

#### 1.1 Create ECR Repositories

```bash
# Source environment variables
source .env.aws

# Create backend repository
aws ecr create-repository \
    --repository-name ${ECR_BACKEND_REPO} \
    --region ${AWS_REGION} \
    --image-scanning-configuration scanOnPush=true

# Create frontend repository
aws ecr create-repository \
    --repository-name ${ECR_FRONTEND_REPO} \
    --region ${AWS_REGION} \
    --image-scanning-configuration scanOnPush=true

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

echo "Backend URI: $BACKEND_REPO_URI"
echo "Frontend URI: $FRONTEND_REPO_URI"
```

#### 1.2 Create S3 Bucket for Model Storage

```bash
# Create S3 bucket
aws s3 mb s3://${S3_BUCKET_NAME} --region ${AWS_REGION}

# Enable versioning
aws s3api put-bucket-versioning \
    --bucket ${S3_BUCKET_NAME} \
    --versioning-configuration Status=Enabled

# Block public access (recommended)
aws s3api put-public-access-block \
    --bucket ${S3_BUCKET_NAME} \
    --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# Enable encryption
aws s3api put-bucket-encryption \
    --bucket ${S3_BUCKET_NAME} \
    --server-side-encryption-configuration \
    '{"Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]}'
```

#### 1.3 Create RDS PostgreSQL Database

First, create a security group for RDS:

```bash
# Get default VPC ID
export VPC_ID=$(aws ec2 describe-vpcs \
    --filters "Name=isDefault,Values=true" \
    --query 'Vpcs[0].VpcId' \
    --output text)

# Create security group for RDS
aws ec2 create-security-group \
    --group-name ${PROJECT_NAME}-rds-sg \
    --description "Security group for RDS PostgreSQL" \
    --vpc-id ${VPC_ID}

export RDS_SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=${PROJECT_NAME}-rds-sg" \
    --query 'SecurityGroups[0].GroupId' \
    --output text)

# Allow PostgreSQL access from ECS tasks (we'll update this later)
aws ec2 authorize-security-group-ingress \
    --group-id ${RDS_SG_ID} \
    --protocol tcp \
    --port 5432 \
    --cidr 0.0.0.0/0  # TEMPORARY - will restrict to ECS security group
```

Create RDS instance:

```bash
# Create RDS instance (Free tier eligible)
aws rds create-db-instance \
    --db-instance-identifier ${PROJECT_NAME}-db \
    --db-instance-class ${DB_INSTANCE_CLASS} \
    --engine postgres \
    --engine-version 15.4 \
    --master-username ${DB_USERNAME} \
    --master-user-password ${DB_PASSWORD} \
    --allocated-storage ${DB_ALLOCATED_STORAGE} \
    --vpc-security-group-ids ${RDS_SG_ID} \
    --publicly-accessible \
    --backup-retention-period 7 \
    --storage-encrypted \
    --enable-cloudwatch-logs-exports '["postgresql"]' \
    --region ${AWS_REGION}

echo "Creating RDS instance... This will take 5-10 minutes"

# Wait for RDS to be available
aws rds wait db-instance-available \
    --db-instance-identifier ${PROJECT_NAME}-db

# Get RDS endpoint
export DB_ENDPOINT=$(aws rds describe-db-instances \
    --db-instance-identifier ${PROJECT_NAME}-db \
    --query 'DBInstances[0].Endpoint.Address' \
    --output text)

echo "RDS Endpoint: $DB_ENDPOINT"

# Store credentials in Secrets Manager
aws secretsmanager create-secret \
    --name ${PROJECT_NAME}/database \
    --description "Database credentials for Model Registry" \
    --secret-string "{\"username\":\"${DB_USERNAME}\",\"password\":\"${DB_PASSWORD}\",\"host\":\"${DB_ENDPOINT}\",\"port\":5432,\"database\":\"${DB_NAME}\"}"
```

#### 1.4 Create ECS Cluster

```bash
# Create ECS cluster
aws ecs create-cluster \
    --cluster-name ${ECS_CLUSTER_NAME} \
    --region ${AWS_REGION} \
    --capacity-providers FARGATE FARGATE_SPOT \
    --default-capacity-provider-strategy \
        capacityProvider=FARGATE,weight=1 \
        capacityProvider=FARGATE_SPOT,weight=1

echo "ECS Cluster created: ${ECS_CLUSTER_NAME}"
```

### Phase 2: Build and Push Docker Images

#### 2.1 Authenticate Docker to ECR

```bash
# Get ECR login password and authenticate
aws ecr get-login-password --region ${AWS_REGION} | \
    docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com
```

#### 2.2 Build and Push Backend Image

```bash
# Build backend image
docker build -t ${ECR_BACKEND_REPO}:latest \
    -f Dockerfile.production .

# Tag for ECR
docker tag ${ECR_BACKEND_REPO}:latest ${BACKEND_REPO_URI}:latest
docker tag ${ECR_BACKEND_REPO}:latest ${BACKEND_REPO_URI}:v1.0.0

# Push to ECR
docker push ${BACKEND_REPO_URI}:latest
docker push ${BACKEND_REPO_URI}:v1.0.0
```

#### 2.3 Build and Push Frontend Image

```bash
# Build frontend image
cd front-end/model-registry-frontend
docker build -t ${ECR_FRONTEND_REPO}:latest \
    -f Dockerfile.production .

# Tag for ECR
docker tag ${ECR_FRONTEND_REPO}:latest ${FRONTEND_REPO_URI}:latest
docker tag ${ECR_FRONTEND_REPO}:latest ${FRONTEND_REPO_URI}:v1.0.0

# Push to ECR
docker push ${FRONTEND_REPO_URI}:latest
docker push ${FRONTEND_REPO_URI}:v1.0.0

cd ../..
```

### Phase 3: Create ECS Task Definitions and Services

#### 3.1 Create IAM Roles for ECS

Create task execution role:

```bash
# Create trust policy
cat > ecs-task-trust-policy.json <<EOF
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
aws iam create-role \
    --role-name ${PROJECT_NAME}-ecs-execution-role \
    --assume-role-policy-document file://ecs-task-trust-policy.json

# Attach policies
aws iam attach-role-policy \
    --role-name ${PROJECT_NAME}-ecs-execution-role \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

aws iam attach-role-policy \
    --role-name ${PROJECT_NAME}-ecs-execution-role \
    --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite

# Create task role (for app permissions)
aws iam create-role \
    --role-name ${PROJECT_NAME}-ecs-task-role \
    --assume-role-policy-document file://ecs-task-trust-policy.json

# Create and attach S3 and CloudWatch policies
cat > ecs-task-policy.json <<EOF
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
    --policy-document file://ecs-task-policy.json

export EXECUTION_ROLE_ARN=$(aws iam get-role \
    --role-name ${PROJECT_NAME}-ecs-execution-role \
    --query 'Role.Arn' \
    --output text)

export TASK_ROLE_ARN=$(aws iam get-role \
    --role-name ${PROJECT_NAME}-ecs-task-role \
    --query 'Role.Arn' \
    --output text)
```

#### 3.2 Create CloudWatch Log Groups

```bash
aws logs create-log-group --log-group-name /ecs/${PROJECT_NAME}-backend
aws logs create-log-group --log-group-name /ecs/${PROJECT_NAME}-frontend

# Set retention (7 days for cost savings)
aws logs put-retention-policy \
    --log-group-name /ecs/${PROJECT_NAME}-backend \
    --retention-in-days 7

aws logs put-retention-policy \
    --log-group-name /ecs/${PROJECT_NAME}-frontend \
    --retention-in-days 7
```

#### 3.3 Create Backend Task Definition

```bash
cat > backend-task-definition.json <<EOF
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
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "essential": true,
      "environment": [
        {
          "name": "PYTHONPATH",
          "value": "/app"
        },
        {
          "name": "DATABASE_URL",
          "value": "postgresql://${DB_USERNAME}:${DB_PASSWORD}@${DB_ENDPOINT}:5432/${DB_NAME}"
        },
        {
          "name": "S3_BUCKET_NAME",
          "value": "${S3_BUCKET_NAME}"
        },
        {
          "name": "AWS_REGION",
          "value": "${AWS_REGION}"
        },
        {
          "name": "ENVIRONMENT",
          "value": "aws"
        },
        {
          "name": "LOG_LEVEL",
          "value": "1"
        },
        {
          "name": "ADMIN_USERNAME",
          "value": "${ADMIN_USERNAME}"
        },
        {
          "name": "ADMIN_PASSWORD",
          "value": "${ADMIN_PASSWORD}"
        },
        {
          "name": "SECRET_KEY",
          "value": "${SECRET_KEY}"
        }
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
    }
  ]
}
EOF

# Register task definition
aws ecs register-task-definition \
    --cli-input-json file://backend-task-definition.json
```

#### 3.4 Create Load Balancer and Target Group

```bash
# Create security group for ALB
aws ec2 create-security-group \
    --group-name ${PROJECT_NAME}-alb-sg \
    --description "Security group for Application Load Balancer" \
    --vpc-id ${VPC_ID}

export ALB_SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=${PROJECT_NAME}-alb-sg" \
    --query 'SecurityGroups[0].GroupId' \
    --output text)

# Allow HTTP traffic
aws ec2 authorize-security-group-ingress \
    --group-id ${ALB_SG_ID} \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0

# Create security group for ECS tasks
aws ec2 create-security-group \
    --group-name ${PROJECT_NAME}-ecs-sg \
    --description "Security group for ECS tasks" \
    --vpc-id ${VPC_ID}

export ECS_SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=${PROJECT_NAME}-ecs-sg" \
    --query 'SecurityGroups[0].GroupId' \
    --output text)

# Allow traffic from ALB to ECS tasks
aws ec2 authorize-security-group-ingress \
    --group-id ${ECS_SG_ID} \
    --protocol tcp \
    --port 8000 \
    --source-group ${ALB_SG_ID}

# Get subnet IDs (use at least 2 for ALB)
export SUBNET_IDS=$(aws ec2 describe-subnets \
    --filters "Name=vpc-id,Values=${VPC_ID}" \
    --query 'Subnets[0:2].SubnetId' \
    --output text | tr '\t' ' ')

# Create Application Load Balancer
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

echo "Load Balancer DNS: $ALB_DNS"

# Create target group
aws elbv2 create-target-group \
    --name ${PROJECT_NAME}-backend-tg \
    --protocol HTTP \
    --port 8000 \
    --vpc-id ${VPC_ID} \
    --target-type ip \
    --health-check-path /health \
    --health-check-interval-seconds 30 \
    --health-check-timeout-seconds 5 \
    --healthy-threshold-count 2 \
    --unhealthy-threshold-count 3

export TG_ARN=$(aws elbv2 describe-target-groups \
    --names ${PROJECT_NAME}-backend-tg \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text)

# Create listener
aws elbv2 create-listener \
    --load-balancer-arn ${ALB_ARN} \
    --protocol HTTP \
    --port 80 \
    --default-actions Type=forward,TargetGroupArn=${TG_ARN}
```

#### 3.5 Create ECS Service

```bash
cat > backend-service.json <<EOF
{
  "cluster": "${ECS_CLUSTER_NAME}",
  "serviceName": "${ECS_BACKEND_SERVICE}",
  "taskDefinition": "${PROJECT_NAME}-backend",
  "loadBalancers": [
    {
      "targetGroupArn": "${TG_ARN}",
      "containerName": "backend",
      "containerPort": 8000
    }
  ],
  "desiredCount": 1,
  "launchType": "FARGATE",
  "networkConfiguration": {
    "awsvpcConfiguration": {
      "subnets": $(echo ${SUBNET_IDS} | jq -R 'split(" ")'),
      "securityGroups": ["${ECS_SG_ID}"],
      "assignPublicIp": "ENABLED"
    }
  },
  "healthCheckGracePeriodSeconds": 60
}
EOF

# Create service
aws ecs create-service --cli-input-json file://backend-service.json

echo "Service created. Waiting for tasks to start..."
aws ecs wait services-stable --cluster ${ECS_CLUSTER_NAME} --services ${ECS_BACKEND_SERVICE}

echo "Deployment complete!"
echo "Your API is available at: http://${ALB_DNS}"
```

---

## Testing the Deployment

```bash
# Test health endpoint
curl http://${ALB_DNS}/health

# Test authentication
curl -X POST http://${ALB_DNS}/authenticate \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"${ADMIN_USERNAME}\",\"password\":\"${ADMIN_PASSWORD}\"}"

# Get API documentation
curl http://${ALB_DNS}/docs
```

---

## CI/CD with GitHub Actions

This section will be covered in a separate document: `GITHUB_ACTIONS_AWS_CICD.md`

---

## Monitoring and Logging

### View CloudWatch Logs

```bash
# Stream backend logs
aws logs tail /ecs/${PROJECT_NAME}-backend --follow

# Query for errors in last hour
aws logs filter-log-events \
    --log-group-name /ecs/${PROJECT_NAME}-backend \
    --start-time $(date -u -d '1 hour ago' +%s)000 \
    --filter-pattern "ERROR"
```

### Set Up CloudWatch Alarms

```bash
# CPU utilization alarm
aws cloudwatch put-metric-alarm \
    --alarm-name ${PROJECT_NAME}-high-cpu \
    --alarm-description "Alert when CPU exceeds 80%" \
    --metric-name CPUUtilization \
    --namespace AWS/ECS \
    --statistic Average \
    --period 300 \
    --threshold 80 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 2

# Error rate alarm
aws cloudwatch put-metric-alarm \
    --alarm-name ${PROJECT_NAME}-error-rate \
    --alarm-description "Alert on high error rate" \
    --metric-name 4XXError \
    --namespace AWS/ApplicationELB \
    --statistic Sum \
    --period 300 \
    --threshold 10 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 1
```

---

## Cost Management

### Free Tier Limits

- **ECS Fargate**: No free tier, ~$0.04/hour per task
- **RDS db.t3.micro**: 750 hours/month free
- **S3**: 5GB storage, 20,000 GET, 2,000 PUT requests/month
- **ECR**: 500MB storage/month
- **CloudWatch**: 10 custom metrics, 5GB logs

### Cost Estimation (Monthly)

- ECS Fargate (1 task, 24/7): ~$30
- RDS db.t3.micro (free tier): $0
- ALB: ~$16
- S3 (10GB storage): ~$0.23
- CloudWatch Logs (5GB): $0
- Data transfer: Variable

**Estimated Total**: ~$50/month (after free tier)

### Cost Optimization Tips

1. **Use Fargate Spot** for non-critical tasks (70% cheaper)
2. **Stop/Start RDS** during non-working hours
3. **Use S3 Lifecycle Policies** to move old data to cheaper storage
4. **Set up AWS Budgets** to get alerts

```bash
# Set up budget alert
aws budgets create-budget \
    --account-id ${AWS_ACCOUNT_ID} \
    --budget file://budget.json \
    --notifications-with-subscribers file://budget-notifications.json
```

---

## Cleanup / Teardown

To avoid ongoing costs, delete resources when done:

```bash
# Delete ECS service
aws ecs update-service \
    --cluster ${ECS_CLUSTER_NAME} \
    --service ${ECS_BACKEND_SERVICE} \
    --desired-count 0

aws ecs delete-service \
    --cluster ${ECS_CLUSTER_NAME} \
    --service ${ECS_BACKEND_SERVICE} \
    --force

# Delete ECS cluster
aws ecs delete-cluster --cluster ${ECS_CLUSTER_NAME}

# Delete load balancer
aws elbv2 delete-load-balancer --load-balancer-arn ${ALB_ARN}
aws elbv2 delete-target-group --target-group-arn ${TG_ARN}

# Delete RDS instance
aws rds delete-db-instance \
    --db-instance-identifier ${PROJECT_NAME}-db \
    --skip-final-snapshot

# Empty and delete S3 bucket
aws s3 rm s3://${S3_BUCKET_NAME} --recursive
aws s3 rb s3://${S3_BUCKET_NAME}

# Delete ECR repositories
aws ecr delete-repository \
    --repository-name ${ECR_BACKEND_REPO} \
    --force

aws ecr delete-repository \
    --repository-name ${ECR_FRONTEND_REPO} \
    --force

# Delete security groups (wait for resources to be deleted first)
aws ec2 delete-security-group --group-id ${ECS_SG_ID}
aws ec2 delete-security-group --group-id ${ALB_SG_ID}
aws ec2 delete-security-group --group-id ${RDS_SG_ID}

# Delete CloudWatch log groups
aws logs delete-log-group --log-group-name /ecs/${PROJECT_NAME}-backend
aws logs delete-log-group --log-group-name /ecs/${PROJECT_NAME}-frontend

# Delete IAM roles
aws iam delete-role-policy \
    --role-name ${PROJECT_NAME}-ecs-task-role \
    --policy-name ${PROJECT_NAME}-task-permissions

aws iam detach-role-policy \
    --role-name ${PROJECT_NAME}-ecs-execution-role \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

aws iam delete-role --role-name ${PROJECT_NAME}-ecs-execution-role
aws iam delete-role --role-name ${PROJECT_NAME}-ecs-task-role
```

---

## Troubleshooting

### Common Issues

**Issue: ECS tasks fail to start**
```bash
# Check task logs
aws ecs describe-tasks \
    --cluster ${ECS_CLUSTER_NAME} \
    --tasks $(aws ecs list-tasks --cluster ${ECS_CLUSTER_NAME} --query 'taskArns[0]' --output text)

# View stopped task reason
aws ecs describe-tasks \
    --cluster ${ECS_CLUSTER_NAME} \
    --tasks <task-arn> \
    --query 'tasks[0].stoppedReason'
```

**Issue: Can't connect to RDS**
```bash
# Verify security group allows connections
aws ec2 describe-security-groups --group-ids ${RDS_SG_ID}

# Test connection from local machine
psql -h ${DB_ENDPOINT} -U ${DB_USERNAME} -d ${DB_NAME}
```

**Issue: High costs**
```bash
# Check current costs
aws ce get-cost-and-usage \
    --time-period Start=2025-12-01,End=2025-12-02 \
    --granularity DAILY \
    --metrics BlendedCost
```

---

## Next Steps

1. Set up CI/CD with GitHub Actions (see `GITHUB_ACTIONS_AWS_CICD.md`)
2. Configure custom domain with Route 53
3. Add HTTPS with ACM (AWS Certificate Manager)
4. Implement auto-scaling based on load
5. Set up database backups and disaster recovery

---

## Support

For issues or questions:
- Check CloudWatch Logs for application errors
- Review ECS task events in the AWS Console
- Consult AWS documentation: https://docs.aws.amazon.com/

**Important**: Always monitor your AWS costs and set up billing alerts!
