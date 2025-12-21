FROM python:3.11-slim

WORKDIR /app

# Copy and install platform_aws_context helper
COPY platform_aws_context/ ./platform_aws_context/
RUN pip install -e ./platform_aws_context/

# Copy and install ECS MCP server
COPY ecs-mcp-server/ ./ecs-mcp-server/
WORKDIR /app/ecs-mcp-server
RUN pip install -e .

# Copy and install IaC MCP server
WORKDIR /app
COPY aws-iac-mcp-server/ ./aws-iac-mcp-server/
WORKDIR /app/aws-iac-mcp-server
RUN pip install -e .

# Install FastAPI and uvicorn for HTTP gateway
WORKDIR /app
RUN pip install fastapi uvicorn[standard]

# Copy gateway
COPY mcp-gateway/gateway.py ./

# Expose port 8080
EXPOSE 8080

# Run gateway
CMD ["python", "gateway.py"]
