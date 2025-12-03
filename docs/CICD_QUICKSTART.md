# CI/CD Quick Start Guide

## Fast Setup (5 Minutes)

This guide will get you up and running with CI/CD in 5 minutes using AWS Elastic Beanstalk (the easiest option).

### Prerequisites
- GitHub repository with your code pushed
- AWS account ([sign up for free tier](https://aws.amazon.com/free/))
- AWS CLI installed locally

### Step 1: Create AWS IAM User (2 minutes)

1. Go to AWS Console → IAM → Users → Add User
2. Username: `github-actions-deploy`
3. Select: **Access key - Programmatic access**
4. Permissions: Attach **AdministratorAccess** (for simplicity; restrict later!)
5. Save the **Access Key ID** and **Secret Access Key**

### Step 2: Configure GitHub Secrets (1 minute)

Go to your GitHub repo → Settings → Secrets and variables → Actions → New repository secret

Add these 3 secrets:
```
Name: AWS_ACCESS_KEY_ID
Value: [paste your access key]

Name: AWS_SECRET_ACCESS_KEY
Value: [paste your secret key]

Name: AWS_REGION
Value: us-east-1
```

### Step 3: Create Elastic Beanstalk Application (1 minute)

```bash
# Install EB CLI
pip install awsebcli

# Initialize (run in your project directory)
eb init -p python-3.11 phase2-app --region us-east-1

# Create environment (this takes ~5 minutes)
eb create phase2-env
```

After it finishes, note the application and environment names.

### Step 4: Add EB Secrets to GitHub (30 seconds)

Add 2 more secrets to GitHub:
```
Name: EB_APP_NAME
Value: phase2-app

Name: EB_ENV_NAME
Value: phase2-env
```

### Step 5: Enable Branch Protection (30 seconds)

GitHub repo → Settings → Branches → Add rule:
- Branch name: `main`
- Require pull request before merging
- Require status checks to pass
- Select: "Run Automated Tests"
- Save

### Step 6: Test It! (1 minute)

```bash
# Create a test branch
git checkout -b test-cicd

# Make a small change
echo "# Testing CI/CD" >> README.md

# Commit and push
git add .
git commit -m "Test CI/CD pipeline"
git push origin test-cicd
```

Now:
1. Go to GitHub and create a Pull Request
2. Watch the "Actions" tab - tests will run automatically! 
3. Once tests pass, merge the PR
4. Watch "Actions" again - deployment will start automatically! 
5. Check your AWS console to see the deployment


You now have:
- Automated tests on every PR
- Automatic deployment to AWS on merge
- Professional CI/CD pipeline

## What Happens Now?

### When you create a Pull Request:
1. GitHub Actions automatically runs your tests
2. You see a check or an X on the PR
3. You can only merge if tests pass

### When you merge to main:
1. GitHub Actions runs tests again
2. If tests pass, automatically deploys to AWS
3. You can see your app running in Elastic Beanstalk console

## Viewing Your Application

```bash
# Open your application in browser
eb open
```

## Checking Logs

```bash
# View recent logs
eb logs

# Stream logs in real-time
eb logs --stream
```

## Common Commands

```bash
# Check application status
eb status

# View health
eb health

# SSH into instance (for debugging)
eb ssh

# Manually deploy (if needed)
eb deploy
```

## Troubleshooting

### Tests fail in CI but pass locally
- Check Python version (CI uses 3.10, 3.11, 3.12)
- Ensure all dependencies are in dependencies.txt

### Deployment fails
- Check GitHub Actions logs in "Actions" tab
- Verify AWS credentials are correct
- Check EB logs: `eb logs`

### Application runs but crashes
- Check EB logs: `eb logs`
- Verify environment variables in EB console
- Make sure port 8000 is not hardcoded (use EB's port)

## Next Steps

### 1. Add environment variables (if needed)
```bash
eb setenv KEY=value
```

### 2. Set up a custom domain
```bash
# In EB console: Configuration → Load Balancer → Add listener
```

### 3. Enable HTTPS
```bash
# In EB console: Configuration → Load Balancer → Add certificate
```

### 4. Set up monitoring
- CloudWatch alarms for health
- SNS notifications for failures

### 5. Add staging environment
```bash
eb create phase2-staging
```

## Cost

Free Tier includes:
- 750 hours/month of t2.micro or t3.micro
- Enough for 1 environment running 24/7

After free tier: ~$15-30/month for small apps

## Advanced: Using Other AWS Services

See `.github/workflows/README.md` for:
- AWS Lambda deployment (serverless)
- ECS deployment (containers)
- EC2 with CodeDeploy

## Security Best Practices

1. **Rotate AWS keys regularly** (every 90 days)
2. **Use separate AWS accounts** for dev/prod
3. **Restrict IAM permissions** (don't use AdministratorAccess in prod)
4. **Enable MFA** on AWS root account
5. **Never commit secrets** to git

## Getting Help

- Check GitHub Actions logs: Repo → Actions tab
- Check EB logs: `eb logs`
- AWS Support: https://console.aws.amazon.com/support/
- GitHub Actions docs: https://docs.github.com/actions

## Example Workflow

```
1. Write code
2. Create branch: git checkout -b feature-x
3. Push: git push origin feature-x
4. Create PR on GitHub
5. Wait for CI to pass
6. Get code review
7. Merge PR
8. Automatic deployment!
9. Verify in production
```

## Architecture Diagram

```
Developer
   ↓
Push to Branch
   ↓
Create PR
   ↓
┌─────────────────────┐
│  GitHub Actions CI  │
│  • Run tests        │
│  • Check coverage   │
│  • Code quality     │
└──────────┬──────────┘
           ↓
       Pass /  Fail
           ↓
      Merge to main
           ↓
┌─────────────────────┐
│  GitHub Actions CD  │
│  • Run tests        │
│  • Deploy to AWS    │
│  • Health check     │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│  AWS Elastic Beanstalk│
│  • Auto-scaling     │
│  • Load balancing   │
│  • Monitoring       │
└─────────────────────┘
           ↓
       Live!
```

## Files Created

- `.github/workflows/ci.yml` - CI pipeline (tests on PR)
- `.github/workflows/cd.yml` - CD pipeline (deploy on merge)
- `.github/workflows/README.md` - Detailed documentation
- `Dockerfile` - For containerized deployments
- `appspec.yml` - For CodeDeploy deployments
- `scripts/*.sh` - Deployment scripts

## Customization

Edit `.github/workflows/ci.yml` to:
- Change Python versions to test
- Add more linting rules
- Customize test commands

Edit `.github/workflows/cd.yml` to:
- Change deployment method
- Add smoke tests
- Customize health checks

## Team Workflow

1. **Developer**: Create feature branch, make changes, push
2. **CI**: Automatically tests the changes
3. **Team**: Reviews code in PR
4. **Merge**: After approval and tests pass
5. **CD**: Automatically deploys to production
6. **Monitor**: Check AWS console and logs

Everyone can see test and deployment status in real-time!

---

**🎓 You're all set!** Your project now has professional-grade CI/CD. Happy coding! 🚀
