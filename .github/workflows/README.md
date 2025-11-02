# CI/CD Setup Guide

This document explains how to set up and use the GitHub Actions CI/CD pipelines for automated testing and AWS deployment.

## Overview

This project has two main workflows:

1. **CI (Continuous Integration)**: Runs automated tests on every pull request
2. **CD (Continuous Deployment)**: Deploys to AWS after successful merge to main branch

## CI Workflow (`.github/workflows/ci.yml`)

### What it does:
- ✅ Runs on every pull request to `main` or `develop` branches
- ✅ Tests against multiple Python versions (3.10, 3.11, 3.12)
- ✅ Installs dependencies using `./run install`
- ✅ Runs tests with coverage using `./run test`
- ✅ Performs code quality checks (flake8, black)
- ✅ Generates and uploads coverage reports

### How to use:
1. Create a pull request
2. The CI workflow automatically runs
3. Check the "Actions" tab in GitHub to see results
4. All tests must pass before merging

## CD Workflow (`.github/workflows/cd.yml`)

### What it does:
- 🚀 Runs automatically when code is merged to `main` branch
- 🚀 Re-runs tests to ensure nothing broke
- 🚀 Deploys to AWS using your chosen deployment method
- 🚀 Performs post-deployment health checks

### Deployment Options:

The workflow supports 4 AWS deployment methods:

#### 1. **Elastic Beanstalk** (Default - Easiest)
- Best for: Web applications, APIs
- Automatic scaling and load balancing
- Easy to manage

#### 2. **Lambda** (Serverless)
- Best for: Event-driven functions, APIs
- Pay only for execution time
- Auto-scaling

#### 3. **EC2 via CodeDeploy**
- Best for: Traditional applications
- More control over infrastructure
- Requires EC2 instances

#### 4. **ECS** (Containerized)
- Best for: Docker applications
- Microservices architecture
- Requires Dockerfile

## Setup Instructions

### Step 1: Configure GitHub Secrets

Go to your GitHub repository → Settings → Secrets and variables → Actions → New repository secret

Add the following secrets:

#### Required for all deployments:
```
AWS_ACCESS_KEY_ID          - Your AWS access key
AWS_SECRET_ACCESS_KEY      - Your AWS secret key
AWS_REGION                 - AWS region (e.g., us-east-1)
```

#### For Elastic Beanstalk (Recommended):
```
EB_APP_NAME               - Your Elastic Beanstalk application name
EB_ENV_NAME               - Your Elastic Beanstalk environment name
```

#### For Lambda:
```
LAMBDA_FUNCTION_NAME      - Your Lambda function name
```

#### For CodeDeploy:
```
S3_BUCKET                 - S3 bucket for deployments
CODEDEPLOY_APP_NAME       - CodeDeploy application name
CODEDEPLOY_GROUP_NAME     - CodeDeploy deployment group name
```

#### For ECS:
```
ECR_REPOSITORY            - Your ECR repository name
ECS_CLUSTER               - Your ECS cluster name
ECS_SERVICE               - Your ECS service name
ECS_TASK_DEFINITION       - Path to task definition file
```

### Step 2: Configure Deployment Type

Go to your GitHub repository → Settings → Secrets and variables → Actions → Variables tab

Add a variable:
```
DEPLOYMENT_TYPE           - elasticbeanstalk | lambda | codedeploy | ecs
```

If not set, defaults to Elastic Beanstalk.

### Step 3: Set up AWS Resources

#### Option A: Elastic Beanstalk Setup (Recommended for beginners)

```bash
# Install EB CLI
pip install awsebcli

# Initialize Elastic Beanstalk
eb init -p python-3.11 my-app-name --region us-east-1

# Create environment
eb create my-app-env

# Note the application and environment names for GitHub secrets
```

#### Option B: Lambda Setup

```bash
# Create Lambda function
aws lambda create-function \
  --function-name my-function \
  --runtime python3.11 \
  --role arn:aws:iam::YOUR_ACCOUNT:role/lambda-role \
  --handler main.lambda_handler \
  --zip-file fileb://function.zip
```

#### Option C: EC2 with CodeDeploy Setup

1. Create EC2 instances
2. Create CodeDeploy application and deployment group
3. Create S3 bucket for deployments
4. Create appspec.yml file (template below)

#### Option D: ECS Setup

1. Create ECR repository
2. Create ECS cluster
3. Create task definition
4. Create ECS service
5. Create Dockerfile (template below)

### Step 4: Protect Your Main Branch

Go to Settings → Branches → Add branch protection rule:

