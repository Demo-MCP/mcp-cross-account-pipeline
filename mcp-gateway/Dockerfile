FROM python:3.11-slim

# Install system dependencies for cfn-guard and internal networking
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1. Install platform helper first as a dependency for other modules
COPY platform_aws_context/ ./platform_aws_context/
RUN pip install --no-cache-dir -e ./platform_aws_context/

# 2. Setup ECS MCP server
COPY ecs-mcp-server/ ./ecs-mcp-server/
RUN pip install --no-cache-dir -e ./ecs-mcp-server/

# 3. Setup IaC MCP server
COPY aws-iac-mcp-server/ ./aws-iac-mcp-server/
RUN pip install --no-cache-dir -e ./aws-iac-mcp-server/

# 4. Install Gateway dependencies
# Note: uvicorn[standard] is needed for high-performance loops
RUN pip install --no-cache-dir fastapi uvicorn[standard] requests boto3 loguru fastmcp

# 5. Copy Gateway script
COPY mcp-gateway/gateway.py ./

# CRITICAL: Set PYTHONPATH so 'python -m awslabs...' can resolve from multiple roots
# This points to the parent directories of the 'awslabs' package folders
ENV PYTHONPATH="/app/ecs-mcp-server:/app/aws-iac-mcp-server:/app:${PYTHONPATH}"

# Expose Gateway port
EXPOSE 8080

# Run gateway with high-performance settings
CMD ["python", "gateway.py"]
