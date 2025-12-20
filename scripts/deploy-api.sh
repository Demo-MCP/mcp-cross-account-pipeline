#!/bin/bash

# Deploy MCP API Gateway and Lambda

ACCOUNT_ID="500330120558"
REGION="us-east-1"

echo "Creating Lambda deployment package..."
cd lambda
zip -r mcp-api.zip mcp-api.py
cd ..

echo "Creating Lambda function..."
aws lambda create-function \
  --function-name mcp-api \
  --runtime python3.11 \
  --role arn:aws:iam::$ACCOUNT_ID:role/McpServerTaskRole \
  --handler mcp-api.lambda_handler \
  --zip-file fileb://lambda/mcp-api.zip \
  --timeout 60 \
  --region $REGION

echo "Creating API Gateway..."
API_ID=$(aws apigatewayv2 create-api \
  --name mcp-api \
  --protocol-type HTTP \
  --target arn:aws:lambda:$REGION:$ACCOUNT_ID:function:mcp-api \
  --region $REGION \
  --query 'ApiId' --output text)

echo "Adding Lambda permission for API Gateway..."
aws lambda add-permission \
  --function-name mcp-api \
  --statement-id api-gateway-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:$REGION:$ACCOUNT_ID:$API_ID/*/*" \
  --region $REGION

echo "Getting API endpoint..."
API_ENDPOINT=$(aws apigatewayv2 get-api \
  --api-id $API_ID \
  --region $REGION \
  --query 'ApiEndpoint' --output text)

echo ""
echo "✅ MCP API deployed successfully!"
echo "API Endpoint: $API_ENDPOINT"
echo ""
echo "Add this to GitHub repository secrets:"
echo "MCP_API_ENDPOINT=$API_ENDPOINT"
echo ""
echo "Test with:"
echo "curl -X POST $API_ENDPOINT -H 'Content-Type: application/json' -d '{\"tool\":\"troubleshoot_cloudformation_deployment\",\"account_id\":\"$ACCOUNT_ID\",\"region\":\"$REGION\",\"stack_name\":\"test\"}'"
