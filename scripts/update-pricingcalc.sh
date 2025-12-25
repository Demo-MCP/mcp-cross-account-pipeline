#!/bin/bash

# Update pricing calculator task definition with stable image

# Get current task definition
CURRENT_TASK_DEF=$(aws ecs describe-task-definition --task-definition pricingcalc-mcp --query 'taskDefinition')

# Update image to v2 tag
UPDATED_TASK_DEF=$(echo $CURRENT_TASK_DEF | jq '.containerDefinitions[0].image = "500330120558.dkr.ecr.us-east-1.amazonaws.com/pricingcalc-mcp:v2"')

# Remove fields that shouldn't be in register call
CLEAN_TASK_DEF=$(echo $UPDATED_TASK_DEF | jq 'del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .placementConstraints, .compatibilities, .registeredAt, .registeredBy)')

# Register new task definition
NEW_TASK_DEF_ARN=$(aws ecs register-task-definition --cli-input-json "$CLEAN_TASK_DEF" --query 'taskDefinition.taskDefinitionArn' --output text)

echo "New task definition registered: $NEW_TASK_DEF_ARN"

# Update service to use new task definition
aws ecs update-service \
  --cluster mcp-cluster \
  --service pricingcalc-mcp \
  --task-definition $NEW_TASK_DEF_ARN \
  --force-new-deployment

echo "Service updated with new task definition"
