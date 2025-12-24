#!/bin/bash

# Deploy MCP Metrics Infrastructure
# Usage: ./deploy-metrics-infrastructure.sh <vpc-id> <subnet-id-1,subnet-id-2> <db-password>

set -e

if [ $# -ne 3 ]; then
    echo "Usage: $0 <vpc-id> <subnet-id-1,subnet-id-2> <db-password>"
    echo "Example: $0 vpc-12345 subnet-abc123,subnet-def456 MySecurePassword123"
    exit 1
fi

VPC_ID=$1
SUBNET_IDS=$2
DB_PASSWORD=$3
STACK_NAME="mcp-metrics-infrastructure"

echo "Deploying MCP Metrics Infrastructure..."
echo "VPC: $VPC_ID"
echo "Subnets: $SUBNET_IDS"

# Deploy CloudFormation stack
aws cloudformation deploy \
    --template-file infrastructure/metrics-infrastructure.yaml \
    --stack-name $STACK_NAME \
    --parameter-overrides \
        VpcId=$VPC_ID \
        PrivateSubnetIds=$SUBNET_IDS \
        DBPassword=$DB_PASSWORD \
    --capabilities CAPABILITY_IAM \
    --region us-east-1

echo "Getting stack outputs..."
DB_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`DatabaseEndpoint`].OutputValue' \
    --output text)

LAMBDA_URL=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query 'Stacks[0].Outputs[?OutputKey==`LambdaFunctionUrl`].OutputValue' \
    --output text)

echo ""
echo "✅ Infrastructure deployed successfully!"
echo ""
echo "Database Endpoint: $DB_ENDPOINT"
echo "Lambda Function URL: $LAMBDA_URL"
echo ""
echo "Next steps:"
echo "1. Deploy actual Lambda code: ./scripts/deploy-lambda-code.sh"
echo "2. Run database migrations: psql -h $DB_ENDPOINT -U metrics_user -d mcp_metrics -f sql/migrations/001_init.sql"
echo "3. Update GitHub workflow to use Lambda URL: $LAMBDA_URL"
echo ""
echo "Note: CloudFormation created the Lambda function with placeholder code."
echo "Step 1 will update it with the actual metrics writer implementation."
