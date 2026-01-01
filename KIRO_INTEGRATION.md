# Kiro MCP Integration Configuration

## Overview
This configuration adds our AWS MCP Broker as a Kiro agent, providing access to 7 user-tier tools through authenticated API Gateway.

## Available Tools
- `ecs_call_tool` - ECS cluster and service operations
- `iac_call_tool` - CloudFormation stack analysis  
- `deploy_find_latest` - Find latest deployment runs
- `deploy_get_run` - Get deployment run details
- `deploy_get_steps` - Get deployment step progress
- `deploy_get_summary` - Get deployment final summary
- `pricingcalc_estimate_from_stack` - AWS cost estimation

## Configuration

### Option 1: MCP Server Configuration (Recommended)
Add to your Kiro MCP servers configuration:

```json
{
  "mcpServers": {
    "aws-mcp-broker": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-fetch"],
      "env": {
        "FETCH_BASE_URL": "https://d0yrd186v6.execute-api.us-east-1.amazonaws.com/prod",
        "FETCH_METHOD": "POST",
        "FETCH_ENDPOINT": "/ask",
        "FETCH_HEADERS": "{\"Content-Type\": \"application/json\"}",
        "AWS_PROFILE": "default",
        "AWS_ROLE_ARN": "arn:aws:iam::500330120558:role/DevMcpInvokeRole",
        "AWS_ROLE_EXTERNAL_ID": "dev-mcp-access",
        "AWS_REGION": "us-east-1"
      }
    }
  }
}
```

### Option 2: Direct HTTP Configuration
If using direct HTTP transport:

```json
{
  "name": "aws-mcp-broker",
  "transport": "http",
  "base_url": "https://d0yrd186v6.execute-api.us-east-1.amazonaws.com/prod",
  "endpoint": "/ask",
  "method": "POST",
  "auth": {
    "type": "aws_sigv4",
    "service": "execute-api",
    "region": "us-east-1"
  },
  "headers": {
    "Content-Type": "application/json"
  }
}
```

## AWS Credentials Setup

Ensure your AWS credentials can assume the DevMcpInvokeRole:

```bash
# Test credentials
aws sts assume-role \
  --role-arn "arn:aws:iam::500330120558:role/DevMcpInvokeRole" \
  --role-session-name "kiro-test" \
  --external-id "dev-mcp-access"
```

## Request Format

Kiro should send requests in this format:

```json
{
  "ask_text": "Your question here",
  "account_id": "500330120558",
  "region": "us-east-1",
  "metadata": {
    "repository": "ORG/REPO",
    "actor": "kiro-user",
    "pr_number": 123,
    "run_id": "optional-github-run-id"
  }
}
```

## Response Format

Clean responses with only essential data:

```json
{
  "final_response": "The answer to your question...",
  "debug": {
    "tier": "user",
    "correlation_id": "broker__abc123",
    "tools_advertised_count": 7,
    "total_ms": 3119
  }
}
```

## Correlation ID Headers

Always include correlation ID for traceability:

```
x-correlation-id: <repo>__pr-<PR_NUMBER>__attempt-<N>__run-<github_run_id>
```

Example: `Demo-MCP/mcp-cross-account-pipeline__pr-123__attempt-1__run-456789`

## Testing

Test the configuration:

```bash
# Test tools endpoint (no auth required)
curl "https://d0yrd186v6.execute-api.us-east-1.amazonaws.com/prod/tools"

# Test authenticated request
curl -X POST \
  --aws-sigv4 "aws:amz:us-east-1:execute-api" \
  -H "Content-Type: application/json" \
  -H "x-correlation-id: test__pr-1__attempt-1" \
  "https://d0yrd186v6.execute-api.us-east-1.amazonaws.com/prod/ask" \
  -d '{"ask_text": "List ECS clusters", "account_id": "500330120558", "region": "us-east-1"}'
```

## Security Features

- ✅ AWS SigV4 authentication required
- ✅ Role-based access control (DevMcpInvokeRole)
- ✅ Session token validation
- ✅ Correlation ID tracking
- ✅ Clean response format
- ✅ No direct ALB access allowed

## Deployment Workflow Integration

For the deployment workflow described in the integration plan:

1. **Trigger**: Kiro posts `/deploy` comment on PR
2. **Discovery**: Use `deploy_find_latest` to find active run
3. **Polling**: Use `deploy_get_steps` to track progress  
4. **Summary**: Use `deploy_get_summary` for final status

All tools are available through the `/ask` endpoint with DevMcpInvokeRole credentials.
