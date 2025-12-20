# MCP Cross-Account Pipeline

End-to-end AWS infrastructure analysis pipeline using Model Context Protocol (MCP) servers with cross-account support.

## Architecture

```
GitHub PR Comment → GitHub Actions → ECS Fargate → MCP Servers → AssumeRole → AWS APIs → AI Analysis
```

## Features

- **Cross-Account Support**: Dynamic role assumption per API call
- **MCP Protocol**: Standardized AI tool integration
- **ECS Fargate**: Serverless container execution
- **GitHub Integration**: PR comment triggers and responses
- **Multi-Service**: ECS and Infrastructure-as-Code analysis

## Quick Start

1. **Deploy IAM Roles**:
   ```bash
   ./scripts/setup-iam-roles.sh
   ```

2. **Build and Deploy**:
   ```bash
   docker build -t mcp-servers .
   ./scripts/deploy-ecs.sh
   ```

3. **Test Cross-Account**:
   ```bash
   ./scripts/test-cross-account.sh
   ```

## Repository Structure

```
├── docker/                 # Container configuration
├── iac/                   # Infrastructure as Code
├── scripts/               # Deployment scripts
├── .github/workflows/     # GitHub Actions
└── mcp-servers/          # MCP server code
```

## Usage

Comment on any PR with:
- `/analyze-infrastructure` - Analyze CloudFormation/CDK
- `/troubleshoot-ecs` - Debug ECS deployments
- `/cross-account <account-id>` - Target specific account

## Cost

~$30/month if running 24/7, or ~$0.04/hour on-demand.
