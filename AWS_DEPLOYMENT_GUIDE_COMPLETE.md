# Complete AWS Deployment Guide for Phase 2

## 🎯 Goal

Deploy your Phase 2 Model Registry to AWS so the autograder can test it. You need:
1. **Backend URL** (e.g., `http://your-alb.us-east-1.elb.amazonaws.com:8000`)
2. **Frontend URL** (e.g., `http://your-alb.us-east-1.elb.amazonaws.com`)

---

## 📋 Prerequisites

### 1. AWS Account Setup

```bash
# Create AWS account (if you don't have one)
# https://aws.amazon.com/free

# Install AWS CLI
# macOS
brew install awscli

# Linux
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Verify installation
aws --version
```

### 2. Configure AWS Credentials

```bash
# Create IAM user with permissions:
# - AmazonEC2FullAccess
# - AmazonECSFullAccess
# - AmazonRDSFullAccess
# - AmazonS3FullAccess
# - IAMFullAccess
# - CloudWatchLogsFullAccess
# - ElasticLoadBalancingFullAccess

# Configure CLI
aws configure

# Enter:
# AWS Access Key ID: YOUR_ACCESS_KEY
# AWS Secret Access Key: YOUR_SECRET_KEY
# Default region: us-east-1
# Default output format: json

# Verify
aws sts get-caller-identity
```

### 3. Set Up Billing Alerts

**CRITICAL:** Set up billing alerts to avoid unexpected charges!

```bash
# Go to AWS Console > Billing > Billing Preferences
# Enable:
# - Receive Free Tier Usage Alerts
# - Receive Billing Alerts

# Create alarm for $50
# Go to CloudWatch > Alarms > Create Alarm
```

### 4. Install Docker

```bash
# Verify Docker is installed and running
docker --version
docker ps

# If not installed:
# https://docs.docker.com/get-docker/
```

---

## 🚀 Quick Deployment (Automated)

### Step 1: Configure Environment

```bash
cd /home/bperovic/software-engineering/Phase-2

# Copy template
cp .env.aws.template .env.aws

# Edit .env.aws with your values
nano .env.aws
```

**Important values to change in .env.aws:**

```bash
# AWS Configuration
AWS_REGION=us-east-1  # KEEP THIS
PROJECT_NAME=model-registry  # Can change

# S3 Bucket - MUST be globally unique
S3_BUCKET_NAME=model-registry-models-YOUR_AWS_ACCOUNT_ID  # Replace YOUR_AWS_ACCOUNT_ID

# Database - Generate secure password
DB_PASSWORD=$(openssl rand -base64 32)  # Run this and paste result

# Security
SECRET_KEY=$(openssl rand -hex 32)  # Run this and paste result

# DO NOT CHANGE (required by autograder)
ADMIN_USERNAME=ece30861defaultadminuser
ADMIN_PASSWORD='correcthorsebatterystaple123(!__+@**(A'"'"'";DROP TABLE packages;'
```

### Step 2: Run Automated Deployment

```bash
# This script does EVERYTHING:
# - Creates ECR repositories
# - Creates S3 bucket
# - Creates RDS database
# - Builds and pushes Docker images
# - Creates ECS cluster
# - Creates Application Load Balancer
# - Deploys backend and frontend services
# - Tests endpoints

./deploy-to-aws-complete.sh
```

**Expected Time:** 20-30 minutes (mostly waiting for RDS)

