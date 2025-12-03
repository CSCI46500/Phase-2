#!/bin/bash
set -e

# Load config
source .env.aws

# Get AWS account ID
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "Creating frontend ECS service..."

# Get frontend repo URI
FRONTEND_REPO_URI=$(aws ecr describe-repositories \
    --repository-names ${ECR_FRONTEND_REPO} \
    --region ${AWS_REGION} \
    --query 'repositories[0].repositoryUri' \
    --output text)

# Get IAM role ARNs
EXECUTION_ROLE_ARN=$(aws iam get-role \
    --role-name ${PROJECT_NAME}-ecs-execution-role \
    --query 'Role.Arn' \
    --output text)

TASK_ROLE_ARN=$(aws iam get-role \
    --role-name ${PROJECT_NAME}-ecs-task-role \
    --query 'Role.Arn' \
    --output text)

# Get VPC and subnet info
VPC_ID=$(aws ec2 describe-vpcs \
    --filters "Name=isDefault,Values=true" \
    --query 'Vpcs[0].VpcId' \
    --output text)

SUBNET_IDS=$(aws ec2 describe-subnets \
    --filters "Name=vpc-id,Values=${VPC_ID}" \
    --query 'Subnets[0:2].SubnetId' \
    --output json)

# Get security group for ECS
ECS_SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=${PROJECT_NAME}-ecs-sg" \
    --query 'SecurityGroups[0].GroupId' \
    --output text)

# Get ALB ARN
ALB_ARN=$(aws elbv2 describe-load-balancers \
    --names ${PROJECT_NAME}-alb \
    --query 'LoadBalancers[0].LoadBalancerArn' \
    --output text)

echo "Frontend URI: $FRONTEND_REPO_URI"
echo "VPC ID: $VPC_ID"
echo "Security Group: $ECS_SG_ID"

# Create CloudWatch log group for frontend
if aws logs describe-log-groups --log-group-name-prefix "/ecs/${PROJECT_NAME}-frontend" 2>/dev/null | grep -q "logGroupName"; then
    echo "CloudWatch log group already exists"
else
    aws logs create-log-group --log-group-name /ecs/${PROJECT_NAME}-frontend
    aws logs put-retention-policy \
        --log-group-name /ecs/${PROJECT_NAME}-frontend \
        --retention-in-days 7
    echo "Created CloudWatch log group"
fi

# Create frontend target group
if aws elbv2 describe-target-groups --names ${PROJECT_NAME}-frontend-tg 2>/dev/null | grep -q "TargetGroupArn"; then
    echo "Frontend target group already exists"
    FRONTEND_TG_ARN=$(aws elbv2 describe-target-groups \
        --names ${PROJECT_NAME}-frontend-tg \
        --query 'TargetGroups[0].TargetGroupArn' \
        --output text)
else
    aws elbv2 create-target-group \
        --name ${PROJECT_NAME}-frontend-tg \
        --protocol HTTP \
        --port 80 \
        --vpc-id ${VPC_ID} \
        --target-type ip \
        --health-check-path / \
        --health-check-interval-seconds 30

    FRONTEND_TG_ARN=$(aws elbv2 describe-target-groups \
        --names ${PROJECT_NAME}-frontend-tg \
        --query 'TargetGroups[0].TargetGroupArn' \
        --output text)

    echo "Created frontend target group: $FRONTEND_TG_ARN"
fi

# Update ALB listener to use frontend as default and route /api to backend
BACKEND_TG_ARN=$(aws elbv2 describe-target-groups \
    --names ${PROJECT_NAME}-backend-tg \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text)

# Get existing listener ARN
LISTENER_ARN=$(aws elbv2 describe-listeners \
    --load-balancer-arn ${ALB_ARN} \
    --query 'Listeners[0].ListenerArn' \
    --output text)

echo "Updating ALB listener to route traffic..."

# Modify listener to default to frontend
aws elbv2 modify-listener \
    --listener-arn ${LISTENER_ARN} \
    --default-actions Type=forward,TargetGroupArn=${FRONTEND_TG_ARN}

