#!/bin/bash

# Deploy Lambda function code for MCP metrics writer
# Usage: ./deploy-lambda-code.sh

set -e

FUNCTION_NAME="mcp-metrics-writer"
LAMBDA_DIR="lambda/metrics-writer"

echo "Building Lambda deployment package with Docker..."

# Use Docker to build with Linux environment (commented out - package already exists)
# docker run --rm \
#   -v "$PWD/$LAMBDA_DIR":/var/task \
#   -w /var/task \
#   --entrypoint="" \
#   public.ecr.aws/lambda/python:3.11 \
#   bash -c "
#     yum install -y zip && 
#     pip install psycopg2-binary -t . && 
#     zip -r lambda-deployment.zip . -x '*.pyc' '__pycache__/*'
#   "

# Create deployment package with existing dependencies
cd $LAMBDA_DIR
zip -r lambda-deployment.zip . -x "*.pyc" "__pycache__/*"

echo "Updating Lambda function code..."
aws lambda update-function-code \
    --function-name $FUNCTION_NAME \
    --zip-file fileb://lambda-deployment.zip \
    --region us-east-1

# Cleanup
rm -f lambda-deployment.zip
cd ../..

echo "✅ Lambda function code updated successfully!"

# Test the function
echo "Testing Lambda function..."
aws lambda invoke \
    --function-name $FUNCTION_NAME \
    --payload '{"action":"test"}' \
    --cli-binary-format raw-in-base64-out \
    --region us-east-1 \
    response.json

echo "Lambda response:"
cat response.json
rm response.json

echo ""
echo "✅ Lambda deployment complete!"
