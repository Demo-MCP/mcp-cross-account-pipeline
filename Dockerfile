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

# Create startup scripts
WORKDIR /app
COPY start-servers.sh ./
COPY start-http-servers.sh ./
RUN chmod +x start-servers.sh start-http-servers.sh

# Install uvicorn for HTTP servers
RUN pip install uvicorn fastapi

EXPOSE 8000 8001

CMD ["./start-http-servers.sh"]
