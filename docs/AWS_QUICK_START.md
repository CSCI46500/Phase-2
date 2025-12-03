# AWS Quick Start Guide

This is a condensed guide to get your Model Registry deployed to AWS quickly.

## Prerequisites

1. **AWS Account** - Sign up at https://aws.amazon.com/free/
2. **AWS CLI** - Install from https://aws.amazon.com/cli/
3. **Docker** - Install from https://www.docker.com/get-started
4. **Git & jq** - Should be pre-installed on most systems

## Step 1: Configure AWS CLI (5 minutes)

```bash
# Install AWS CLI if not already installed
# macOS: brew install awscli
# Linux: Use the installer from AWS website

# Configure your credentials
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Default region: us-east-1
# Default output format: json

# Verify configuration
aws sts get-caller-identity
```

### Getting AWS Credentials

1. Log into AWS Console: https://console.aws.amazon.com/
2. Go to IAM → Users → Your username
3. Click "Security credentials" tab
4. Click "Create access key"
5. Select "Command Line Interface (CLI)" use case
6. Save the Access Key ID and Secret Access Key

## Step 2: Set Up Billing Alerts (IMPORTANT - 5 minutes)

**Do this FIRST to avoid unexpected charges!**

```bash
# Create a budget to alert you if costs exceed $10/month
cat > budget.json <<EOF
{
  "BudgetLimit": {
    "Amount": "10",
    "Unit": "USD"
  },
  "BudgetName": "Monthly AWS Budget",
  "BudgetType": "COST",
  "TimeUnit": "MONTHLY"
}
EOF

cat > budget-notifications.json <<EOF
[
  {
    "Notification": {
      "ComparisonOperator": "GREATER_THAN",
      "NotificationType": "ACTUAL",
      "Threshold": 80,
      "ThresholdType": "PERCENTAGE"
    },
    "Subscribers": [
      {
        "Address": "your-email@example.com",
        "SubscriptionType": "EMAIL"
      }
    ]
  }
]
EOF

# Get your account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create budget (update email in budget-notifications.json first!)
aws budgets create-budget \
  --account-id $ACCOUNT_ID \
  --budget file://budget.json \
  --notifications-with-subscribers file://budget-notifications.json
```

## Step 3: Configure Environment (5 minutes)

```bash
# Copy the environment template
cp .env.aws.template .env.aws

# Get your AWS Account ID
aws sts get-caller-identity --query Account --output text

# Edit .env.aws and update these values:
# 1. Replace REPLACE_WITH_YOUR_ACCOUNT_ID with your actual account ID
# 2. Generate a secure DB password: openssl rand -base64 32
# 3. Generate a secure secret key: openssl rand -hex 32

# Example:
# S3_BUCKET_NAME=model-registry-models-123456789012
# DB_PASSWORD=generated_secure_password_here
# SECRET_KEY=generated_secret_key_here
```

## Step 4: Deploy to AWS (20-30 minutes)

**Option A: Automated Deployment (Recommended)**

```bash
# Run the automated deployment script
./scripts/deploy-to-aws.sh
```

This script will:
- Create ECR repositories
- Create S3 bucket
- Create RDS PostgreSQL database (takes ~10 minutes)
- Create ECS cluster
- Build and push Docker images
- Create load balancer and networking
- Deploy ECS service

**Option B: Manual Deployment**

Follow the detailed steps in `docs/AWS_DEPLOYMENT_GUIDE.md`

## Step 5: Verify Deployment (2 minutes)

After deployment completes, you'll see output like:

```
API Endpoint: http://model-registry-alb-123456789.us-east-1.elb.amazonaws.com
```

Test your deployment:

```bash
# Set the URL from deployment output
export API_URL=http://your-alb-dns-here

# Test health endpoint
curl $API_URL/health

# Expected response:
# {"status":"healthy","timestamp":"..."}

# Test authentication
curl -X POST $API_URL/authenticate \
  -H "Content-Type: application/json" \
  -d '{"username":"ece30861defaultadminuser","password":"correcthorsebatterystaple123(!__+@**(A;DROP TABLE packages"}'

# Expected response:
# {"token":"...","calls_remaining":1000}

# Visit API documentation
open $API_URL/docs  # macOS
# or
xdg-open $API_URL/docs  # Linux
```

## Step 6: Set Up CI/CD (10 minutes)

