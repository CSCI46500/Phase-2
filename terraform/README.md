# Terraform Infrastructure

Infrastructure as Code for deploying Model Registry to AWS.

## Quick Start

```bash
# 1. Copy and configure variables
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your configuration

# 2. Initialize Terraform
terraform init

# 3. Review planned changes
terraform plan

# 4. Deploy infrastructure
terraform apply

# 5. View outputs
terraform output
```

## Resources Created

### Networking
- VPC with public and private subnets (2 AZs)
- Internet Gateway
- NAT Gateways (one per AZ)
- Route tables and associations
- Security groups for ALB, ECS, RDS, and Batch
- VPC endpoints for S3

### Compute
- ECS Cluster (Fargate)
- ECS Service for backend API (auto-scaling 2-10 tasks)
- Application Load Balancer
- AWS Batch compute environment (Fargate)
- AWS Batch job queue and definition

### Storage
- RDS PostgreSQL database (with encryption, backups, monitoring)
- S3 buckets:
  - Package storage
  - Frontend hosting
  - Log storage
- ECR repositories:
  - Backend container images
  - Autograder container images

### Content Delivery
- CloudFront distribution for frontend
- Origin Access Control for S3

### Monitoring
- CloudWatch log groups
- CloudWatch dashboard
- CloudWatch alarms for:
  - ECS metrics
  - RDS metrics
  - ALB metrics
  - Batch job failures

### Security
- IAM roles and policies
- Security groups
- Encrypted storage (RDS, S3)

## File Structure

```
terraform/
├── main.tf           # Provider and main configuration
├── variables.tf      # Input variables
├── outputs.tf        # Output values
├── vpc.tf            # VPC and networking
├── ecr.tf            # Container registries
├── rds.tf            # Database
├── s3.tf             # S3 buckets
├── iam.tf            # IAM roles and policies
├── ecs.tf            # ECS cluster and services
├── batch.tf          # AWS Batch configuration
├── cloudfront.tf     # CloudFront distribution
├── cloudwatch.tf     # Monitoring and logging
└── terraform.tfvars  # Your configuration (gitignored)
```

## Configuration

### Required Variables

```hcl
db_username = "admin"
db_password = "SecurePassword123!"
```

### Optional Variables

See `terraform.tfvars.example` for all available variables.

## State Management

### Local State (Default)

Terraform state is stored locally in `terraform.tfstate`.

**⚠️ Warning:** Not recommended for production or team environments.

### Remote State (Recommended)

Uncomment the backend configuration in `main.tf` after creating the S3 bucket and DynamoDB table:

```bash
# Create resources
aws s3api create-bucket --bucket model-registry-terraform-state --region us-east-1
aws s3api put-bucket-versioning --bucket model-registry-terraform-state --versioning-configuration Status=Enabled

aws dynamodb create-table \
  --table-name terraform-state-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

# Then uncomment backend block in main.tf and run:
terraform init -migrate-state
```

## Outputs

Key outputs after deployment:

```bash
# API endpoint
terraform output alb_dns_name

# Frontend URL
terraform output frontend_url

# ECR repository URLs
terraform output ecr_repositories

# Database endpoint
terraform output rds_endpoint

# CloudWatch dashboard
terraform output cloudwatch_dashboard_url
```

## Cost Estimation

Approximate monthly costs (us-east-1, current configuration):

| Service | Configuration | Monthly Cost |
|---------|--------------|--------------|
| ECS Fargate | 2 tasks (0.5vCPU, 1GB) | $50-70 |
| RDS PostgreSQL | db.t3.micro | $15-20 |
| Application Load Balancer | - | $20-25 |
| NAT Gateway | 2 AZs | $64 |
| S3 | Depends on usage | $5-10 |
| CloudFront | Depends on traffic | $5-10 |
| **Total** | | **$160-200** |

### Cost Optimization

- **NAT Gateway:** Use single NAT Gateway instead of 2 (reduces by $32/month, but loses HA)
- **RDS:** db.t3.micro is already the smallest option
- **ECS:** Reduce to 1 min task (not recommended for production)
- **S3:** Use Intelligent-Tiering for automatic optimization

## Security Considerations

### Secrets Management

**Current:** Database credentials in `terraform.tfvars` (gitignored)

**Production recommendation:** Use AWS Secrets Manager

```hcl
# Add to rds.tf
resource "aws_secretsmanager_secret" "db_password" {
  name = "${local.name_prefix}-db-password"
}

# Reference in RDS resource
password = data.aws_secretsmanager_secret_version.db_password.secret_string
```

### HTTPS

**Current:** ALB uses HTTP only

**Production requirement:** Add ACM certificate and HTTPS listener

1. Request certificate in ACM
2. Uncomment HTTPS listener in `ecs.tf`
3. Update ALB HTTP listener to redirect to HTTPS

### Custom Domain

1. Create hosted zone in Route 53
2. Add ACM certificate
3. Add CloudFront aliases
4. Update CORS configuration

## Troubleshooting

### Terraform Init Fails

```bash
# Clear cache and reinitialize
rm -rf .terraform .terraform.lock.hcl
terraform init
```

### Apply Fails - Resource Already Exists

```bash
# Import existing resource (example for ECR)
terraform import aws_ecr_repository.backend model-registry-prod-backend
```

### RDS Creation Timeout

RDS can take 10-15 minutes to create. If it times out:
- Check AWS console for actual status
- Increase timeout in `rds.tf` if needed

### Can't Delete Resources

Some resources have deletion protection:
- RDS: `deletion_protection = true`
- ALB: `enable_deletion_protection = true`

Set these to `false` in `variables.tf` before destroying.

## Maintenance

### Updating Infrastructure

```bash
# Review changes
terraform plan

# Apply updates
terraform apply
```

### Updating Task Definitions

When you push new Docker images, ECS won't automatically update. Either:

1. Update task definition in `ecs.tf` (change image tag)
2. Force new deployment via AWS CLI:
   ```bash
   aws ecs update-service --cluster <cluster> --service <service> --force-new-deployment
   ```

### Database Migrations

Migrations run automatically on ECS task startup. To run manually:

```bash
aws ecs execute-command \
  --cluster model-registry-prod-cluster \
  --task <task-id> \
  --container backend \
  --interactive \
  --command "/bin/bash"
```

## Destroying Infrastructure

⚠️ **WARNING:** This will delete all data!

```bash
# 1. Disable deletion protection
# Edit variables.tf: enable_deletion_protection = false
terraform apply

# 2. Delete ECR images (required before destroying)
aws ecr batch-delete-image \
  --repository-name model-registry-prod-backend \
  --image-ids imageTag=latest

aws ecr batch-delete-image \
  --repository-name model-registry-prod-autograder \
  --image-ids imageTag=latest

# 3. Destroy infrastructure
terraform destroy
```

## Additional Resources

- [Terraform AWS Provider Docs](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [AWS Batch Documentation](https://docs.aws.amazon.com/batch/)
