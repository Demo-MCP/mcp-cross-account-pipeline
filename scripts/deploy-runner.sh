#!/bin/bash

# Deploy GitHub Actions runner on ECS

ACCOUNT_ID="500330120558"
REGION="us-east-1"

echo "Building GitHub runner image..."
docker build -f Dockerfile.runner -t github-runner .
docker tag github-runner:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/github-runner:latest

# Create ECR repo for runner
aws ecr create-repository --repository-name github-runner --region $REGION || echo "Repo exists"
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Push runner image
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/github-runner:latest

echo "Creating runner task definition..."
cat > runner-task.json << EOF
{
  "family": "github-runner",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::$ACCOUNT_ID:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::$ACCOUNT_ID:role/McpServerTaskRole",
  "containerDefinitions": [
    {
      "name": "github-runner",
      "image": "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/github-runner:latest",
      "essential": true,
      "environment": [
        {"name": "GITHUB_REPO", "value": "YOUR_USERNAME/mcp-cross-account-pipeline"}
      ],
      "secrets": [
        {"name": "GITHUB_TOKEN", "valueFrom": "arn:aws:secretsmanager:$REGION:$ACCOUNT_ID:secret:github-token"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/github-runner",
          "awslogs-region": "$REGION",
          "awslogs-stream-prefix": "runner"
        }
      }
    }
  ]
}
EOF

# Create log group
aws logs create-log-group --log-group-name /ecs/github-runner --region $REGION || echo "Log group exists"

# Register task
aws ecs register-task-definition --cli-input-json file://runner-task.json --region $REGION

echo "✅ GitHub runner task ready!"
echo ""
echo "Next steps:"
echo "1. Create GitHub token secret: aws secretsmanager create-secret --name github-token --secret-string 'YOUR_GITHUB_TOKEN'"
echo "2. Update GITHUB_REPO in task definition"
echo "3. Run task: aws ecs run-task --cluster mcp-cluster --task-definition github-runner:1 --launch-type FARGATE --network-configuration 'awsvpcConfiguration={subnets=[subnet-0d1a30fbc37023fea],assignPublicIp=ENABLED}'"

rm runner-task.json