# Create rules to route API paths to backend (split into multiple rules due to 5-path limit)
RULE1_EXISTS=$(aws elbv2 describe-rules \
    --listener-arn ${LISTENER_ARN} \
    --query "Rules[?Priority=='1'].Priority" \
    --output text)

if [ -z "$RULE1_EXISTS" ]; then
    aws elbv2 create-rule \
        --listener-arn ${LISTENER_ARN} \
        --priority 1 \
        --conditions Field=path-pattern,Values='/health','/docs','/openapi.json','/authenticate','/logs' \
        --actions Type=forward,TargetGroupArn=${BACKEND_TG_ARN}
    echo "Created ALB rule 1 to route API traffic to backend"
else
    echo "ALB rule 1 already exists"
fi

RULE2_EXISTS=$(aws elbv2 describe-rules \
    --listener-arn ${LISTENER_ARN} \
    --query "Rules[?Priority=='2'].Priority" \
    --output text)

if [ -z "$RULE2_EXISTS" ]; then
    aws elbv2 create-rule \
        --listener-arn ${LISTENER_ARN} \
        --priority 2 \
        --conditions Field=path-pattern,Values='/user/*','/package/*','/packages','/reset' \
        --actions Type=forward,TargetGroupArn=${BACKEND_TG_ARN}
    echo "Created ALB rule 2 to route API traffic to backend"
else
    echo "ALB rule 2 already exists"
fi

# Register frontend task definition
cat > /tmp/frontend-task-def.json <<EOF
{
  "family": "${PROJECT_NAME}-frontend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "${EXECUTION_ROLE_ARN}",
  "taskRoleArn": "${TASK_ROLE_ARN}",
  "containerDefinitions": [
    {
      "name": "frontend",
      "image": "${FRONTEND_REPO_URI}:latest",
      "portMappings": [{"containerPort": 80, "protocol": "tcp"}],
      "essential": true,
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/${PROJECT_NAME}-frontend",
          "awslogs-region": "${AWS_REGION}",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
EOF

aws ecs register-task-definition --cli-input-json file:///tmp/frontend-task-def.json
echo "Registered frontend task definition"

# Create or update frontend service
if aws ecs describe-services --cluster ${ECS_CLUSTER_NAME} --services ${ECS_FRONTEND_SERVICE} 2>/dev/null | grep -q "serviceName"; then
    echo "Updating existing frontend ECS service..."
    aws ecs update-service \
        --cluster ${ECS_CLUSTER_NAME} \
        --service ${ECS_FRONTEND_SERVICE} \
        --force-new-deployment
else
    echo "Creating frontend ECS service..."

    aws ecs create-service \
        --cluster ${ECS_CLUSTER_NAME} \
        --service-name ${ECS_FRONTEND_SERVICE} \
        --task-definition ${PROJECT_NAME}-frontend \
        --desired-count 1 \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=${SUBNET_IDS},securityGroups=[\"${ECS_SG_ID}\"],assignPublicIp=ENABLED}" \
        --load-balancers "targetGroupArn=${FRONTEND_TG_ARN},containerName=frontend,containerPort=80" \
        --health-check-grace-period-seconds 60
fi

echo "Waiting for service to stabilize..."
aws ecs wait services-stable --cluster ${ECS_CLUSTER_NAME} --services ${ECS_FRONTEND_SERVICE}

# Get ALB DNS
ALB_DNS=$(aws elbv2 describe-load-balancers \
    --names ${PROJECT_NAME}-alb \
    --query 'LoadBalancers[0].DNSName' \
    --output text)

echo ""
echo "=========================================="
echo "  Frontend Deployment Complete!"
echo "=========================================="
echo ""
echo "Frontend URL: http://${ALB_DNS}"
echo "Backend API: http://${ALB_DNS}/health"
echo "API Docs: http://${ALB_DNS}/docs"
echo ""
echo "Test your deployment:"
echo "  curl http://${ALB_DNS}"
echo ""
echo "=========================================="
