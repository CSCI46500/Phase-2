#!/bin/bash
set -e

# Quick script to fix ALB listener rules for existing deployment

echo "Fixing ALB listener rules..."

# Load config
source .env.aws

# Get ALB ARN
ALB_ARN=$(aws elbv2 describe-load-balancers --names ${PROJECT_NAME}-alb --query 'LoadBalancers[0].LoadBalancerArn' --output text 2>/dev/null)
if [ -z "$ALB_ARN" ] || [ "$ALB_ARN" == "None" ]; then
    echo "Error: ALB not found"
    exit 1
fi

echo "Found ALB: $ALB_ARN"

# Get listener ARN
LISTENER_ARN=$(aws elbv2 describe-listeners --load-balancer-arn ${ALB_ARN} --query 'Listeners[0].ListenerArn' --output text 2>/dev/null)
echo "Found Listener: $LISTENER_ARN"

# Get target group ARNs
BACKEND_TG_ARN=$(aws elbv2 describe-target-groups --names ${PROJECT_NAME}-backend-tg --query 'TargetGroups[0].TargetGroupArn' --output text 2>/dev/null)
FRONTEND_TG_ARN=$(aws elbv2 describe-target-groups --names ${PROJECT_NAME}-frontend-tg --query 'TargetGroups[0].TargetGroupArn' --output text 2>/dev/null)

echo "Backend TG: $BACKEND_TG_ARN"
echo "Frontend TG: $FRONTEND_TG_ARN"

# Get all existing rules
echo ""
echo "Current listener rules:"
aws elbv2 describe-rules --listener-arn ${LISTENER_ARN} --query 'Rules[].[Priority,Conditions[].Values[],Actions[].TargetGroupArn]' --output table

# Update default action to forward to frontend
echo ""
echo "Updating default action to forward to frontend..."
aws elbv2 modify-listener \
    --listener-arn ${LISTENER_ARN} \
    --default-actions Type=forward,TargetGroupArn=${FRONTEND_TG_ARN}

echo ""
echo "ALB listener rules fixed successfully!"
echo "The ALB now routes:"
echo "  - API endpoints (/api/*, /authenticate, /tracks, etc.) → Backend"
echo "  - Everything else (/) → Frontend"
