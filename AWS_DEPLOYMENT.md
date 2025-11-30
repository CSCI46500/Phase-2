# AWS Deployment Guide

Complete guide for deploying the Model Registry to AWS using ECS, S3, RDS, and AWS Batch.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         AWS Cloud                                │
│                                                                   │
│  ┌─────────────┐                                                │
│  │ CloudFront  │ ◄── Frontend (Static SPA)                      │
│  └──────┬──────┘                                                │
│         │                                                         │
│  ┌──────▼──────┐                                                │
│  │ S3 (Frontend)│                                                │
│  └─────────────┘                                                │
│                                                                   │
│  ┌─────────────┐      ┌──────────────┐                          │
│  │     ALB     │ ◄──► │   ECS/Fargate│ ◄── Backend API          │
│  └─────────────┘      │   (Backend)  │                          │
│                        └──────┬───────┘                          │
│                               │                                   │
│  ┌─────────────┐      ┌──────▼───────┐                          │
│  │     RDS     │ ◄──► │     VPC      │                          │
│  │ (PostgreSQL)│      │   (Private)  │                          │
│  └─────────────┘      └──────┬───────┘                          │
│                               │                                   │
│  ┌─────────────┐      ┌──────▼───────┐                          │
│  │ S3 (Packages)│◄──► │  AWS Batch   │ ◄── Autograder/Scorer   │
│  └─────────────┘      │  (Fargate)   │                          │
│                        └──────────────┘                          │
│                                                                   │
│  ┌─────────────┐                                                │
│  │ CloudWatch  │ ◄── Logs & Metrics                             │
│  └─────────────┘                                                │
│                                                                   │
│  ┌─────────────┐                                                │
│  │     ECR     │ ◄── Docker Images                              │
│  └─────────────┘                                                │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

### Required Tools
- AWS CLI v2
- Terraform >= 1.0
- Docker
- Node.js 20+
- Python 3.11+

### AWS Account Setup
1. AWS account with appropriate permissions
2. AWS CLI configured with credentials
3. (Optional) Domain name in Route 53

## Initial Setup

### 1. Configure AWS Credentials

```bash
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Default region: us-east-1
```

### 2. Create Terraform Backend (Optional but Recommended)

```bash
# Create S3 bucket for Terraform state
aws s3api create-bucket \
  --bucket model-registry-terraform-state \
  --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket model-registry-terraform-state \
  --versioning-configuration Status=Enabled

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name terraform-state-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

Then uncomment the backend configuration in `terraform/main.tf`.

### 3. Set Up Environment Variables

Create a `.env.aws` file:

```bash
# AWS Configuration
export AWS_REGION=us-east-1
export ENVIRONMENT=prod
export PROJECT_NAME=model-registry

# Database Credentials (CHANGE THESE!)
export TF_VAR_db_username=admin
export TF_VAR_db_password="YourSecurePassword123!"

# Load environment
source .env.aws
```

## Deployment Steps

### Step 1: Deploy Infrastructure with Terraform

```bash
cd terraform

# Initialize Terraform
terraform init

# Review the deployment plan
terraform plan

# Deploy infrastructure
terraform apply

# Save outputs
terraform output > ../terraform-outputs.txt
```

This will create:
- VPC with public/private subnets
- RDS PostgreSQL database
- ECS cluster and task definitions
- Application Load Balancer
- S3 buckets (packages, frontend, logs)
- ECR repositories
- AWS Batch compute environment
- CloudFront distribution
- IAM roles and security groups
- CloudWatch dashboards and alarms

**Deployment time:** ~15-20 minutes

### Step 2: Build and Push Docker Images

```bash
# Build and push both backend and autograder
./scripts/aws-deploy/build-and-push.sh all

# Or build individually
./scripts/aws-deploy/build-and-push.sh backend
./scripts/aws-deploy/build-and-push.sh autograder
```

### Step 3: Initialize Database

The database will be automatically migrated when the ECS service starts. If you need to run migrations manually:

```bash
# Get RDS endpoint from Terraform outputs
RDS_ENDPOINT=$(terraform output -raw rds_endpoint)

# Run migrations (example using psql)
DATABASE_URL="postgresql://$TF_VAR_db_username:$TF_VAR_db_password@$RDS_ENDPOINT/model_registry"

# You can exec into a running ECS task to run migrations
aws ecs execute-command \
  --cluster model-registry-prod-cluster \
  --task <TASK_ID> \
  --container backend \
  --interactive \
  --command "/bin/bash"

# Then inside the container:
# python -m src.cli.init_db
```

### Step 4: Deploy Frontend

```bash
./scripts/aws-deploy/deploy-frontend.sh
```

### Step 5: Verify Deployment

```bash
# Get the API URL
API_URL=$(terraform output -raw alb_dns_name)
curl http://$API_URL/health

# Get the Frontend URL
FRONTEND_URL=$(terraform output -raw frontend_url)
echo "Frontend available at: $FRONTEND_URL"
```

## CI/CD with GitHub Actions

### Setup

1. Create an OIDC provider in AWS for GitHub Actions:

```bash
# Create OIDC provider (one-time setup)
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

