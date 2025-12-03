#!/bin/bash
set -e

echo "==== Deployment Diagnostics ===="
echo ""

# Test the endpoint
echo "1. Testing /tracks endpoint..."
curl -s http://model-registry-alb-555572374.us-east-1.elb.amazonaws.com/tracks | head -20
echo ""
echo ""

# Check backend target health
echo "2. Checking backend target health..."
aws elbv2 describe-target-health \
    --target-group-arn arn:aws:elasticloadbalancing:us-east-1:187641964754:targetgroup/model-registry-backend-tg/bce3571e097b4455 \
    --region us-east-1 \
    --query 'TargetHealthDescriptions[*].[Target.Id,TargetHealth.State,TargetHealth.Reason]' \
    --output table

echo ""

# Check if backend service is running
echo "3. Checking backend ECS service..."
aws ecs describe-services \
    --cluster model-registry-cluster \
    --services model-registry-backend-service \
    --region us-east-1 \
    --query 'services[0].[serviceName,status,runningCount,desiredCount]' \
    --output table

echo ""

# Check backend tasks
echo "4. Checking backend tasks..."
aws ecs list-tasks \
    --cluster model-registry-cluster \
    --service-name model-registry-backend-service \
    --region us-east-1 \
    --query 'taskArns' \
    --output table

echo ""

# Check listener default action
echo "5. Checking ALB listener configuration..."
aws elbv2 describe-listeners \
    --listener-arns arn:aws:elasticloadbalancing:us-east-1:187641964754:listener/app/model-registry-alb/3b269dd8ba4a5a33/f93706cab57c760b \
    --region us-east-1 \
    --query 'Listeners[0].DefaultActions[0].TargetGroupArn' \
    --output text

echo ""
echo "Expected backend TG: arn:aws:elasticloadbalancing:us-east-1:187641964754:targetgroup/model-registry-backend-tg/bce3571e097b4455"
