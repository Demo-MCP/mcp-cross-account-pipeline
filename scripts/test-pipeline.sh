#!/bin/bash

# Test the complete end-to-end pipeline

ACCOUNT_ID="500330120558"
REGION="us-east-1"

echo "🧪 Testing MCP Cross-Account Pipeline"
echo "======================================"

# Get API endpoint from deployment
if [ -z "$MCP_API_ENDPOINT" ]; then
  echo "❌ MCP_API_ENDPOINT not set. Run deploy-api.sh first."
  exit 1
fi

echo "📡 Testing API endpoint: $MCP_API_ENDPOINT"

# Test 1: CloudFormation troubleshooting
echo ""
echo "Test 1: CloudFormation Analysis"
echo "-------------------------------"
RESPONSE=$(curl -s -X POST $MCP_API_ENDPOINT \
  -H "Content-Type: application/json" \
  -d "{
    \"tool\": \"troubleshoot_cloudformation_deployment\",
    \"account_id\": \"$ACCOUNT_ID\",
    \"region\": \"$REGION\",
    \"stack_name\": \"test-stack\"
  }")

echo "Response: $RESPONSE"

# Test 2: ECS service analysis  
echo ""
echo "Test 2: ECS Service Analysis"
echo "----------------------------"
RESPONSE=$(curl -s -X POST $MCP_API_ENDPOINT \
  -H "Content-Type: application/json" \
  -d "{
    \"tool\": \"describe_ecs_service\",
    \"account_id\": \"$ACCOUNT_ID\",
    \"region\": \"$REGION\",
    \"service_name\": \"mcp-service\",
    \"cluster_name\": \"mcp-cluster\"
  }")

echo "Response: $RESPONSE"

echo ""
echo "✅ End-to-end testing complete!"
echo ""
echo "🚀 Ready for GitHub integration!"
echo "Add MCP_API_ENDPOINT=$MCP_API_ENDPOINT to GitHub secrets"