Configure GitHub Actions for automatic deployment on push to main:

1. Go to your GitHub repository
2. Settings → Secrets and variables → Actions
3. Add these secrets:
   - `AWS_ACCESS_KEY_ID` - Your AWS access key
   - `AWS_SECRET_ACCESS_KEY` - Your AWS secret key

4. Push to main branch:
```bash
git add .
git commit -m "Set up AWS deployment"
git push origin main
```

GitHub Actions will automatically:
- Run tests on pull requests
- Deploy to AWS when merged to main
- Run smoke tests after deployment

## Step 7: Provide URL to Autograder

Your autograder URL is your Application Load Balancer DNS:

```bash
# Get your ALB DNS
aws elbv2 describe-load-balancers \
  --names model-registry-alb \
  --query 'LoadBalancers[0].DNSName' \
  --output text
```

Example: `http://model-registry-alb-123456789.us-east-1.elb.amazonaws.com`

Submit this URL to your autograder.

## Monitoring Your Application

### View Logs

```bash
# Stream application logs
aws logs tail /ecs/model-registry-backend --follow

# View last 100 lines
aws logs tail /ecs/model-registry-backend --since 1h

# Filter for errors
aws logs filter-log-events \
  --log-group-name /ecs/model-registry-backend \
  --filter-pattern "ERROR"
```

### Check Service Status

```bash
# Check ECS service
aws ecs describe-services \
  --cluster model-registry-cluster \
  --services model-registry-backend-service

# Check running tasks
aws ecs list-tasks \
  --cluster model-registry-cluster \
  --service-name model-registry-backend-service
```

### CloudWatch Dashboard

1. Go to AWS Console → CloudWatch
2. View metrics for ECS, RDS, and ALB
3. Create alarms for high CPU, memory, or error rates

## Cost Management

### Expected Monthly Costs (After Free Tier)

- **ECS Fargate** (1 task, 0.5 vCPU, 1GB RAM, 24/7): ~$15/month
- **RDS db.t3.micro** (Free tier: 750 hours/month): $0 (first year)
- **Application Load Balancer**: ~$16/month
- **S3 Storage** (10GB): ~$0.23/month
- **Data Transfer**: Variable (~$1-5/month for testing)

**Estimated Total: ~$32-35/month** (first year with RDS free tier)

### Cost Optimization Tips

1. **Stop RDS when not in use** (development only):
```bash
aws rds stop-db-instance --db-instance-identifier model-registry-db
```

2. **Use Fargate Spot** (70% cheaper, but tasks can be interrupted):
Edit task definition to use FARGATE_SPOT capacity provider

3. **Reduce task count to 0** when not testing:
```bash
aws ecs update-service \
  --cluster model-registry-cluster \
  --service model-registry-backend-service \
  --desired-count 0
```

4. **Set up auto-scaling** to scale down during off-hours

### Monitor Costs

```bash
# Check current month costs
aws ce get-cost-and-usage \
  --time-period Start=2025-12-01,End=2025-12-31 \
  --granularity MONTHLY \
  --metrics BlendedCost

# View by service
aws ce get-cost-and-usage \
  --time-period Start=2025-12-01,End=2025-12-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE
```

Or use AWS Cost Explorer in the Console.

## Cleanup / Teardown

**When you're done with the project** (to avoid ongoing charges):