**What you'll see:**
```
==================================================
Phase 2 Model Registry - Complete AWS Deployment
==================================================

Step 1: Verifying AWS credentials...
✓ AWS Account ID: 123456789012

Step 2: Creating ECR repositories...
✓ Created ECR repository: model-registry-backend
✓ Created ECR repository: model-registry-frontend

Step 3: Creating S3 bucket...
✓ Created S3 bucket: model-registry-models-123456789012

Step 4: Creating RDS PostgreSQL database...
Creating RDS instance (this takes ~10 minutes)...
Waiting for RDS instance to be available...
✓ Created RDS instance: model-registry-db
  Endpoint: model-registry-db.abc123.us-east-1.rds.amazonaws.com

[... continues ...]

==================================================
DEPLOYMENT COMPLETE!
==================================================

📋 Deployment Summary:

AWS Resources Created:
  ✓ ECR Repositories: model-registry-backend, model-registry-frontend
  ✓ S3 Bucket: model-registry-models-123456789012
  ✓ RDS Instance: model-registry-db
  ✓ ECS Cluster: model-registry-cluster
  ✓ ECS Services: model-registry-backend-service, model-registry-frontend-service
  ✓ Application Load Balancer: model-registry-alb
  ✓ CloudWatch Log Groups: /ecs/model-registry-backend, /ecs/model-registry-frontend

🌐 Your Application URLs:

  Backend API:  http://model-registry-alb-123456789.us-east-1.elb.amazonaws.com:8000
  Frontend UI:  http://model-registry-alb-123456789.us-east-1.elb.amazonaws.com

📝 For Autograder Registration:

  endpoint:     http://model-registry-alb-123456789.us-east-1.elb.amazonaws.com:8000
  fe_endpoint:  http://model-registry-alb-123456789.us-east-1.elb.amazonaws.com
```

### Step 3: Verify Deployment

```bash
# Get your ALB DNS from the output above or run:
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --names model-registry-alb \
  --query 'LoadBalancers[0].DNSName' \
  --output text)

echo "Backend: http://${ALB_DNS}:8000"
echo "Frontend: http://${ALB_DNS}"

# Test backend
curl "http://${ALB_DNS}:8000/health"

# Expected response:
# {"status":"healthy","timestamp":"2025-12-05T...","components":{"database":"healthy","s3":"healthy"}}

# Test frontend (should return HTML)
curl "http://${ALB_DNS}/"

# Test authentication
curl -X POST "http://${ALB_DNS}:8000/authenticate" \
  -H "Content-Type: application/json" \
  -d '{"username": "ece30861defaultadminuser", "password": "correcthorsebatterystaple123(!__+@**(A'\''\"";DROP TABLE packages;"}'

# Expected response:
# {"token":"...","calls_remaining":1000}
```

---

## 📡 Register with Autograder

### Step 1: Get Your Team Information

```bash
# Your group number (check Brightspace)
GROUP_NUMBER=XX  # Replace with your group number

# Your GitHub token (create at https://github.com/settings/tokens)
# Needs: repo access
GITHUB_TOKEN="ghp_..."  # Replace with your token

# Your team members
TEAM_NAMES=["Elijah Beyer", "Mauricio Salazar", "Bozidar Perovic", "Anthony Chavez"]
```

### Step 2: Register with Autograder

```bash
# Get your URLs (from deployment output or DEPLOYMENT_URLS.txt)
BACKEND_URL="http://YOUR_ALB_DNS:8000"
FRONTEND_URL="http://YOUR_ALB_DNS"

# Register
curl -X POST "http://dl-berlin.ecn.purdue.edu/api/phase2/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"group\": $GROUP_NUMBER,
    \"github\": \"https://github.com/YOUR_USERNAME/Phase-2\",
    \"endpoint\": \"$BACKEND_URL\",
    \"fe_endpoint\": \"$FRONTEND_URL\",
    \"gh_token\": \"$GITHUB_TOKEN\",
    \"names\": $TEAM_NAMES
  }"

# Expected response:
# HTTP 201 Created
```

### Step 3: Schedule Autograder Run

```bash
# Schedule a test
curl -X POST "http://dl-berlin.ecn.purdue.edu/api/phase2/schedule" \
  -H "Content-Type: application/json" \
  -d "{
    \"group\": $GROUP_NUMBER,
    \"gh_token\": \"$GITHUB_TOKEN\"
  }"

# Check status
curl "http://dl-berlin.ecn.purdue.edu/api/phase2/run/all"
```

### Step 4: Get Results

```bash
# Wait 5-10 minutes for autograder to complete, then:

# Get last run results
curl "http://dl-berlin.ecn.purdue.edu/api/phase2/last_run?group=$GROUP_NUMBER&gh_token=$GITHUB_TOKEN"

# Get best run results
curl "http://dl-berlin.ecn.purdue.edu/api/phase2/best_run?group=$GROUP_NUMBER&gh_token=$GITHUB_TOKEN"
```

