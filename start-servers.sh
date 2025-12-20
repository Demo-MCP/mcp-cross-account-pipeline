#!/bin/bash

# Set PYTHONPATH to include platform_aws_context
export PYTHONPATH="/app:/app/platform_aws_context:/app/ecs-mcp-server:/app/aws-iac-mcp-server:$PYTHONPATH"

# Start ECS MCP server on port 8000
cd /app/ecs-mcp-server
python -m awslabs.ecs_mcp_server.main &

# Start IaC MCP server on port 8001  
cd /app/aws-iac-mcp-server
python -m awslabs.aws_iac_mcp_server.server &

# Wait for both processes
wait
