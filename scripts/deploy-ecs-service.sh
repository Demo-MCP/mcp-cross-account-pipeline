#!/bin/bash

# Deploy ECS service for persistent MCP servers

ACCOUNT_ID="500330120558"
REGION="us-east-1"

echo "Building and pushing Docker image..."
docker build -t mcp-servers .
docker tag mcp-servers:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/mcp-servers:latest
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/mcp-servers:latest

echo "Creating ECS service task definition..."
cat > ecs-service-task.json << EOF
{
  "family": "mcp-service",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::$ACCOUNT_ID:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::$ACCOUNT_ID:role/McpServerTaskRole",
  "containerDefinitions": [
    {
      "name": "mcp-servers",
      "image": "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/mcp-servers:latest",
      "essential": true,
      "portMappings": [
        {"containerPort": 8000, "protocol": "tcp"},
        {"containerPort": 8001, "protocol": "tcp"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/mcp-servers",
          "awslogs-region": "$REGION",
          "awslogs-stream-prefix": "service"
        }
      }
    }
  ]
}
EOF

echo "Registering task definition..."
aws ecs register-task-definition --cli-input-json file://ecs-service-task.json --region $REGION

echo "Creating ECS service..."
SUBNET_IDS=$(aws ec2 describe-subnets --filters "Name=default-for-az,Values=true" --region $REGION --query 'Subnets[0:2].SubnetId' --output text | tr '\t' ',')

aws ecs create-service \
  --cluster mcp-cluster \
  --service-name mcp-service \
  --task-definition mcp-service:1 \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_IDS],assignPublicIp=ENABLED}" \
  --region $REGION

echo "✅ MCP service deployed!"
echo "Service will be available at the task's public IP on ports 8000 and 8001"

# Clean up
rm ecs-service-task.json
