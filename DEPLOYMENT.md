# 🚀 Deployment Guide

Quick reference for deploying the Model Registry to different environments.

## 📍 Choose Your Deployment

### Local Development (Docker Compose)
**Best for:** Development, testing, local demos

```bash
# Start all services
docker compose up -d

# Access API
http://localhost:8000

# Access Frontend
http://localhost:5173
```

**See:** `README.md` for full local setup instructions

---

### AWS Production Deployment (Recommended)
**Best for:** Production, autograder submission, team demos

```bash
# Quick setup
./scripts/setup-aws-env.sh    # Configure environment
./scripts/deploy-to-aws.sh    # Deploy to AWS (~30 min)

# Or manual setup
cp .env.aws.template .env.aws  # Configure manually
./scripts/deploy-to-aws.sh     # Deploy
```

**Access:** `http://your-alb-dns-here` (provided after deployment)

**See:**
- `docs/AWS_QUICK_START.md` - Fast deployment guide
- `README_AWS.md` - Full AWS documentation
- `AWS_DEPLOYMENT_SUMMARY.md` - Quick reference

---

## 🎯 For This Project (Phase 2)

**You need AWS deployment** because:
- ✅ Project requires 2+ AWS components (we use 7)
- ✅ Autograder needs a public URL
- ✅ Demonstrates production deployment skills
- ✅ Shows CI/CD integration

## 📋 Quick Comparison

| Feature | Local (Docker Compose) | AWS (Production) |
|---------|----------------------|------------------|
| **Setup Time** | 5 minutes | 30 minutes |
| **Cost** | Free | ~$35/month |
| **Access** | localhost only | Public URL |
| **Services** | PostgreSQL, MinIO | 7 AWS services |
| **CI/CD** | Manual | Automated |
| **For Autograder** | ❌ No | ✅ Yes |
| **For Development** | ✅ Yes | Limited |

## 🚦 Getting Started

### Option 1: Local Development First (Recommended)

Good for testing before AWS deployment:

```bash
# 1. Start locally
docker compose up -d

# 2. Test endpoints
curl http://localhost:8000/health

# 3. Run tests
docker compose exec api pytest

# 4. When ready, deploy to AWS
./scripts/setup-aws-env.sh
./scripts/deploy-to-aws.sh
```

### Option 2: Direct to AWS

Skip local testing, go straight to production:

```bash
# 1. Set up AWS credentials
aws configure

# 2. Set up environment (automated)
./scripts/setup-aws-env.sh

# 3. Deploy
./scripts/deploy-to-aws.sh

# 4. Test
curl http://your-alb-dns/health
```

## 📚 Documentation Index

| Document | Purpose | When to Use |
|----------|---------|-------------|
| `README.md` | Local Docker development | Setting up dev environment |
| `README_AWS.md` | AWS deployment overview | Understanding AWS architecture |
| `docs/AWS_QUICK_START.md` | Fast AWS deployment | Deploying to AWS quickly |
| `docs/AWS_DEPLOYMENT_GUIDE.md` | Detailed AWS guide | Step-by-step AWS setup |
| `AWS_DEPLOYMENT_SUMMARY.md` | Quick reference | Looking up commands/checklists |
| `DEPLOYMENT.md` (this file) | Deployment overview | Choosing deployment method |

## ⚡ Ultra Quick Start

**Already have AWS configured?**

```bash
./scripts/setup-aws-env.sh && ./scripts/deploy-to-aws.sh
```

That's it! Wait 30 minutes, get your URL, submit to autograder.

## 🆘 Need Help?

**Local deployment issues:**
- See: `README.md` → "Troubleshooting" section
- Check: Docker is running
- Run: `docker compose logs api`

**AWS deployment issues:**
- See: `README_AWS.md` → "Troubleshooting" section
- Check: AWS credentials configured
- Run: `aws sts get-caller-identity`

**General questions:**
- Start with: `docs/AWS_QUICK_START.md`
- Then: `README_AWS.md`
- Finally: `docs/AWS_DEPLOYMENT_GUIDE.md`

## 🎯 For Autograder Submission

You need:
1. ✅ AWS deployment (not local)
2. ✅ Public URL from Application Load Balancer
3. ✅ Default admin user configured (automatically set)

Get your URL:
```bash
aws elbv2 describe-load-balancers \
  --names model-registry-alb \
  --query 'LoadBalancers[0].DNSName' \
  --output text
```

Test before submitting:
```bash
export API_URL=http://your-alb-dns-here
curl $API_URL/health
curl -X POST $API_URL/authenticate \
  -H "Content-Type: application/json" \
  -d '{"username":"ece30861defaultadminuser","password":"correcthorsebatterystaple123(!__+@**(A;DROP TABLE packages"}'
```

---

**Ready to deploy?** Choose your path above and follow the links!
