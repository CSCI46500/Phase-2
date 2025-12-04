#!/bin/bash
# Fix ALB routing to ensure proper backend/frontend routing

set -e

# Load configuration
source .env.aws

echo "Fixing ALB routing rules..."

# Get listener ARN
LISTENER_ARN=$(aws elbv2 describe-listeners \
    --load-balancer-arn $(aws elbv2 describe-load-balancers --names ${PROJECT_NAME}-alb --query 'LoadBalancers[0].LoadBalancerArn' --output text) \
    --query 'Listeners[0].ListenerArn' \
    --output text)

# Get target group ARNs
BACKEND_TG_ARN=$(aws elbv2 describe-target-groups \
    --names ${PROJECT_NAME}-backend-tg \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text)

FRONTEND_TG_ARN=$(aws elbv2 describe-target-groups \
    --names ${PROJECT_NAME}-frontend-tg \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text)

echo "Listener: $LISTENER_ARN"
echo "Backend TG: $BACKEND_TG_ARN"
echo "Frontend TG: $FRONTEND_TG_ARN"

# Delete all existing rules except default
echo "Removing old routing rules..."
RULE_ARNS=$(aws elbv2 describe-rules --listener-arn $LISTENER_ARN --query 'Rules[?Priority!=`default`].RuleArn' --output text)
for RULE_ARN in $RULE_ARNS; do
    echo "  Deleting rule: $RULE_ARN"
    aws elbv2 delete-rule --rule-arn $RULE_ARN 2>/dev/null || true
done

# Create new rules with proper path patterns
echo "Creating new routing rules..."

# Rule 1: /api/* → backend
aws elbv2 create-rule \
    --listener-arn $LISTENER_ARN \
    --priority 1 \
    --conditions Field=path-pattern,Values='/api/*' \
    --actions Type=forward,TargetGroupArn=$BACKEND_TG_ARN
echo "✅ Rule 1: /api/* → backend"

# Rule 2: /authenticate → backend
aws elbv2 create-rule \
    --listener-arn $LISTENER_ARN \
    --priority 2 \
    --conditions Field=path-pattern,Values='/authenticate' \
    --actions Type=forward,TargetGroupArn=$BACKEND_TG_ARN
echo "✅ Rule 2: /authenticate → backend"

# Rule 3: /tracks → backend
aws elbv2 create-rule \
    --listener-arn $LISTENER_ARN \
    --priority 3 \
    --conditions Field=path-pattern,Values='/tracks' \
    --actions Type=forward,TargetGroupArn=$BACKEND_TG_ARN
echo "✅ Rule 3: /tracks → backend"

# Rule 4: /health → backend
aws elbv2 create-rule \
    --listener-arn $LISTENER_ARN \
    --priority 4 \
    --conditions Field=path-pattern,Values='/health' \
    --actions Type=forward,TargetGroupArn=$BACKEND_TG_ARN
echo "✅ Rule 4: /health → backend"

# Rule 5: /packages → backend (POST requests for search)
aws elbv2 create-rule \
    --listener-arn $LISTENER_ARN \
    --priority 5 \
    --conditions Field=path-pattern,Values='/packages' \
    --actions Type=forward,TargetGroupArn=$BACKEND_TG_ARN
echo "✅ Rule 5: /packages → backend"

# Rule 6: /package/* → backend (all package operations)
aws elbv2 create-rule \
    --listener-arn $LISTENER_ARN \
    --priority 6 \
    --conditions Field=path-pattern,Values='/package/*' \
    --actions Type=forward,TargetGroupArn=$BACKEND_TG_ARN
echo "✅ Rule 6: /package/* → backend"

# Rule 7: /reset → backend
aws elbv2 create-rule \
    --listener-arn $LISTENER_ARN \
    --priority 7 \
    --conditions Field=path-pattern,Values='/reset' \
    --actions Type=forward,TargetGroupArn=$BACKEND_TG_ARN
echo "✅ Rule 7: /reset → backend"

# Rule 8: /logs → backend
aws elbv2 create-rule \
    --listener-arn $LISTENER_ARN \
    --priority 8 \
    --conditions Field=path-pattern,Values='/logs' \
    --actions Type=forward,TargetGroupArn=$BACKEND_TG_ARN
echo "✅ Rule 8: /logs → backend"

# Rule 9: /user/* → backend
aws elbv2 create-rule \
    --listener-arn $LISTENER_ARN \
    --priority 9 \
    --conditions Field=path-pattern,Values='/user/*' \
    --actions Type=forward,TargetGroupArn=$BACKEND_TG_ARN
echo "✅ Rule 9: /user/* → backend"

# Rule 10: /docs → backend (OpenAPI docs)
aws elbv2 create-rule \
    --listener-arn $LISTENER_ARN \
    --priority 10 \
    --conditions Field=path-pattern,Values='/docs' \
    --actions Type=forward,TargetGroupArn=$BACKEND_TG_ARN
echo "✅ Rule 10: /docs → backend"

# Rule 11: /openapi.json → backend
aws elbv2 create-rule \
    --listener-arn $LISTENER_ARN \
    --priority 11 \
    --conditions Field=path-pattern,Values='/openapi.json' \
    --actions Type=forward,TargetGroupArn=$BACKEND_TG_ARN
echo "✅ Rule 11: /openapi.json → backend"

# Update default action to frontend
echo "Setting default action to frontend..."
aws elbv2 modify-listener \
    --listener-arn $LISTENER_ARN \
    --default-actions Type=forward,TargetGroupArn=$FRONTEND_TG_ARN
echo "✅ Default: /* → frontend"

echo ""
echo "=========================================="
echo "✅ ALB routing fixed successfully!"
echo "=========================================="
echo ""
echo "Test the endpoints:"
echo "  Frontend: curl http://model-registry-alb-555572374.us-east-1.elb.amazonaws.com/"
echo "  Health:   curl http://model-registry-alb-555572374.us-east-1.elb.amazonaws.com/health"
echo "  Tracks:   curl http://model-registry-alb-555572374.us-east-1.elb.amazonaws.com/tracks"
echo ""