```bash
# Delete ECS service (stops tasks)
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

# Delete load balancer
ALB_ARN=$(aws elbv2 describe-load-balancers \
  --names model-registry-alb \
  --query 'LoadBalancers[0].LoadBalancerArn' \
  --output text)
aws elbv2 delete-load-balancer --load-balancer-arn $ALB_ARN

# Wait 2-3 minutes for ALB to delete, then delete target group
TG_ARN=$(aws elbv2 describe-target-groups \
  --names model-registry-backend-tg \
  --query 'TargetGroups[0].TargetGroupArn' \
  --output text)
aws elbv2 delete-target-group --target-group-arn $TG_ARN

# Delete RDS database
aws rds delete-db-instance \
  --db-instance-identifier model-registry-db \
  --skip-final-snapshot

# Empty and delete S3 bucket
source .env.aws
aws s3 rm s3://${S3_BUCKET_NAME} --recursive
aws s3 rb s3://${S3_BUCKET_NAME}

# Delete ECR repositories (and all images)
aws ecr delete-repository \
  --repository-name model-registry-backend \
  --force

aws ecr delete-repository \
  --repository-name model-registry-frontend \
  --force

# Delete CloudWatch log groups
aws logs delete-log-group --log-group-name /ecs/model-registry-backend
aws logs delete-log-group --log-group-name /ecs/model-registry-frontend

# Delete security groups (wait for resources to be deleted first - may take 5-10 min)
# Get security group IDs
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query 'Vpcs[0].VpcId' --output text)

ECS_SG_ID=$(aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=model-registry-ecs-sg" \
  --query 'SecurityGroups[0].GroupId' \
  --output text)

ALB_SG_ID=$(aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=model-registry-alb-sg" \
  --query 'SecurityGroups[0].GroupId' \
  --output text)

RDS_SG_ID=$(aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=model-registry-rds-sg" \
  --query 'SecurityGroups[0].GroupId' \
  --output text)

# Delete security groups
aws ec2 delete-security-group --group-id $ECS_SG_ID
aws ec2 delete-security-group --group-id $ALB_SG_ID
aws ec2 delete-security-group --group-id $RDS_SG_ID

# Delete IAM roles
aws iam delete-role-policy \
  --role-name model-registry-ecs-task-role \
  --policy-name model-registry-task-permissions

aws iam detach-role-policy \
  --role-name model-registry-ecs-execution-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

aws iam delete-role --role-name model-registry-ecs-execution-role
aws iam delete-role --role-name model-registry-ecs-task-role
```

## Troubleshooting

### Issue: Deployment script fails

**Check AWS credentials:**
```bash
aws sts get-caller-identity
```

**Check Docker is running:**
```bash
docker ps
```

### Issue: ECS tasks fail to start

**Check task logs:**
```bash
# Get task ARN
TASK_ARN=$(aws ecs list-tasks \
  --cluster model-registry-cluster \
  --service-name model-registry-backend-service \
  --query 'taskArns[0]' \
  --output text)

# Describe task
aws ecs describe-tasks \
  --cluster model-registry-cluster \
  --tasks $TASK_ARN
```

**Common issues:**
- Database connection failed: Check RDS security group allows ECS tasks
- Image pull failed: Check ECR repository exists and has images
- Out of memory: Increase memory in task definition

### Issue: Can't access API via load balancer

**Check target health:**
```bash
TG_ARN=$(aws elbv2 describe-target-groups \
  --names model-registry-backend-tg \
  --query 'TargetGroups[0].TargetGroupArn' \
  --output text)

aws elbv2 describe-target-health --target-group-arn $TG_ARN
```

**Check security groups:**
- ALB security group allows port 80 from 0.0.0.0/0
- ECS security group allows port 8000 from ALB security group

### Issue: High AWS costs

**Check current costs:**
```bash
aws ce get-cost-and-usage \
  --time-period Start=2025-12-01,End=2025-12-02 \
  --granularity DAILY \
  --metrics BlendedCost
```

**Most common cost culprits:**
1. Application Load Balancer (~$16/month base cost)
2. ECS Fargate tasks running 24/7
3. RDS instance (free tier first year)
4. Data transfer costs

## Next Steps

1. **Set up custom domain** - Use Route 53 to map a domain to your ALB
2. **Enable HTTPS** - Use AWS Certificate Manager for free SSL/TLS certificates
3. **Implement auto-scaling** - Scale ECS tasks based on CPU/memory
4. **Set up monitoring** - Create CloudWatch dashboards and alarms
5. **Database backups** - Configure automated RDS snapshots
6. **Multi-AZ deployment** - Deploy across multiple availability zones for high availability

## Support Resources

- **AWS Documentation**: https://docs.aws.amazon.com/
- **AWS Free Tier**: https://aws.amazon.com/free/
- **AWS Cost Calculator**: https://calculator.aws/
- **AWS Support**: https://console.aws.amazon.com/support/

## Summary Checklist

- [ ] AWS CLI installed and configured
- [ ] Billing alerts set up
- [ ] `.env.aws` file created with secure passwords
- [ ] Deployment script executed successfully
- [ ] Health endpoint returns 200 OK
- [ ] Authentication works
- [ ] GitHub Actions secrets configured
- [ ] Autograder URL submitted
- [ ] Monitoring and logs accessible
- [ ] Cost alerts configured

**Your deployment is complete!** 🎉

Your API URL: `http://your-alb-dns-here`
