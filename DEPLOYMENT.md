# Deployment Guide

## Quick Setup

1. **Deploy IAM Roles**:
   ```bash
   ./scripts/setup-iam-roles.sh
   ```

2. **Deploy ECS Service**:
   ```bash
   ./scripts/deploy-ecs-service.sh
   ```

3. **Deploy API Gateway**:
   ```bash
   ./scripts/deploy-api.sh
   ```

4. **Test Pipeline**:
   ```bash
   export MCP_API_ENDPOINT="<endpoint-from-step-3>"
   ./scripts/test-pipeline.sh
   ```

## GitHub Setup

1. **Add Repository Secrets**:
   - `MCP_API_ENDPOINT`: API Gateway endpoint from step 3

2. **Test PR Comments**:
   - `/analyze-infrastructure stack=my-stack account=123456789012`
   - `/troubleshoot-ecs service=my-service account=123456789012`

## Architecture

```
GitHub PR Comment
    ↓ HTTP POST
API Gateway
    ↓ Lambda Invoke  
Lambda Function
    ↓ HTTP Request
ECS Service (MCP Servers)
    ↓ AssumeRole
Target AWS Account
    ↓ API Response
GitHub PR Comment
```

## Benefits

- **No AWS Keys in GitHub**: Only API endpoint needed
- **Fast Response**: Persistent ECS service, no cold starts
- **Cross-Account**: Dynamic role assumption per request
- **Scalable**: ECS service can auto-scale based on load
