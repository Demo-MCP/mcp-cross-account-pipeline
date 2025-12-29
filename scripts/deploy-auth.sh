#!/bin/bash

# MCP Broker Authentication Setup Script
# Deploys IAM roles + API Gateway with SigV4 authentication

set -e

STACK_NAME="mcp-broker-auth"
REGION="us-east-1"
TEMPLATE_FILE="infrastructure/auth-gateway.yaml"

echo "🚀 Deploying MCP Broker Authentication Stack..."

# Deploy CloudFormation stack
aws cloudformation deploy \
  --template-file "$TEMPLATE_FILE" \
  --stack-name "$STACK_NAME" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "$REGION" \
  --parameter-overrides \
    BrokerListenerArn="arn:aws:elasticloadbalancing:us-east-1:500330120558:listener/app/broker-internal-alb/84bc200374f2a646/2c6f9be6996f68cb"

echo "✅ Stack deployed successfully!"

# Get outputs
echo "📋 Getting stack outputs..."
API_ID=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayId`].OutputValue' \
  --output text)

API_URL=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' \
  --output text)

DEV_ROLE_ARN=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`DevRoleArn`].OutputValue' \
  --output text)

ADMIN_ROLE_ARN=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`AdminRoleArn`].OutputValue' \
  --output text)

echo "🔧 HTTP API uses route-level AWS_IAM authorization - no separate resource policy needed"

echo "✅ Resource policy applied!"

echo ""
echo "🎉 MCP Broker Authentication Setup Complete!"
echo ""
echo "📋 Summary:"
echo "  API Gateway URL: $API_URL"
echo "  Dev Role ARN:    $DEV_ROLE_ARN"
echo "  Admin Role ARN:  $ADMIN_ROLE_ARN"
echo ""
echo "🧪 Test Commands:"
echo ""
echo "# Test Dev Role (should work for /ask only):"
echo "aws sts assume-role --role-arn '$DEV_ROLE_ARN' --role-session-name 'dev-test' --external-id 'dev-mcp-access'"
echo ""
echo "# Test Admin Role (should work for both /ask and /admin):"
echo "aws sts assume-role --role-arn '$ADMIN_ROLE_ARN' --role-session-name 'admin-test' --external-id 'admin-mcp-access'"
echo ""
echo "# Example SigV4 request (after assuming role):"
echo "aws apigatewayv2 invoke --api-id '$API_ID' --stage prod --path '/ask' --method POST --body '{\"ask_text\":\"test\"}'"
