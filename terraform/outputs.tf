# Consolidated Terraform Outputs

# Networking
output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "private_subnet_ids" {
  description = "IDs of private subnets"
  value       = aws_subnet.private[*].id
}

output "public_subnet_ids" {
  description = "IDs of public subnets"
  value       = aws_subnet.public[*].id
}

# Application URLs
output "api_url" {
  description = "URL of the backend API (via ALB)"
  value       = "http://${aws_lb.main.dns_name}"
}

output "frontend_url_summary" {
  description = "Frontend application URL"
  value       = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}

# ECR
output "ecr_repositories" {
  description = "ECR repository URLs"
  value = {
    backend    = aws_ecr_repository.backend.repository_url
    autograder = aws_ecr_repository.autograder.repository_url
  }
}

# ECS
output "ecs_cluster_info" {
  description = "ECS cluster information"
  value = {
    cluster_name = aws_ecs_cluster.main.name
    cluster_arn  = aws_ecs_cluster.main.arn
    service_name = aws_ecs_service.backend.name
  }
}

# Batch
output "batch_info" {
  description = "AWS Batch information"
  value = {
    job_queue_arn      = aws_batch_job_queue.autograder.arn
    job_definition_arn = aws_batch_job_definition.autograder.arn
  }
}

# S3
output "s3_buckets" {
  description = "S3 bucket names"
  value = {
    packages = aws_s3_bucket.packages.bucket
    frontend = aws_s3_bucket.frontend.bucket
    logs     = aws_s3_bucket.logs.bucket
  }
}

# Database
output "database_info" {
  description = "Database connection information"
  value = {
    endpoint      = aws_db_instance.main.endpoint
    database_name = aws_db_instance.main.db_name
    port          = aws_db_instance.main.port
  }
  sensitive = true
}

# CloudWatch
output "monitoring" {
  description = "Monitoring resources"
  value = {
    dashboard_url      = "https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
    ecs_log_group      = aws_cloudwatch_log_group.ecs.name
    batch_log_group    = aws_cloudwatch_log_group.batch.name
  }
}

# Deployment Information
output "deployment_summary" {
  description = "Summary of deployed resources"
  value = <<-EOT

    ========================================
    AWS Deployment Summary
    ========================================

    Frontend URL: https://${aws_cloudfront_distribution.frontend.domain_name}
    Backend API: http://${aws_lb.main.dns_name}

    ECR Repositories:
      Backend: ${aws_ecr_repository.backend.repository_url}
      Autograder: ${aws_ecr_repository.autograder.repository_url}

    ECS Cluster: ${aws_ecs_cluster.main.name}
    ECS Service: ${aws_ecs_service.backend.name}

    Batch Job Queue: ${aws_batch_job_queue.autograder.name}

    S3 Buckets:
      Packages: ${aws_s3_bucket.packages.bucket}
      Frontend: ${aws_s3_bucket.frontend.bucket}
      Logs: ${aws_s3_bucket.logs.bucket}

    CloudWatch Dashboard:
      https://console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}

    ========================================
  EOT
}