1. Branch name pattern: `main`
2. ✅ Require a pull request before merging
3. ✅ Require status checks to pass before merging
4. ✅ Select "Run Automated Tests" as required check
5. ✅ Require conversation resolution before merging

This ensures CD only runs after tests pass!

## AWS IAM Permissions

Your AWS user/role needs these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "elasticbeanstalk:*",
        "s3:*",
        "cloudformation:*",
        "ec2:*",
        "autoscaling:*",
        "elasticloadbalancing:*",
        "lambda:*",
        "codedeploy:*",
        "ecs:*",
        "ecr:*",
        "iam:PassRole"
      ],
      "Resource": "*"
    }
  ]
}
```

**Note**: In production, use more restrictive permissions!

## Testing the Setup

### Test CI:
1. Create a new branch: `git checkout -b test-ci`
2. Make a small change
3. Push: `git push origin test-ci`
4. Create a pull request on GitHub
5. Watch the "Actions" tab to see tests run

### Test CD:
1. After CI passes, merge your PR
2. Watch the "Actions" tab to see deployment
3. Check your AWS console to verify deployment

## Workflow Diagram

```
┌─────────────────┐
│  Pull Request   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   CI Workflow   │
│  - Run tests    │
│  - Code checks  │
└────────┬────────┘
         │
    ✅ Pass / ❌ Fail
         │
         ▼
┌─────────────────┐
│  Merge to Main  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   CD Workflow   │
│  - Run tests    │
│  - Deploy AWS   │
│  - Health check │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ✅ Deployed!    │
└─────────────────┘
```

## Additional Files Needed

### For CodeDeploy - Create `appspec.yml`:

```yaml
version: 0.0
os: linux
files:
  - source: /
    destination: /home/ec2-user/app
hooks:
  ApplicationStop:
    - location: scripts/stop_application.sh
      timeout: 300
  ApplicationStart:
    - location: scripts/start_application.sh
      timeout: 300
  ValidateService:
    - location: scripts/validate_service.sh
      timeout: 300
```

### For ECS - Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY dependencies.txt .
RUN pip install --no-cache-dir -r dependencies.txt

COPY . .

CMD ["python", "main.py"]
```

### For Lambda - Modify `main.py` to add handler:

```python
def lambda_handler(event, context):
    # Your Lambda handler code
    return {
        'statusCode': 200,
        'body': json.dumps('Success')
    }
```

## Troubleshooting

### CI fails with "Permission denied: ./run"
- Make sure the run script is executable: `git update-index --chmod=+x run`

### CD fails with "AWS credentials not configured"
- Check that AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are set in GitHub secrets

### Deployment succeeds but app doesn't work
- Check AWS CloudWatch logs
- Verify environment variables are set in AWS
- Ensure security groups allow traffic

### Tests pass locally but fail in CI
- Check Python version compatibility
- Verify all dependencies are in dependencies.txt
- Check for environment-specific code

## Manual Deployment

You can manually trigger deployments:
1. Go to Actions tab
2. Select "CD - Deploy to AWS"
3. Click "Run workflow"
4. Select branch and click "Run workflow"

## Monitoring

- **GitHub Actions**: Check the "Actions" tab for workflow runs
- **AWS CloudWatch**: Monitor application logs
- **AWS Console**: Check service health in your chosen AWS service

## Best Practices

1. ✅ Always create PRs instead of pushing directly to main
2. ✅ Wait for CI to pass before merging
3. ✅ Test changes in a development environment first
4. ✅ Monitor deployments in the Actions tab
5. ✅ Set up CloudWatch alarms for critical metrics
6. ✅ Use separate AWS accounts for dev/staging/production
7. ✅ Regularly rotate AWS credentials
8. ✅ Keep dependencies up to date

## Getting Help

- GitHub Actions docs: https://docs.github.com/en/actions
- AWS Elastic Beanstalk: https://docs.aws.amazon.com/elasticbeanstalk/
- AWS Lambda: https://docs.aws.amazon.com/lambda/
- AWS ECS: https://docs.aws.amazon.com/ecs/
- AWS CodeDeploy: https://docs.aws.amazon.com/codedeploy/

## Cost Considerations

- **Elastic Beanstalk**: ~$15-50/month (t2.micro/t3.small)
- **Lambda**: Pay per invocation (free tier: 1M requests/month)
- **ECS**: ~$10-40/month + container costs
- **EC2**: ~$5-50/month depending on instance type

Use AWS Free Tier for learning: https://aws.amazon.com/free/