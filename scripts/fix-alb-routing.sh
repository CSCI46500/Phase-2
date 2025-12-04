#!/bin/bash
# Fix ALB routing to ensure frontend is the default target

set -e

# Load configuration
source .env.aws

# Get listener ARN
LISTENER_ARN=$(aws elbv2 describe-listeners \
    --load-balancer-arn $(aws elbv2 describe-load-balancers --names ${PROJECT_NAME}-alb --query 'LoadBalancers[0].LoadBalancerArn' --output text) \
    --query 'Listeners[0].ListenerArn' \
    --output text)

# Get target group ARNs
FRONTEND_TG_ARN=$(aws elbv2 describe-target-groups \
    --names ${PROJECT_NAME}-frontend-tg \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text)

echo "Updating listener default action to forward to frontend..."

# Update the listener's default action to point to frontend
aws elbv2 modify-listener \
    --listener-arn $LISTENER_ARN \
    --default-actions Type=forward,TargetGroupArn=$FRONTEND_TG_ARN

echo "✅ ALB routing fixed! Frontend should now be accessible at /"
echo "Test with: curl http://model-registry-alb-555572374.us-east-1.elb.amazonaws.com/"
