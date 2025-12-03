#!/bin/bash
set -e

# Quick fix: Route all ALB traffic to backend for autograder

echo "Getting ALB and target group info..."

ALB_ARN=$(aws elbv2 describe-load-balancers --names model-registry-alb --query 'LoadBalancers[0].LoadBalancerArn' --output text --region us-east-1)
LISTENER_ARN=$(aws elbv2 describe-listeners --load-balancer-arn $ALB_ARN --query 'Listeners[0].ListenerArn' --output text --region us-east-1)
BACKEND_TG=$(aws elbv2 describe-target-groups --names model-registry-backend-tg --query 'TargetGroups[0].TargetGroupArn' --output text --region us-east-1)

echo "ALB ARN: $ALB_ARN"
echo "Listener ARN: $LISTENER_ARN"
echo "Backend Target Group: $BACKEND_TG"

echo ""
echo "Routing all traffic to backend..."

aws elbv2 modify-listener --listener-arn $LISTENER_ARN --default-actions Type=forward,TargetGroupArn=$BACKEND_TG --region us-east-1

echo ""
echo "Done! Testing /tracks endpoint..."
sleep 2

curl http://model-registry-alb-555572374.us-east-1.elb.amazonaws.com/tracks

echo ""
echo ""
echo "If you see JSON above, it worked!"
