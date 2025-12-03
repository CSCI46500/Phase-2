# AWS Deployment for Model Registry

Complete guide for deploying the Model Registry application to Amazon Web Services using Docker containers.

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Deployment Process](#deployment-process)
5. [CI/CD Setup](#cicd-setup)
6. [Monitoring](#monitoring)
7. [Cost Management](#cost-management)
8. [Troubleshooting](#troubleshooting)

## 🚀 Quick Start

**For those who want to deploy immediately:**

```bash
# 1. Configure AWS CLI
aws configure

# 2. Set up environment
cp .env.aws.template .env.aws
# Edit .env.aws with your values (see Step 3 in AWS_QUICK_START.md)

# 3. Deploy everything
./scripts/deploy-to-aws.sh

# 4. Test deployment
export API_URL=http://your-alb-dns-from-output
curl $API_URL/health
```

**For detailed instructions:** See `docs/AWS_QUICK_START.md`

## 🏗️ Architecture

### AWS Services Used

Our deployment uses **7 AWS services** (exceeding the 2+ requirement):

1. **Amazon ECR** - Docker container registry
2. **Amazon ECS** - Container orchestration (Fargate)
3. **Amazon RDS** - PostgreSQL database
4. **Amazon S3** - Object storage for models
5. **Application Load Balancer** - Traffic distribution
6. **Amazon CloudWatch** - Logging and monitoring
7. **AWS Secrets Manager** - Secure credential storage

### Architecture Diagram

```
Internet
   │
   ▼
┌─────────────────┐
│ Application LB  │ (Port 80, HTTP)
└────────┬────────┘
         │
         ▼
   ┌─────────┐
   │   ECS   │
   │ Cluster │
   └────┬────┘
        │
   ┌────┴─────────────┐
   │                  │
   ▼                  ▼
Backend Task      Frontend Task
(Fargate)         (Fargate)
   │
   │
   ├──────► RDS PostgreSQL
   │
   └──────► S3 Bucket
```

### Why These Components?

| Component | Justification |
|-----------|--------------|
| **ECR** | Secure, private Docker registry integrated with ECS |
| **ECS Fargate** | Serverless containers - no EC2 management needed |
| **RDS** | Managed PostgreSQL with automatic backups, patches |
| **S3** | Scalable object storage for multi-GB model files |
| **ALB** | Health checks, auto-scaling, SSL termination |
| **CloudWatch** | Centralized logging required by spec |
| **Secrets Manager** | Secure credential storage (best practice) |

## 📦 Prerequisites

### Local Tools Required

- **AWS CLI** v2.x - [Install guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- **Docker** v20.x+ - [Install guide](https://docs.docker.com/get-docker/)
- **jq** - JSON processor - `brew install jq` or `apt install jq`
- **Git** - Version control

### AWS Account Setup

1. **Create AWS Account**: https://aws.amazon.com/free/
2. **Create IAM User** with these policies:
   - AmazonECS_FullAccess
   - AmazonEC2ContainerRegistryFullAccess
   - AmazonRDSFullAccess
   - AmazonS3FullAccess
   - CloudWatchLogsFullAccess
   - ElasticLoadBalancingFullAccess
   - IAMFullAccess

3. **Generate Access Keys**:
   - IAM Console → Users → Your User → Security Credentials
   - Create Access Key → CLI
   - Save Access Key ID and Secret Access Key

4. **Configure AWS CLI**:
   ```bash
   aws configure
   # AWS Access Key ID: <your-key-id>
   # AWS Secret Access Key: <your-secret-key>
   # Default region name: us-east-1
   # Default output format: json
   ```

5. **Verify Configuration**:
   ```bash
   aws sts get-caller-identity
   # Should show your account ID, user ARN
   ```

## 🛠️ Deployment Process

### Option 1: Automated Deployment (Recommended)

```bash
# 1. Copy and configure environment
cp .env.aws.template .env.aws

# 2. Edit .env.aws - update these values:
#    - AWS_REGION (e.g., us-east-1)
#    - S3_BUCKET_NAME (must include your account ID for uniqueness)
#    - DB_PASSWORD (generate with: openssl rand -base64 32)
#    - SECRET_KEY (generate with: openssl rand -hex 32)

# 3. Run deployment script
./scripts/deploy-to-aws.sh

# This will take 20-30 minutes on first run
# The script is idempotent - safe to run multiple times
```

### Option 2: Manual Deployment

Follow the step-by-step guide in `docs/AWS_DEPLOYMENT_GUIDE.md`

### What Gets Deployed?

```
AWS Resources Created:
✅ ECR Repositories (backend + frontend)
✅ S3 Bucket (versioned, encrypted)
✅ RDS PostgreSQL (db.t3.micro, 20GB)
✅ ECS Cluster (Fargate)
✅ Application Load Balancer
✅ Security Groups (ALB, ECS, RDS)
✅ IAM Roles (execution + task)
✅ CloudWatch Log Groups
✅ Target Groups and Listeners
```

### Deployment Output

After successful deployment:

```
==========================================
  AWS Deployment Summary
==========================================

API Endpoint: http://model-registry-alb-1234567890.us-east-1.elb.amazonaws.com
API Docs: http://model-registry-alb-1234567890.us-east-1.elb.amazonaws.com/docs
Health Check: http://model-registry-alb-1234567890.us-east-1.elb.amazonaws.com/health

AWS Resources Created:
  - ECR Repositories: model-registry-backend, model-registry-frontend
  - S3 Bucket: model-registry-models-123456789012
  - RDS Instance: model-registry-db
  - ECS Cluster: model-registry-cluster
  - ECS Service: model-registry-backend-service
  - Load Balancer: model-registry-alb
==========================================
```

## 🔄 CI/CD Setup

### GitHub Actions Workflow

Our CI/CD pipeline (`.github/workflows/deploy-aws.yml`) automates:

**On Pull Request:**
- ✅ Run linting (flake8)
- ✅ Run security scan (bandit)
- ✅ Run tests with coverage (pytest)
- ✅ Upload coverage reports

**On Push to Main:**
- 🏗️ Build Docker images
- 📦 Push images to ECR
- 🚀 Deploy to ECS
- ⏳ Wait for service stability
- 🧪 Run smoke tests
- 📊 Generate deployment report

### Setup Instructions

1. **Add GitHub Secrets**:
   - Go to: Repository → Settings → Secrets and Variables → Actions
   - Add these secrets:
     - `AWS_ACCESS_KEY_ID`: Your AWS access key
     - `AWS_SECRET_ACCESS_KEY`: Your AWS secret key

2. **Configure Workflow** (already done):
   - File: `.github/workflows/deploy-aws.yml`
   - Triggers: push to main, pull requests

3. **Test CI/CD**:
   ```bash
   git add .
   git commit -m "Test CI/CD pipeline"
   git push origin main
   ```

4. **Monitor Deployment**:
   - GitHub → Actions tab
   - View workflow run progress
   - Check deployment logs

### Workflow Features

- **Parallel Testing**: Runs multiple test suites concurrently
- **Security First**: Blocks merge if security issues found
- **Zero-Downtime Deployment**: ECS handles rolling updates
- **Automatic Rollback**: Failed health checks revert deployment
- **Deployment Reports**: Generates summary in PR comments

## 📊 Monitoring

### CloudWatch Logs

**View logs in real-time:**
```bash
# Stream backend logs
aws logs tail /ecs/model-registry-backend --follow

# View logs from last hour
aws logs tail /ecs/model-registry-backend --since 1h

# Filter for errors
aws logs filter-log-events \
  --log-group-name /ecs/model-registry-backend \
  --filter-pattern "ERROR"
```

### Health Endpoint

```bash
# Basic health check
curl http://your-alb-dns/health

# Detailed metrics
curl "http://your-alb-dns/health?detailed=true" | jq .
```

**Response includes:**
- Request counts (total, successful, failed)
- Error rate percentage
- Response times (avg, p95, p99)
- System resources (CPU, memory)
- Top endpoints by usage

### CloudWatch Dashboard

**Access via AWS Console:**
1. CloudWatch → Dashboards
2. View metrics for:
   - ECS task CPU/memory utilization
   - RDS database connections
   - ALB request count and latency
   - S3 bucket size and requests

**Create Custom Alarms:**
```bash
# High CPU alarm
aws cloudwatch put-metric-alarm \
  --alarm-name model-registry-high-cpu \
  --alarm-description "Alert when CPU exceeds 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2
```

### ECS Service Status

```bash
# Check service health
aws ecs describe-services \
  --cluster model-registry-cluster \
  --services model-registry-backend-service

# List running tasks
aws ecs list-tasks \
  --cluster model-registry-cluster

# Describe specific task
aws ecs describe-tasks \
  --cluster model-registry-cluster \
  --tasks <task-arn>
```

## 💰 Cost Management

### Free Tier Limits (First 12 Months)

- ✅ **RDS db.t3.micro**: 750 hours/month (can run 24/7)
- ✅ **S3**: 5GB storage, 20,000 GET, 2,000 PUT requests
- ✅ **ECR**: 500MB storage
- ✅ **CloudWatch**: 10 custom metrics, 5GB logs
- ❌ **ECS Fargate**: No free tier
- ❌ **Application Load Balancer**: No free tier

### Monthly Cost Estimate

| Service | Configuration | Cost |
|---------|--------------|------|
| ECS Fargate | 1 task (0.5 vCPU, 1GB RAM) 24/7 | ~$15 |
| RDS | db.t3.micro (free tier) | $0 |
| Application Load Balancer | Standard | ~$16 |
| S3 | 10GB storage + requests | ~$0.50 |
| Data Transfer | Moderate usage | ~$2 |
| **Total** | | **~$33-35/month** |

### Cost Optimization Strategies

**1. Use Fargate Spot (70% cheaper)**
```bash
# Update capacity provider in task definition
# FARGATE_SPOT instead of FARGATE
# Caveat: Tasks can be interrupted
```

**2. Stop Non-Production Resources**
```bash
# Stop RDS when not in use (dev/test only)
aws rds stop-db-instance --db-instance-identifier model-registry-db

# Scale ECS to 0 tasks
aws ecs update-service \
  --cluster model-registry-cluster \
  --service model-registry-backend-service \
  --desired-count 0
```

**3. Enable Auto-Scaling**
- Scale down during off-hours (nights, weekends)
- Scale based on CPU/memory metrics
- Example: 1 task during low traffic, 4 during peak

**4. Use S3 Lifecycle Policies**
```bash
# Move old models to cheaper storage classes
# Standard → Infrequent Access → Glacier
```

**5. Set Up Budget Alerts**
```bash
# Get email when costs exceed $10/month
aws budgets create-budget \
  --account-id $(aws sts get-caller-identity --query Account --output text) \
  --budget file://budget.json \
  --notifications-with-subscribers file://budget-notifications.json
```

### Monitor Costs

```bash
# View current month costs
aws ce get-cost-and-usage \
  --time-period Start=2025-12-01,End=2025-12-31 \
  --granularity MONTHLY \
  --metrics BlendedCost

# Break down by service
aws ce get-cost-and-usage \
  --time-period Start=2025-12-01,End=2025-12-31 \
  --granularity DAILY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE
```

**Or use AWS Cost Explorer:**
- AWS Console → Billing → Cost Explorer
- View charts by service, region, tag
- Set up cost anomaly detection

## 🔧 Troubleshooting

### Common Issues

#### Issue: Deployment script fails with "Access Denied"

**Solution:**
```bash
# Verify AWS credentials
aws sts get-caller-identity

# Check IAM permissions
aws iam get-user
aws iam list-attached-user-policies --user-name <your-username>
```

#### Issue: ECS tasks fail to start

**Check task logs:**
```bash
TASK_ARN=$(aws ecs list-tasks \
  --cluster model-registry-cluster \
  --query 'taskArns[0]' --output text)

aws ecs describe-tasks \
  --cluster model-registry-cluster \
  --tasks $TASK_ARN \
  --query 'tasks[0].stoppedReason'
```

**Common causes:**
- ❌ Database connection failed → Check RDS security group
- ❌ Image pull failed → Verify ECR repository has images
- ❌ Out of memory → Increase task memory limit
- ❌ Environment variables missing → Check task definition

#### Issue: Load balancer returns 503

**Check target health:**
```bash
TG_ARN=$(aws elbv2 describe-target-groups \
  --names model-registry-backend-tg \
  --query 'TargetGroups[0].TargetGroupArn' --output text)

aws elbv2 describe-target-health --target-group-arn $TG_ARN
```

**If unhealthy:**
- Check ECS tasks are running
- Verify health check endpoint works: `/health`
- Check security groups allow ALB → ECS on port 8000

#### Issue: Database connection errors

**Test RDS connectivity:**
```bash
# Get RDS endpoint
DB_ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier model-registry-db \
  --query 'DBInstances[0].Endpoint.Address' --output text)

# Test connection (requires psql installed)
psql -h $DB_ENDPOINT -U admin -d modelregistry
```

**Fix security group:**
```bash
# Ensure RDS security group allows port 5432 from ECS security group
aws ec2 authorize-security-group-ingress \
  --group-id <rds-sg-id> \
  --protocol tcp \
  --port 5432 \
  --source-group <ecs-sg-id>
```

#### Issue: High costs / unexpected charges

**Identify cost drivers:**
```bash
# Check running resources
aws ecs list-tasks --cluster model-registry-cluster
aws rds describe-db-instances --query 'DBInstances[].DBInstanceIdentifier'
aws elbv2 describe-load-balancers --query 'LoadBalancers[].LoadBalancerName'

# View detailed costs
aws ce get-cost-and-usage \
  --time-period Start=2025-12-01,End=2025-12-02 \
  --granularity DAILY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE
```

**Stop non-critical resources:**
```bash
# Scale ECS to 0
aws ecs update-service --cluster model-registry-cluster \
  --service model-registry-backend-service --desired-count 0

# Stop RDS (can restart later)
aws rds stop-db-instance --db-instance-identifier model-registry-db
```

### Debugging Commands

```bash
# View all ECS tasks
aws ecs list-tasks --cluster model-registry-cluster

# Get task details
aws ecs describe-tasks --cluster model-registry-cluster --tasks <task-arn>

# View CloudWatch logs
aws logs tail /ecs/model-registry-backend --follow

# Check load balancer health
aws elbv2 describe-target-health --target-group-arn <tg-arn>

# Test API endpoint
curl -v http://<alb-dns>/health

# Check RDS status
aws rds describe-db-instances --db-instance-identifier model-registry-db

# List S3 objects
aws s3 ls s3://model-registry-models-<account-id>/
```

## 🗑️ Cleanup

**To delete all AWS resources and stop charges:**

See detailed cleanup instructions in `docs/AWS_QUICK_START.md` under "Cleanup / Teardown"

**Quick cleanup:**
```bash
# WARNING: This will delete EVERYTHING

# 1. Delete ECS service and cluster
aws ecs delete-service --cluster model-registry-cluster \
  --service model-registry-backend-service --force
aws ecs delete-cluster --cluster model-registry-cluster

# 2. Delete load balancer and target group
aws elbv2 delete-load-balancer --load-balancer-arn <alb-arn>
aws elbv2 delete-target-group --target-group-arn <tg-arn>

# 3. Delete RDS
aws rds delete-db-instance --db-instance-identifier model-registry-db \
  --skip-final-snapshot

# 4. Delete S3 bucket
aws s3 rm s3://model-registry-models-<account-id> --recursive
aws s3 rb s3://model-registry-models-<account-id>

# 5. Delete ECR repositories
aws ecr delete-repository --repository-name model-registry-backend --force
aws ecr delete-repository --repository-name model-registry-frontend --force

# 6. Delete security groups, IAM roles, CloudWatch logs
# (See full cleanup script in docs/AWS_QUICK_START.md)
```

## 📚 Additional Resources

### Documentation
- [AWS Quick Start Guide](docs/AWS_QUICK_START.md) - Fastest way to deploy
- [Full Deployment Guide](docs/AWS_DEPLOYMENT_GUIDE.md) - Detailed explanations
- [Local Development](README.md) - Docker Compose setup

### AWS Documentation
- [ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [RDS Documentation](https://docs.aws.amazon.com/rds/)
- [S3 Documentation](https://docs.aws.amazon.com/s3/)
- [CloudWatch Documentation](https://docs.aws.amazon.com/cloudwatch/)

### Tools
- [AWS CLI Reference](https://docs.aws.amazon.com/cli/latest/reference/)
- [AWS Free Tier](https://aws.amazon.com/free/)
- [AWS Pricing Calculator](https://calculator.aws/)
- [Docker Documentation](https://docs.docker.com/)

## ✅ Deployment Checklist

Before submitting to autograder:

- [ ] AWS CLI configured and working
- [ ] Billing alerts set up
- [ ] `.env.aws` configured with secure passwords
- [ ] Deployment script ran successfully
- [ ] Health endpoint returns 200 OK
- [ ] Can authenticate and get token
- [ ] API documentation accessible at `/docs`
- [ ] GitHub Actions secrets configured
- [ ] CI/CD pipeline tested (push to main)
- [ ] CloudWatch logs accessible
- [ ] Cost monitoring enabled
- [ ] ALB DNS recorded for autograder

## 🎯 For the Autograder

**Your submission URL format:**
```
http://<load-balancer-dns>
```

Example:
```
http://model-registry-alb-1234567890.us-east-1.elb.amazonaws.com
```

**To get your URL:**
```bash
aws elbv2 describe-load-balancers \
  --names model-registry-alb \
  --query 'LoadBalancers[0].DNSName' \
  --output text
```

**Test before submitting:**
```bash
export API_URL=http://your-alb-dns-here

# Health check
curl $API_URL/health

# Authentication
curl -X POST $API_URL/authenticate \
  -H "Content-Type: application/json" \
  -d '{"username":"ece30861defaultadminuser","password":"correcthorsebatterystaple123(!__+@**(A;DROP TABLE packages"}'

# API docs
curl $API_URL/docs
```

---

**Questions?** Check the troubleshooting section or review CloudWatch logs for errors.

**Ready to deploy?** Start with `docs/AWS_QUICK_START.md`
