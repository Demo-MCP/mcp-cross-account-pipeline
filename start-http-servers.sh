#!/bin/bash

# Start both MCP servers with HTTP endpoints
cd /app

# Start ECS MCP server on port 8000
cd ecs-mcp-server
export PYTHONPATH="/app:/app/platform_aws_context:/app/ecs-mcp-server"
python3 -m uvicorn awslabs.ecs_mcp_server.main:app --host 0.0.0.0 --port 8000 &

# Start IaC MCP server on port 8001  
cd /app/aws-iac-mcp-server
export PYTHONPATH="/app:/app/platform_aws_context:/app/aws-iac-mcp-server"
python3 -m uvicorn awslabs.aws_iac_mcp_server.server:app --host 0.0.0.0 --port 8001 &

# Keep container running
wait
