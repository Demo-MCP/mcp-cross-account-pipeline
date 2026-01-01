# AWS MCP Broker - Kiro Integration

Smart MCP proxy that connects Kiro CLI to AWS MCP Broker with automatic context injection and local command execution.

## Features

- **Auto-Context**: Automatically detects Git repo, branch, and user context
- **Dynamic Tools**: Fetches available tools from AWS MCP Broker automatically  
- **Local Commands**: Executes GitHub CLI commands locally with user's credentials
- **Smart Deployment**: Complete deployment workflow with auto-diagnostics

## Available Tools

### Core AWS Tools
- `ecs_call_tool` - Query ECS clusters, services, and tasks
- `iac_call_tool` - Analyze CloudFormation stacks and infrastructure  
- `deploy_find_latest` - Find recent deployments
- `deploy_get_run` - Get deployment run details
- `deploy_get_steps` - Get deployment step details
- `deploy_get_summary` - Get deployment summary
- `pricingcalc_estimate_from_stack` - Estimate costs from CloudFormation

### Smart Deployment
- `deploy_workflow` - **Complete deployment with auto-diagnostics**
  - **Auto-detects**: Repository, branch, PR number from Git context
  - **Natural language**: Just say "deploy" or "deploy to staging"
  - Posts PR comments using your GitHub credentials
  - Monitors deployment progress in real-time
  - Auto-investigates failures using IAC and ECS tools
  - Provides actionable next steps

**Example**: When you're on branch `pr-123` in `Demo-MCP/mcp-cross-account-pipeline`:
```bash
kiro "deploy"  # Automatically uses repo, branch, and PR #123
```

## Usage Examples

### Smart Deployment (Auto-Context)
```bash
# Super simple - uses current repo, branch, and auto-detected PR
kiro "deploy"

# Specify environment
kiro "deploy to staging"
kiro "deploy to production"

# Override specific parameters
kiro "deploy to staging with PR 456"
```

### Manual Deployment (Full Control)
```bash
kiro "deploy Demo-MCP/mcp-cross-account-pipeline to staging"
kiro "deploy Demo-MCP/mcp-cross-account-pipeline to production with PR 123"
```

### Infrastructure Queries
```bash
kiro "show ECS services in mcp-cluster"
kiro "get status of CloudFormation stack mcp-broker-auth"
kiro "estimate cost of stack mcp-metrics-infrastructure"
```

## Smart Deployment Flow

1. **Trigger**: Posts `/deploy` comment on PR using your GitHub credentials
2. **Monitor**: Tracks deployment progress automatically  
3. **Diagnose**: If deployment fails, auto-investigates using:
   - CloudFormation stack status and events
   - ECS service health and task status
   - Resource capacity and health checks
4. **Report**: Provides actionable suggestions for fixes

## Auto-Context Detection

Every tool call automatically detects and includes:
- **Repository**: Current Git repository name
- **Branch**: Current Git branch  
- **User**: Local username and Git user
- **Commit**: Current Git commit hash
- **PR Number**: Auto-detected from:
  - Branch name (e.g., `pr-123`, `pull-456`)
  - Recent commit messages (e.g., "Fix issue #123")
  - GitHub CLI (`gh pr view` for current branch)

### Smart Defaults for deploy_workflow
When you run `kiro "deploy"`, it automatically uses:
- Repository from current Git repo
- Branch from current Git branch
- PR number if detected from branch/commits
- Environment from branch (main → production, dev → staging)
- Region from `.kiro/deploy.json` or defaults to `us-east-1`

## Setup

1. **Install Dependencies**:
   ```bash
   cd scripts/aws-mcp-broker
   uv add "mcp[cli]" boto3 requests
   ```

2. **Configure Kiro**:
   ```bash
   kiro-cli mcp add --name aws-mcp-broker \
     --command './run-mcp.sh' \
     --env 'FETCH_BASE_URL=https://d0yrd186v6.execute-api.us-east-1.amazonaws.com/prod' \
     --env 'AWS_PROFILE=default' \
     --env 'AWS_ROLE_ARN=arn:aws:iam::500330120558:role/DevMcpInvokeRole' \
     --env 'AWS_ROLE_EXTERNAL_ID=dev-mcp-access' \
     --env 'AWS_REGION=us-east-1'
   ```

3. **Verify GitHub CLI**:
   ```bash
   gh auth status
   ```

## Architecture

```
Kiro CLI → MCP Proxy → AWS MCP Broker → AWS Services
    ↓         ↓              ↓
Local Git   GitHub CLI    ECS/IAC/Deploy
Context     (User Creds)   Tools
```

## Error Handling

The proxy automatically handles:
- **GitHub CLI failures**: Clear error messages with auth guidance
- **AWS authentication**: Role assumption with proper error reporting  
- **Deployment failures**: Auto-diagnosis with specific tool suggestions
- **Network issues**: Timeout handling and retry logic

## Development

- **Proxy Code**: `aws-mcp-broker.py` - Local MCP server with GitHub CLI integration
- **Deployment Tools**: `deployment-metrics-mcp/` - Cloud-based deployment monitoring
- **Configuration**: `.kiro/settings/mcp.json` - Kiro MCP server configuration

## Troubleshooting

### GitHub CLI Issues
```bash
# Check authentication
gh auth status

# Re-authenticate if needed  
gh auth login
```

### AWS Authentication Issues
```bash
# Check AWS credentials
aws sts get-caller-identity

# Verify role assumption
aws sts assume-role --role-arn arn:aws:iam::500330120558:role/DevMcpInvokeRole --role-session-name test --external-id dev-mcp-access
```

### MCP Server Issues
```bash
# Check Kiro logs
tail -f /var/folders/*/T/kiro-log/kiro-chat.log

# Test MCP server directly
cd scripts/aws-mcp-broker
./run-mcp.sh
```
