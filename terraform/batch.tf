# AWS Batch for Package Autograder/Scoring

# CloudWatch Log Group for Batch
resource "aws_cloudwatch_log_group" "batch" {
  name              = "/aws/batch/${local.name_prefix}"
  retention_in_days = 30

  tags = local.common_tags
}

# Batch Compute Environment
resource "aws_batch_compute_environment" "autograder" {
  compute_environment_name = "${local.name_prefix}-autograder-compute"
  type                     = "MANAGED"
  service_role             = aws_iam_role.batch_service.arn

  compute_resources {
    type               = "FARGATE"
    max_vcpus          = 16
    security_group_ids = [aws_security_group.batch.id]
    subnets            = aws_subnet.private[*].id
  }

  tags = local.common_tags

  depends_on = [aws_iam_role_policy_attachment.batch_service]
}

# Batch Job Queue
resource "aws_batch_job_queue" "autograder" {
  name     = "${local.name_prefix}-autograder-queue"
  state    = "ENABLED"
  priority = 1

  compute_environment_order {
    order               = 1
    compute_environment = aws_batch_compute_environment.autograder.arn
  }

  tags = local.common_tags
}

# Batch Job Definition for Package Autograding
resource "aws_batch_job_definition" "autograder" {
  name = "${local.name_prefix}-autograder-job"
  type = "container"

  platform_capabilities = ["FARGATE"]

  container_properties = jsonencode({
    image = "${aws_ecr_repository.autograder.repository_url}:latest"

    fargatePlatformConfiguration = {
      platformVersion = "LATEST"
    }

    resourceRequirements = [
      {
        type  = "VCPU"
        value = tostring(var.autograder_cpu / 1024)
      },
      {
        type  = "MEMORY"
        value = tostring(var.autograder_memory)
      }
    ]

    jobRoleArn      = aws_iam_role.batch_job.arn
    executionRoleArn = aws_iam_role.ecs_task_execution.arn

    environment = [
      {
        name  = "S3_BUCKET_NAME"
        value = aws_s3_bucket.packages.bucket
      },
      {
        name  = "AWS_REGION"
        value = var.aws_region
      },
      {
        name  = "ENVIRONMENT"
        value = var.environment
      },
      {
        name  = "DATABASE_URL"
        value = "postgresql://${var.db_username}:${var.db_password}@${aws_db_instance.main.endpoint}/${var.db_name}"
      }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.batch.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "autograder"
      }
    }

    networkConfiguration = {
      assignPublicIp = "DISABLED"
    }

    # Security: Resource limits for untrusted code execution
    linuxParameters = {
      maxSwap = 0
      swappiness = 0
    }
  })

  retry_strategy {
    attempts = 3
    evaluate_on_exit {
      action       = "RETRY"
      on_status_reason = "Task failed to start"
    }
  }

  timeout {
    attempt_duration_seconds = 900 # 15 minutes max per job
  }

  tags = local.common_tags
}

# EventBridge Rule to monitor Batch job failures
resource "aws_cloudwatch_event_rule" "batch_job_failed" {
  name        = "${local.name_prefix}-batch-job-failed"
  description = "Trigger on Batch job failures"

  event_pattern = jsonencode({
    source      = ["aws.batch"]
    detail-type = ["Batch Job State Change"]
    detail = {
      status    = ["FAILED"]
      jobQueue  = [aws_batch_job_queue.autograder.arn]
    }
  })

  tags = local.common_tags
}

# CloudWatch Log Metric Filter for Batch errors
resource "aws_cloudwatch_log_metric_filter" "batch_errors" {
  name           = "${local.name_prefix}-batch-errors"
  log_group_name = aws_cloudwatch_log_group.batch.name
  pattern        = "[ERROR]"

  metric_transformation {
    name      = "BatchErrors"
    namespace = "${var.project_name}/${var.environment}"
    value     = "1"
    default_value = 0
  }
}

# CloudWatch Alarm for Batch errors
resource "aws_cloudwatch_metric_alarm" "batch_errors" {
  alarm_name          = "${local.name_prefix}-batch-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "BatchErrors"
  namespace           = "${var.project_name}/${var.environment}"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "This metric monitors batch job errors"
  treat_missing_data  = "notBreaching"

  tags = local.common_tags
}

# Outputs
output "batch_job_queue_arn" {
  description = "ARN of the Batch job queue"
  value       = aws_batch_job_queue.autograder.arn
}

output "batch_job_definition_arn" {
  description = "ARN of the Batch job definition"
  value       = aws_batch_job_definition.autograder.arn
}