---

## 🔧 Troubleshooting

### Issue: RDS Takes Too Long

**Solution:** RDS creation takes 10-15 minutes. Be patient.

```bash
# Check RDS status
aws rds describe-db-instances \
  --db-instance-identifier model-registry-db \
  --query 'DBInstances[0].DBInstanceStatus'
```

### Issue: ECS Service Won't Start

**Solution:** Check CloudWatch logs

```bash
# View logs
aws logs tail /ecs/model-registry-backend --follow

# Common issues:
# - Database connection failed (check RDS endpoint)
# - S3 permissions denied (check IAM role)
# - Environment variables missing
```

### Issue: ALB Health Check Fails

**Solution:** Verify health endpoint

```bash
# Get task IP directly
TASK_ARN=$(aws ecs list-tasks \
  --cluster model-registry-cluster \
  --service-name model-registry-backend-service \
  --query 'taskArns[0]' \
  --output text)

TASK_IP=$(aws ecs describe-tasks \
  --cluster model-registry-cluster \
  --tasks $TASK_ARN \
  --query 'tasks[0].attachments[0].details[?name==`privateIPv4Address`].value' \
  --output text)

# Test directly (from within VPC or with VPN)
curl "http://${TASK_IP}:8000/health"
```

### Issue: Autograder Can't Reach Backend

**Checklist:**
- [ ] Security group allows inbound traffic on ports 80 and 8000
- [ ] ALB is internet-facing (not internal)
- [ ] Target group health checks pass
- [ ] ECS tasks have public IPs assigned

```bash
# Check security group rules
aws ec2 describe-security-groups \
  --group-names model-registry-sg \
  --query 'SecurityGroups[0].IpPermissions'

# Check ALB scheme
aws elbv2 describe-load-balancers \
  --names model-registry-alb \
  --query 'LoadBalancers[0].Scheme'

# Should be "internet-facing"

# Check target health
aws elbv2 describe-target-health \
  --target-group-arn $(aws elbv2 describe-target-groups \
    --names model-registry-backend-tg \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text)
```

### Issue: High AWS Costs

**Prevention:**
```bash
# Stop ECS services when not testing
aws ecs update-service \
  --cluster model-registry-cluster \
  --service model-registry-backend-service \
  --desired-count 0

aws ecs update-service \
  --cluster model-registry-cluster \
  --service model-registry-frontend-service \
  --desired-count 0

# Restart when needed
aws ecs update-service \
  --cluster model-registry-cluster \
  --service model-registry-backend-service \
  --desired-count 1
```

**Monitor costs:**
```bash
# AWS Console > Billing Dashboard > Cost Explorer
# Set up budget alerts for $25, $50
```

---

## 🔄 Update Deployment

### Option 1: Re-run Deployment Script

```bash
# Rebuilds images, pushes to ECR, updates ECS services
./deploy-to-aws-complete.sh
```

### Option 2: GitHub Actions (Automated CI/CD)

```bash
# Push to main branch triggers automatic deployment
git add .
git commit -m "Update feature X"
git push origin main

# Check GitHub Actions tab for deployment status
```

### Option 3: Manual Update

```bash
# Build new image
docker build -f Dockerfile.production -t model-registry-backend .

# Tag
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
docker tag model-registry-backend:latest \
  ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/model-registry-backend:latest

# Push
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com

docker push ${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/model-registry-backend:latest

# Update service
aws ecs update-service \
  --cluster model-registry-cluster \
  --service model-registry-backend-service \
  --force-new-deployment
```

---

## 🧹 Cleanup (Delete Everything)

**WARNING:** This deletes ALL AWS resources. Only do this after the course ends!