2. Create an IAM role for GitHub Actions with necessary permissions

3. Add GitHub Secrets:
   - `AWS_ROLE_TO_ASSUME`: ARN of the IAM role created above

4. Push to `aws-deployment` branch to trigger deployment

## Configuration

### Environment Variables

The backend application uses these environment variables (set in ECS task definition):

```bash
DATABASE_URL          # PostgreSQL connection string
S3_BUCKET_NAME        # S3 bucket for packages
AWS_REGION            # AWS region
ENVIRONMENT           # Environment name (prod/staging/dev)
```

### Scaling Configuration

**ECS Auto-scaling:**
- Min: 2 tasks
- Max: 10 tasks
- Scale up: CPU > 70% or Memory > 80%
- Scale down: CPU < 50% and Memory < 60%

**AWS Batch:**
- Max vCPUs: 16
- Job timeout: 15 minutes
- Retry attempts: 3

### Cost Optimization

**Current configuration (approximate monthly costs):**
- ECS Fargate (2 tasks): ~$50-70
- RDS db.t3.micro: ~$15-20
- ALB: ~$20-25
- S3 + CloudFront: ~$5-10 (depends on usage)
- NAT Gateway: ~$32 (per AZ)
- **Total: ~$150-200/month**

**To reduce costs:**
- Use single NAT Gateway (modify `terraform/vpc.tf`)
- Use smaller RDS instance (db.t3.micro is smallest)
- Reduce ECS min tasks to 1 (not recommended for production)
- Use S3 Intelligent-Tiering

## Monitoring and Observability

### CloudWatch Dashboard

Access the CloudWatch dashboard:
```bash
terraform output cloudwatch_dashboard_url
```

### View Logs

```bash
# Backend logs
aws logs tail /aws/ecs/model-registry-prod --follow

# Autograder logs
aws logs tail /aws/batch/model-registry-prod --follow
```

### Alarms

Configured alarms:
- ECS CPU/Memory high
- RDS CPU/Storage/Connections
- ALB 5xx errors and response time
- Batch job failures
- CloudFront error rate

## Security

### Network Security
- Backend runs in private subnets
- Only ALB exposed to internet
- Security groups restrict traffic between services
- VPC endpoints for S3 (no NAT Gateway charges for S3 traffic)

### Data Security
- RDS encryption at rest
- S3 encryption (AES256)
- HTTPS enforced on CloudFront
- Secrets stored in environment variables (consider AWS Secrets Manager for production)

### Autograder Isolation
- Runs in isolated Fargate containers
- Resource limits (CPU, memory, time)
- Non-root user
- VPC egress controls
- No persistent storage

## Troubleshooting

### ECS Service Not Starting

```bash
# Check service events
aws ecs describe-services \
  --cluster model-registry-prod-cluster \
  --services model-registry-prod-backend-service \
  --query 'services[0].events[0:5]'

# Check task logs
aws logs tail /aws/ecs/model-registry-prod --follow
```

### Database Connection Issues

```bash
# Verify security group allows ECS -> RDS
# Check RDS endpoint is correct
# Verify credentials
```

### Frontend Not Loading

```bash
# Check S3 bucket contents
aws s3 ls s3://model-registry-prod-frontend-<account-id>/

# Check CloudFront distribution status
aws cloudfront list-distributions
```

## Updating the Deployment

### Update Infrastructure

```bash
cd terraform
terraform plan
terraform apply
```

### Update Backend Code

```bash
# Build and push new image
./scripts/aws-deploy/build-and-push.sh backend v1.2.0

# Force new deployment
aws ecs update-service \
  --cluster model-registry-prod-cluster \
  --service model-registry-prod-backend-service \
  --force-new-deployment
```

### Update Frontend

```bash
./scripts/aws-deploy/deploy-frontend.sh
```

## Cleanup

To destroy all AWS resources:

```bash
cd terraform

# This will delete EVERYTHING
terraform destroy

# Manually delete ECR images first if needed
aws ecr list-images --repository-name model-registry-prod-backend
aws ecr batch-delete-image --repository-name model-registry-prod-backend --image-ids imageTag=latest
```

## Production Checklist

Before going to production:

- [ ] Enable RDS Multi-AZ
- [ ] Configure custom domain with Route 53
- [ ] Set up ACM certificates for HTTPS
- [ ] Enable AWS Secrets Manager for credentials
- [ ] Set up CloudWatch alarms with SNS notifications
- [ ] Configure backup strategy
- [ ] Enable AWS WAF on ALB
- [ ] Set up VPC Flow Logs
- [ ] Review and tighten IAM policies
- [ ] Enable deletion protection on critical resources
- [ ] Set up disaster recovery plan
- [ ] Configure log retention policies
- [ ] Enable AWS Config for compliance
- [ ] Set up cost allocation tags
- [ ] Create runbooks for common operations

## Support

For issues:
1. Check CloudWatch Logs
2. Review Terraform outputs
3. Check AWS service health dashboard
4. Review security group rules
5. Verify IAM permissions

## Additional Resources

- [AWS ECS Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/)
- [AWS Batch Best Practices](https://docs.aws.amazon.com/batch/latest/userguide/best-practices.html)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
