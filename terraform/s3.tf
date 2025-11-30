# S3 Buckets for package storage and frontend hosting

# S3 Bucket for Package Storage
resource "aws_s3_bucket" "packages" {
  bucket = "${local.name_prefix}-packages-${local.account_id}"

  tags = merge(
    local.common_tags,
    {
      Name    = "${local.name_prefix}-packages"
      Purpose = "PackageStorage"
    }
  )
}

# Enable versioning for package bucket
resource "aws_s3_bucket_versioning" "packages" {
  bucket = aws_s3_bucket.packages.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Enable encryption for package bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "packages" {
  bucket = aws_s3_bucket.packages.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block public access for package bucket
resource "aws_s3_bucket_public_access_block" "packages" {
  bucket = aws_s3_bucket.packages.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle policy for package bucket
resource "aws_s3_bucket_lifecycle_configuration" "packages" {
  bucket = aws_s3_bucket.packages.id

  rule {
    id     = "delete-old-versions"
    status = "Enabled"

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }

  rule {
    id     = "abort-incomplete-multipart-uploads"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# CORS configuration for package bucket
resource "aws_s3_bucket_cors_configuration" "packages" {
  bucket = aws_s3_bucket.packages.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST", "DELETE", "HEAD"]
    allowed_origins = ["*"] # Update with specific origins in production
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

# S3 Bucket for Frontend Hosting
resource "aws_s3_bucket" "frontend" {
  bucket = "${local.name_prefix}-frontend-${local.account_id}"

  tags = merge(
    local.common_tags,
    {
      Name    = "${local.name_prefix}-frontend"
      Purpose = "FrontendHosting"
    }
  )
}

# Enable encryption for frontend bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Public access for frontend bucket (served through CloudFront)
resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Bucket policy for CloudFront OAC
resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontServicePrincipal"
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.frontend.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.frontend.arn
          }
        }
      }
    ]
  })

  depends_on = [aws_cloudfront_distribution.frontend]
}

# S3 Bucket for CloudWatch Logs (long-term storage)
resource "aws_s3_bucket" "logs" {
  bucket = "${local.name_prefix}-logs-${local.account_id}"

  tags = merge(
    local.common_tags,
    {
      Name    = "${local.name_prefix}-logs"
      Purpose = "LogStorage"
    }
  )
}

# Enable encryption for logs bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block public access for logs bucket
resource "aws_s3_bucket_public_access_block" "logs" {
  bucket = aws_s3_bucket.logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle policy for logs bucket
resource "aws_s3_bucket_lifecycle_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    id     = "transition-to-glacier"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 365
    }
  }
}

# Outputs
output "s3_packages_bucket_name" {
  description = "Name of the S3 bucket for packages"
  value       = aws_s3_bucket.packages.bucket
}

output "s3_frontend_bucket_name" {
  description = "Name of the S3 bucket for frontend"
  value       = aws_s3_bucket.frontend.bucket
}

output "s3_logs_bucket_name" {
  description = "Name of the S3 bucket for logs"
  value       = aws_s3_bucket.logs.bucket
}