```bash
# Delete ECS services
aws ecs update-service \
  --cluster model-registry-cluster \
  --service model-registry-backend-service \
  --desired-count 0

aws ecs delete-service \
  --cluster model-registry-cluster \
  --service model-registry-backend-service \
  --force

# Delete ECS cluster
aws ecs delete-cluster --cluster model-registry-cluster

# Delete ALB
ALB_ARN=$(aws elbv2 describe-load-balancers \
  --names model-registry-alb \
  --query 'LoadBalancers[0].LoadBalancerArn' \
  --output text)

aws elbv2 delete-load-balancer --load-balancer-arn $ALB_ARN

# Delete target groups
aws elbv2 delete-target-group \
  --target-group-arn $(aws elbv2 describe-target-groups \
    --names model-registry-backend-tg \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text)

# Delete RDS (with snapshot)
aws rds delete-db-instance \
  --db-instance-identifier model-registry-db \
  --final-db-snapshot-identifier model-registry-final-snapshot

# Delete S3 bucket (empty it first)
aws s3 rm s3://model-registry-models-${AWS_ACCOUNT_ID} --recursive
aws s3 rb s3://model-registry-models-${AWS_ACCOUNT_ID}

# Delete ECR repositories
aws ecr delete-repository \
  --repository-name model-registry-backend \
  --force

aws ecr delete-repository \
  --repository-name model-registry-frontend \
  --force

# Delete CloudWatch log groups
aws logs delete-log-group --log-group-name /ecs/model-registry-backend
aws logs delete-log-group --log-group-name /ecs/model-registry-frontend

# Delete security group
SG_ID=$(aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=model-registry-sg" \
  --query 'SecurityGroups[0].GroupId' \
  --output text)

aws ec2 delete-security-group --group-id $SG_ID
```

---

## 📊 Cost Breakdown

### Free Tier (First 12 Months)
- **RDS db.t3.micro:** 750 hours/month → $0
- **S3:** 5GB storage → $0
- **CloudWatch:** 5GB logs → $0
- **ECR:** 500MB storage → $0

### Paid Services (After Free Tier)
- **ECS Fargate:**
  - Backend (1 vCPU, 2GB RAM): ~$15/month
  - Frontend (0.5 vCPU, 1GB RAM): ~$7/month
- **Application Load Balancer:** ~$16/month
- **RDS db.t3.micro (beyond free tier):** ~$15/month
- **S3 (beyond 5GB):** ~$0.023/GB/month
- **Data Transfer:** ~$0.09/GB

**Total Estimated Cost:** $35-50/month (after free tier expires)

### Cost Optimization Tips
1. **Stop services when not testing** (scale to 0)
2. **Use Fargate Spot** (70% cheaper, may be interrupted)
3. **Delete old CloudWatch logs**
4. **Use S3 lifecycle policies** (move to Glacier)
5. **Set up billing alerts!**

---

## ✅ Deployment Checklist

Before submitting to autograder:

- [ ] AWS account created and configured
- [ ] Billing alerts set up ($25, $50)
- [ ] .env.aws configured with secure passwords
- [ ] Deployment script ran successfully
- [ ] Backend health endpoint returns 200
- [ ] Frontend loads in browser
- [ ] Authentication works (test with curl)
- [ ] Registered with autograder
- [ ] Autograder test scheduled
- [ ] URLs saved in DEPLOYMENT_URLS.txt

---

## 📞 Getting Help

**AWS Issues:**
- Check CloudWatch logs: `aws logs tail /ecs/model-registry-backend --follow`
- Check ECS events: AWS Console > ECS > Clusters > model-registry-cluster
- AWS documentation: https://docs.aws.amazon.com/

**Autograder Issues:**
- Check autograder status: `curl http://dl-berlin.ecn.purdue.edu/api/phase2/stats`
- Download logs: Use the `/phase2/log/download` endpoint
- Contact course staff during office hours

**Cost Issues:**
- View detailed costs: AWS Console > Billing > Cost Explorer
- Stop services: Scale ECS desired count to 0
- Request AWS credits: https://aws.amazon.com/education/awseducate/

---

## 🎉 Success!

When your deployment is successful:

1. ✅ Backend URL returns `{"status":"healthy"}`
2. ✅ Frontend loads in browser
3. ✅ Autograder can reach both URLs
4. ✅ All 320 tests pass (or most of them!)
5. ✅ Your Phase 2 is complete!

**Good luck with your submission!** 🚀

---

**Last Updated:** December 5, 2025
**Author:** Phase 2 Team
**Project:** ECE 30861/46100 Software Engineering
