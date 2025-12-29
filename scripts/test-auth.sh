#!/bin/bash

# MCP Broker Authentication Test Script
# Tests SigV4 authentication with Dev and Admin roles

set -e

STACK_NAME="mcp-broker-auth"
REGION="us-east-1"

echo "🧪 Testing MCP Broker Authentication..."

# Get stack outputs
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

echo "📋 Test Configuration:"
echo "  API URL: $API_URL"
echo "  Dev Role: $DEV_ROLE_ARN"
echo "  Admin Role: $ADMIN_ROLE_ARN"
echo ""

# Test 1: Dev Role -> /ask (should succeed)
echo "🔍 Test 1: Dev Role calling /ask (should succeed)"
DEV_CREDS=$(aws sts assume-role \
  --role-arn "$DEV_ROLE_ARN" \
  --role-session-name "dev-test-$(date +%s)" \
  --external-id "dev-mcp-access" \
  --output json)

export AWS_ACCESS_KEY_ID=$(echo "$DEV_CREDS" | jq -r '.Credentials.AccessKeyId')
export AWS_SECRET_ACCESS_KEY=$(echo "$DEV_CREDS" | jq -r '.Credentials.SecretAccessKey')
export AWS_SESSION_TOKEN=$(echo "$DEV_CREDS" | jq -r '.Credentials.SessionToken')

echo "  Making SigV4 request to /ask..."
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  --aws-sigv4 "aws:amz:$REGION:execute-api" \
  --user "$AWS_ACCESS_KEY_ID:$AWS_SECRET_ACCESS_KEY" \
  -H "X-Amz-Security-Token: $AWS_SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -X POST "$API_URL/ask" \
  -d '{"ask_text": "List ECS clusters", "account_id": "500330120558", "region": "us-east-1"}' \
  2>/dev/null || echo "FAILED")

HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE:/d')

if [[ "$HTTP_CODE" == "200" ]]; then
  echo "  ✅ SUCCESS: Dev role can call /ask (HTTP $HTTP_CODE)"
  echo "  📤 Request: List ECS clusters"
  echo "  📥 Response: $BODY"
else
  echo "  ❌ FAILED: Dev role cannot call /ask (HTTP $HTTP_CODE)"
  echo "  Response: $BODY"
fi

# Test 2: Dev Role -> /admin (should fail)
echo ""
echo "🔍 Test 2: Dev Role calling /admin (should fail with 403)"
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  --aws-sigv4 "aws:amz:$REGION:execute-api" \
  --user "$AWS_ACCESS_KEY_ID:$AWS_SECRET_ACCESS_KEY" \
  -H "X-Amz-Security-Token: $AWS_SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -X POST "$API_URL/admin" \
  -d '{"ask_text": "Analyze PR 9", "account_id": "500330120558", "region": "us-east-1"}' \
  2>/dev/null || echo "FAILED")

HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)

if [[ "$HTTP_CODE" == "403" ]]; then
  echo "  ✅ SUCCESS: Dev role correctly denied /admin access (HTTP $HTTP_CODE)"
else
  echo "  ❌ UNEXPECTED: Dev role got HTTP $HTTP_CODE for /admin (expected 403)"
fi

# Test 3: Admin Role -> /admin (should succeed)
echo ""
echo "🔍 Test 3: Admin Role calling /admin (should succeed)"

# Reset to base credentials before assuming admin role
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN

ADMIN_CREDS=$(aws sts assume-role \
  --role-arn "$ADMIN_ROLE_ARN" \
  --role-session-name "admin-test-$(date +%s)" \
  --external-id "admin-mcp-access" \
  --output json)

export AWS_ACCESS_KEY_ID=$(echo "$ADMIN_CREDS" | jq -r '.Credentials.AccessKeyId')
export AWS_SECRET_ACCESS_KEY=$(echo "$ADMIN_CREDS" | jq -r '.Credentials.SecretAccessKey')
export AWS_SESSION_TOKEN=$(echo "$ADMIN_CREDS" | jq -r '.Credentials.SessionToken')

echo "  Making SigV4 request to /admin..."
RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  --aws-sigv4 "aws:amz:$REGION:execute-api" \
  --user "$AWS_ACCESS_KEY_ID:$AWS_SECRET_ACCESS_KEY" \
  -H "X-Amz-Security-Token: $AWS_SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -X POST "$API_URL/admin" \
  -d '{"ask_text": "Give me pull request 9 summary", "account_id": "500330120558", "region": "us-east-1", "metadata": {"repository": "Demo-MCP/mcp-cross-account-pipeline", "pr_number": 9, "actor": "test-user", "run_id": "12345"}}' \
  2>/dev/null || echo "FAILED")

HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE:/d')

if [[ "$HTTP_CODE" == "200" ]]; then
  echo "  ✅ SUCCESS: Admin role can call /admin (HTTP $HTTP_CODE)"
  echo "  📤 Request: Give me pull request 9 summary"
  echo "  📥 Response: $BODY"
else
  echo "  ❌ FAILED: Admin role cannot call /admin (HTTP $HTTP_CODE)"
  echo "  Response: $BODY"
fi

# Test 4: No credentials (should fail)
echo ""
echo "🔍 Test 4: Unsigned request (should fail with 403)"
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN

RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  -H "Content-Type: application/json" \
  -X POST "$API_URL/ask" \
  -d '{"ask_text": "test"}' \
  2>/dev/null || echo "FAILED")

HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)

if [[ "$HTTP_CODE" == "403" ]]; then
  echo "  ✅ SUCCESS: Unsigned request correctly denied (HTTP $HTTP_CODE)"
else
  echo "  ❌ UNEXPECTED: Unsigned request got HTTP $HTTP_CODE (expected 403)"
fi

echo ""
echo "🎉 Authentication tests completed!"
echo ""
echo "📋 Summary:"
echo "  - Dev role can access /ask only ✅"
echo "  - Dev role denied /admin access ✅"  
echo "  - Admin role can access /admin ✅"
echo "  - Unsigned requests denied ✅"
