FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install fastapi uvicorn[standard] boto3 requests pydantic fastmcp

# Copy source code
COPY awslabs/ ./awslabs/
COPY server.json ./

# Expose port
EXPOSE 8080

# Run the MCP server
CMD ["python", "-m", "awslabs.ecs_mcp_server.main"]
