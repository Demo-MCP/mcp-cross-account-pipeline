# MCP Cross-Account Pipeline

End-to-end AWS infrastructure analysis pipeline using Model Context Protocol (MCP) servers with cross-account support, Nova Pro AI integration, enhanced Strands implementation, and comprehensive AWS SigV4 authentication.

## 🏗️ Architecture

```
┌─ GitHub PR Comment ─┐    ┌─ Kiro CLI (Local) ─┐
│                     │    │                    │
▼                     ▼    ▼                    ▼
GitHub Actions → AWS SigV4 Auth → API Gateway → Enhanced Strands Broker → MCP Gateway → MCP Servers → AWS APIs → Nova Pro Analysis
                      ▲                                                                    ▲
                      │                                                                    │
                      └─ Local MCP Server ──────────────────────────────────────────────┘
                         (aws-mcp-broker)
```

**Integration Paths:**
- **GitHub Actions**: PR comments trigger authenticated workflows
- **Kiro CLI**: Local development with direct MCP server access
- **API Gateway**: Centralized authentication and routing
- **MCP Protocol**: Standardized tool integration across all paths

## 🔒 Authentication & Security

### AWS SigV4 Authentication
- **API Gateway Integration**: All requests must go through authenticated API Gateway endpoints
- **Role-Based Access Control**: Dev and Admin roles with different permissions
- **Session Token Validation**: Validates AWS session tokens from assumed roles
- **Defense in Depth**: Both API Gateway IAM auth AND broker-level validation

### Access Control Matrix
| Role | `/ask` Endpoint | `/admin` Endpoint | Tools Available |
|------|----------------|-------------------|-----------------|
| **DevMcpInvokeRole** | ✅ Allowed | ❌ Denied | User tools only (7 tools) |
| **AdminMcpInvokeRole** | ✅ Allowed | ✅ Allowed | All tools (11 tools) |
| **Unauthenticated** | ❌ Denied | ❌ Denied | None |

### Security Features
- **Direct ALB Access Blocked**: GitHub workflows cannot bypass authentication
- **Session Token Verification**: Validates tokens are from authorized roles
- **API Gateway Headers**: Validates requests came through proper API Gateway
- **Fail-Closed Security**: All endpoints require authentication by default

## ✨ Enhanced Strands Implementation

### 🧠 Advanced Prompt Engineering
- **Context-Aware Prompts**: Dynamic prompt generation based on tool context and user intent
- **Multi-Turn Conversations**: Maintains conversation state across tool calls
- **Tool-Specific Instructions**: Tailored prompts for different tool categories (ECS, IAC, PR analysis)
- **Error Recovery Prompts**: Intelligent error handling with contextual retry strategies

### 🛡️ Intelligent Guards System
- **Pre-Execution Validation**: Validates tool parameters before execution
- **Security Guards**: Prevents unauthorized access to sensitive operations
- **Rate Limiting**: Protects against excessive API calls
- **Input Sanitization**: Validates and sanitizes all user inputs
- **Tool Compatibility Checks**: Ensures tool combinations are valid

### 🎯 Model-Minimal Architecture
- **Efficient Token Usage**: Optimized prompts to minimize token consumption
- **Selective Context**: Only includes relevant context for each tool call
- **Response Compression**: Compresses verbose API responses while preserving key information
- **Smart Caching**: Caches frequently used data to reduce model calls
- **Streaming Optimization**: Handles large responses without token overflow

### 🔄 Stateful Data Handoff
- **Internal Tool Orchestration**: Tools can call other tools internally without exposing complexity to Nova
- **Data Pipeline**: Seamless data flow between pr_get_diff → pr_analyze → pr_summarize
- **Context Preservation**: Maintains state across multi-step operations
- **Error Isolation**: Failures in one step don't cascade to others
- **Response Aggregation**: Combines multiple tool outputs into coherent responses

### 🚫 Hallucination Prevention
- **Fact-Based Responses**: All responses grounded in actual API data
- **Source Attribution**: Clear attribution of information sources
- **Validation Layers**: Multiple validation steps prevent incorrect information
- **Structured Outputs**: Enforced JSON schemas for consistent, accurate responses
- **Real-Time Verification**: Cross-references responses with live AWS data

## ✨ Core Features

* **🔄 Tier-Based Broker**: Secure multi-tier access control with `/ask` (user) and `/admin` (privileged) endpoints
* **🔒 Security-First Design**: Fail-closed security with AWS SigV4 authentication and role-based access control
* **📊 Deployment Metrics Integration**: Real-time GitHub Actions deployment tracking and analysis
* **🔍 PR Analysis Tools**: Comprehensive pull request analysis with security scanning (admin-only)
* **🤖 Nova Pro Integration**: Advanced AI tool calling with agentic loops and streaming timeout resolution
* **🔀 Cross-Account Support**: Dynamic role assumption per API call
* **🌐 MCP Protocol**: Standardized AI tool integration with gateway routing
* **☁️ ECS Fargate**: Serverless container execution with container stability improvements
* **🔗 GitHub Integration**: PR comment triggers and responses with enhanced workflow output
* **🏗️ Multi-Service**: ECS, Infrastructure-as-Code, deployment analysis, and pricing

### 🆕 Enhanced: Streaming Timeout Resolution

**Problem Solved**: Large CloudFormation templates (169+ lines) were causing "Response ended prematurely" errors and container crashes.

**Solution Implemented**:
- **Tool Orchestration**: Created pr_analyze orchestrator tool that handles large diff data internally
- **Stateful Handoff Pattern**: pr_analyze processes large diffs internally and returns lightweight summaries to Nova
- **Parameter Resolution**: Fixed missing correlation_id and pr_get_diff parameter issues
- **Container Stability**: Eliminated 504 gateway timeouts and container crashes during PR analysis
- **Checkov Integration Preserved**: Maintained full security scanning functionality through internal tool calls

**Results**:
- ✅ **No More Streaming Failures**: Large templates processed without "Response ended prematurely" errors
- ✅ **Container Stability**: No more broker container crashes during analysis
- ✅ **Full Security Scanning**: Checkov integration maintained with comprehensive analysis output
- ✅ **Performance**: Sub-2-minute analysis of complex CloudFormation templates

### 🆕 Enhanced: Tool Selection & Orchestration

**Intelligent Tool Policy Management**:
- **Tool Descriptions**: Updated to guide Nova toward optimal tool selection
- **Orchestration Pattern**: pr_analyze calls both pr_get_diff and pr_summarize internally
- **Policy-Based Selection**: Tools can call other tools internally if both are available in policy
- **Duplicate Function Cleanup**: Removed conflicting tool definitions

**Tool Availability by Tier**:

**Tool Availability by Tier**:

**👤 User Tier (`/ask` endpoint):**
- **9 Tools Available**: Basic infrastructure and deployment tools
- **Safe Operations**: Read-only access to ECS, CloudFormation, deployments
- **Pricing Analysis**: Cost estimation for approved resources
- **No Sensitive Access**: Cannot access PR analysis or stack pricing

**🔐 Admin Tier (`/admin` endpoint):**
- **12 Tools Available**: All user tools + sensitive operations
- **PR Analysis**: Full pull request diff analysis and security scanning with pr_analyze orchestrator
- **Stack Pricing**: Cost estimation for any CloudFormation stack
- **Complete Access**: All infrastructure analysis capabilities

**Security Features**:
- **Fail-Closed Design**: Tools not explicitly allowed are blocked
- **Tool Execution Gating**: Double validation at advertisement and execution
- **Metadata-Driven**: Uses GitHub Actions context for secure parameter mapping
- **Audit Logging**: Tracks all tool calls and denied attempts
- **Correlation ID Tracking**: Full request tracing for debugging and security

### 🆕 New: AWS Pricing Calculator Integration

The system now includes comprehensive AWS cost estimation capabilities:

- **Real-Time Pricing**: Uses AWS Pricing API for accurate, up-to-date cost calculations
- **CloudFormation Support**: Estimates costs from CloudFormation templates (YAML/JSON)
- **Cross-Account Pricing**: Price stacks deployed in different AWS accounts
- **47 AWS Services**: Supports EC2, RDS, Lambda, S3, ECS, ALB, and 40+ other services
- **Free Tier Handling**: Automatically applies AWS Free Tier allowances
- **Monthly Estimates**: Provides detailed monthly cost breakdowns
- **Template Parsing**: Handles CloudFormation intrinsic functions and references

### 🆕 New: Unified MCP Broker Integration

The broker service now provides a single, intelligent entry point for all deployment tools:

- **Dynamic Tool Discovery**: Automatically discovers tools from PR Context, deployment metrics, and pricing MCP servers
- **Intelligent Routing**: Routes `pr_*` tools to PR Context, `deploy_*` tools to metrics, `pricingcalc_*` tools to pricing
- **Tool Caching**: Caches 12 tools at startup for consistent sub-second response times
- **Metadata Integration**: Uses GitHub Actions metadata for repository and run_id when available
- **Parameter Mapping**: Automatically maps Bedrock parameters to MCP service requirements
- **Auto Run Selection**: Automatically selects RUNNING deployments when no run_id provided
- **Text Response Handling**: Properly formats text responses for Bedrock compatibility
- **Repository Validation**: Validates repository format and prefers metadata over AI guesses

### 🆕 Enhanced: PR Analysis & Security Scanning

**Comprehensive Analysis Pipeline**:
- **Diff Analysis**: Complete PR diff retrieval and parsing with large template support
- **Security Scanning**: Checkov integration for infrastructure security analysis
- **Orchestrated Workflow**: pr_analyze → pr_get_diff → pr_summarize internal handoff
- **IAC Resource Detection**: Identifies CloudFormation, Terraform, and other IAC changes
- **Cost Impact Analysis**: Estimates pricing impact of infrastructure changes
- **Admin-Only Access**: Sensitive code analysis restricted to privileged users
- **GitHub Integration**: Seamless integration with GitHub Actions workflows

**Enhanced Security Features**:
- **Medium/High/Critical Issue Detection**: Comprehensive security finding classification
- **Resource-Specific Findings**: Identifies exact resources and line numbers with issues
- **Remediation Guidance**: Provides actionable steps to fix security issues
- **Compliance Scanning**: Checks against AWS security best practices
- **Large Template Support**: Handles 169+ line CloudFormation templates without timeout

**Workflow Integration**:
- **Clean Output**: Removed `.answer` fallback for cleaner GitHub workflow results
- **Structured Response**: Consistent JSON response format
- **Error Handling**: Graceful handling of analysis failures with detailed error messages

## 🖥️ Kiro CLI Integration

### Local Development with MCP

The pipeline now includes **Kiro CLI integration** for local development and testing, providing direct access to deployment orchestration tools through a local MCP server.

**🔧 Key Features:**
- **Local MCP Server**: Run deployment tools locally without GitHub Actions
- **Automatic Status Updates**: `deploy_local` automatically calls `deploy_status` after posting PR comments
- **Cross-Account Authentication**: Uses AWS role assumption for secure API access
- **Real-Time Deployment Tracking**: Monitor deployment progress directly from terminal
- **Fallback Protection**: Graceful degradation if automatic status calls fail

**🛠️ Available Tools:**
- `deploy_local <repo> <branch> <environment>` - Post deployment comment and get status
- `deploy_status <repo>` - Check current deployment status
- `deploy_get_run <run_id>` - Get detailed run information
- `deploy_list_runs <repo>` - List recent deployment runs

**⚡ Quick Setup:**
```bash
# 1. Run setup script
./scripts/setup-kiro-mcp.sh

# 2. Start Kiro CLI
kiro-cli chat

# 3. Deploy and monitor
deploy_local Demo-MCP/mcp-cross-account-pipeline feature-branch dev
```

**🔄 Workflow Enhancement:**
- **Before**: Manual PR comment → Manual status check → Manual run details
- **After**: Single command → Automatic status → Integrated monitoring

**📁 Integration Files:**
- `scripts/aws-mcp-broker/` - Complete MCP server implementation
- `scripts/setup-kiro-mcp.sh` - Automated setup script
- `scripts/kiro-mcp-config.json` - Configuration template
- `KIRO_INTEGRATION.md` - Detailed integration documentation

**🔒 Security:**
- Uses same AWS role assumption as GitHub Actions
- Validates repository access permissions
- Secure credential handling through AWS profiles
- No hardcoded secrets or tokens

## 🚀 Quick Deploy from Scratch

### Prerequisites
- AWS CLI configured with admin permissions
- Docker installed and logged into ECR
- GitHub repository with Actions enabled

### 1. Configure Infrastructure Parameters

Update the following files with your AWS account details:

**scripts/mcp-gateway-task.json**
```json
{
  "family": "mcp-gateway",
  "taskRoleArn": "arn:aws:iam::YOUR-ACCOUNT-ID:role/McpServerTaskRole",
  "executionRoleArn": "arn:aws:iam::YOUR-ACCOUNT-ID:role/ecsTaskExecutionRole"
}
```

## 🔐 Authentication Setup

### 1. Deploy Authentication Infrastructure

Deploy the API Gateway with AWS SigV4 authentication:

```bash
cd infrastructure
./deploy-auth.sh
```

This creates:
- **API Gateway HTTP API** with AWS_IAM authorization
- **DevMcpInvokeRole** - Limited to `/ask` endpoint (user tools)
- **AdminMcpInvokeRole** - Access to both `/ask` and `/admin` endpoints
- **VPC Link** for secure ALB integration

### 2. Test Authentication

Test the authentication system:

```bash
cd scripts
./test-auth.sh
```

Expected results:
- ✅ Dev role can call `/ask` (HTTP 200)
- ✅ Dev role denied `/admin` access (HTTP 403)  
- ✅ Admin role can call `/admin` (HTTP 200)
- ✅ Unsigned requests denied (HTTP 403)

### 3. API Endpoints

**Authenticated API Gateway URLs:**
- **Ask Endpoint**: `https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/prod/ask`
- **Admin Endpoint**: `https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/prod/admin`
- **Tools Endpoint**: `https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/prod/tools` (no auth)

**Direct ALB Access**: ❌ **BLOCKED** - All requests must go through API Gateway

## 🔐 Security & Access Control

### Authentication Flow
```
GitHub Actions → Assume Role → SigV4 Sign → API Gateway → Broker → MCP Servers
```

### Tier-Based Access

The system implements two access tiers for security:

**👤 User Tier (`/ask` endpoint):**
```bash
# Safe for general use - 9 tools available
curl -X POST http://your-broker-url/ask \
  -H "Content-Type: application/json" \
  -d '{"ask_text": "List ECS clusters"}'
```

**🔐 Admin Tier (`/admin` endpoint):**
```bash
# Privileged access - 12 tools available (includes PR analysis)
curl -X POST http://your-broker-url/admin \
  -H "Content-Type: application/json" \
  -d '{
    "ask_text": "Analyze pull request #9 for security issues",
    "metadata": {
      "repository": "org/repo",
      "pr_number": 9,
      "actor": "username",
      "run_id": "12345"
    }
  }'
```

### Tool Categories

| Category | User Tier | Admin Tier | Description |
|----------|-----------|------------|-------------|
| **ECS Tools** | ✅ | ✅ | List clusters, describe services |
| **IAC Tools** | ✅ | ✅ | CloudFormation stack analysis |
| **Deploy Tools** | ✅ | ✅ | GitHub Actions deployment metrics |
| **Basic Pricing** | ✅ | ✅ | Cost estimation from templates |
| **PR Analysis** | ❌ | ✅ | Pull request diff and security scanning |
| **Stack Pricing** | ❌ | ✅ | Cost estimation for any CloudFormation stack |

### GitHub Actions Integration

Use the `/analyze` command in PR comments for admin-level analysis:

```
/analyze Get security analysis and cost impact for this PR
```

This triggers the admin workflow with proper metadata context.

**scripts/broker-task.json**
```json
{
  "family": "broker-service", 
  "taskRoleArn": "arn:aws:iam::YOUR-ACCOUNT-ID:role/McpServerTaskRole",
  "executionRoleArn": "arn:aws:iam::YOUR-ACCOUNT-ID:role/ecsTaskExecutionRole"
}
```

**Update subnets and security groups in deployment scripts:**
- Subnets: `subnet-0d1a30fbc37023fea`, `subnet-0b296ab71b4c7e39d`
- Security Group: `sg-0190ab5630f4e7309`

### 2. Build and Push Images

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR-ACCOUNT-ID.dkr.ecr.us-east-1.amazonaws.com

# Build and push broker service
cd broker-service
docker build -t YOUR-ACCOUNT-ID.dkr.ecr.us-east-1.amazonaws.com/broker-service:latest .
docker push YOUR-ACCOUNT-ID.dkr.ecr.us-east-1.amazonaws.com/broker-service:latest

# Build and push pricing calculator
cd ../pricingcalc-mcp
docker build -t YOUR-ACCOUNT-ID.dkr.ecr.us-east-1.amazonaws.com/pricingcalc-mcp:latest .
docker push YOUR-ACCOUNT-ID.dkr.ecr.us-east-1.amazonaws.com/pricingcalc-mcp:latest

# Build and push MCP gateway
cd ../mcp-gateway
docker build -f Dockerfile -t YOUR-ACCOUNT-ID.dkr.ecr.us-east-1.amazonaws.com/mcp-gateway:latest .
docker push YOUR-ACCOUNT-ID.dkr.ecr.us-east-1.amazonaws.com/mcp-gateway:latest

# Build and push GitHub runner (for testing)
cd ../github-runner
docker build -t YOUR-ACCOUNT-ID.dkr.ecr.us-east-1.amazonaws.com/github-runner:latest .
docker push YOUR-ACCOUNT-ID.dkr.ecr.us-east-1.amazonaws.com/github-runner:latest
```

### 3. Deploy Infrastructure

```bash
# Create ECS cluster
aws ecs create-cluster --cluster-name mcp-cluster

# Register task definitions
aws ecs register-task-definition --cli-input-json file://scripts/broker-task.json
aws ecs register-task-definition --cli-input-json file://scripts/mcp-gateway-task.json

# Create ALB and target groups (update with your VPC/subnet IDs)
aws elbv2 create-load-balancer --name broker-internal-alb --subnets subnet-YOUR-ID subnet-YOUR-ID --security-groups sg-YOUR-ID --scheme internal
aws elbv2 create-load-balancer --name mcp-internal-alb --subnets subnet-YOUR-ID subnet-YOUR-ID --security-groups sg-YOUR-ID --scheme internal

# Create ECS services
aws ecs create-service --cluster mcp-cluster --service-name broker-service --task-definition broker-service:1 --desired-count 1 --launch-type FARGATE --network-configuration "awsvpcConfiguration={subnets=[subnet-YOUR-ID,subnet-YOUR-ID],securityGroups=[sg-YOUR-ID],assignPublicIp=ENABLED}" --load-balancers targetGroupArn=arn:aws:elasticloadbalancing:us-east-1:YOUR-ACCOUNT-ID:targetgroup/broker-targets/YOUR-ID,containerName=broker-service,containerPort=8080

aws ecs create-service --cluster mcp-cluster --service-name mcp-gateway --task-definition mcp-gateway:1 --desired-count 1 --launch-type FARGATE --network-configuration "awsvpcConfiguration={subnets=[subnet-YOUR-ID,subnet-YOUR-ID],securityGroups=[sg-YOUR-ID],assignPublicIp=ENABLED}" --load-balancers targetGroupArn=arn:aws:elasticloadbalancing:us-east-1:YOUR-ACCOUNT-ID:targetgroup/mcp-gateway-targets/YOUR-ID,containerName=mcp-gateway,containerPort=8080
```

### 4. Configure GitHub Actions

Set repository secrets:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`  
- `AWS_REGION` (us-east-1)
- `GITHUB_TOKEN`

Update `.github/workflows/ask.yml` with your ALB URL:
```yaml
env:
  BROKER_URL: "http://internal-broker-internal-alb-YOUR-ID.us-east-1.elb.amazonaws.com"
```

### 5. Test End-to-End

```bash
# Test ECS MCP server
curl -X POST http://YOUR-GATEWAY-ALB-URL/call-tool \
  -H "Content-Type: application/json" \
  -d '{"server": "ecs", "tool": "ecs_call_tool", "params": {"tool": "ecs_resource_management", "params": {"api_operation": "ListClusters", "api_params": {}, "account_id": "YOUR-ACCOUNT-ID", "region": "us-east-1"}}}'

# Test IAC MCP server  
curl -X POST http://YOUR-GATEWAY-ALB-URL/call-tool \
  -H "Content-Type: application/json" \
  -d '{"server": "iac", "tool": "iac_call_tool", "params": {"tool": "troubleshoot_cloudformation_deployment", "params": {"account_id": "YOUR-ACCOUNT-ID", "region": "us-east-1", "stack_name": "sample-demo"}}}'

# Test unified broker with pricing calculator
curl -X POST http://YOUR-BROKER-ALB-URL/ask \
  -H "Content-Type: application/json" \
  -d '{"ask_text": "How much does my sample-demo stack cost per month?", "account_id": "YOUR-ACCOUNT-ID", "region": "us-east-1"}'

# Test unified broker with deployment metrics
curl -X POST http://YOUR-BROKER-ALB-URL/ask \
  -H "Content-Type: application/json" \
  -d '{"ask_text": "Get deployment summary for the latest run", "account_id": "YOUR-ACCOUNT-ID", "region": "us-east-1", "metadata": {"repository": "Demo-MCP/mcp-cross-account-pipeline", "run_id": "20490462868"}}'

# Test broker service with ECS tools
curl -X POST http://YOUR-BROKER-ALB-URL/ask \
  -H "Content-Type: application/json" \
  -d '{"ask_text": "List all ECS clusters in my account", "shim_url": "http://YOUR-GATEWAY-ALB-URL", "account_id": "YOUR-ACCOUNT-ID", "region": "us-east-1", "metadata": {"source": "test"}}'
```

## 📁 Repository Structure

```
├── broker-service/           # Unified Nova Pro broker service
│   ├── broker.py            # FastAPI broker with unified MCP integration
│   ├── Dockerfile           # Container configuration
│   └── requirements.txt     # Python dependencies
├── pricingcalc-mcp/         # AWS Pricing Calculator MCP server
│   ├── app.py              # MCP server with 47 AWS services pricing
│   ├── estimator.py        # CloudFormation template cost estimation
│   ├── aws_resources/      # Individual service pricing implementations
│   └── Dockerfile          # Container configuration
├── mcp-gateway/             # MCP protocol gateway
│   ├── gateway.py           # FastAPI gateway routing MCP servers
│   └── Dockerfile           # Container configuration
├── ecs-mcp-server/          # ECS MCP server (embedded)
├── aws-iac-mcp-server/      # Infrastructure MCP server (embedded)
├── deployment-metrics-mcp-server/ # GitHub Actions deployment tracking (external)
├── platform_aws_context/   # AWS context utilities
├── scripts/                 # Deployment task definitions
├── .github/workflows/       # GitHub Actions
└── sample-stack.yaml        # Demo CloudFormation template
```

## 🔧 Key Components

### Broker Service (Enhanced Strands Implementation)
- **🔄 Unified MCP Integration**: Single entry point routing to multiple MCP servers
- **💰 AWS Pricing Integration**: Real-time cost estimation using AWS Pricing API
- **📊 Deployment Metrics**: Real-time GitHub Actions deployment tracking
- **🤖 Enhanced Nova Pro Integration**: Uses `bedrock.converse()` API with streaming timeout resolution
- **🧠 Intelligent Tool Routing**: Routes `pricingcalc_*` to pricing server, `deploy_*` to metrics server, `pr_*` to PR analysis
- **⚡ Tool Caching**: Caches tools at startup for sub-second response times
- **📝 Metadata Processing**: Extracts repository and run_id from GitHub Actions context
- **🎯 Auto Run Selection**: Prioritizes RUNNING deployments for real-time tracking
- **🔄 Stateful Data Handoff**: Internal tool orchestration for complex operations (pr_analyze → pr_get_diff → pr_summarize)
- **🛡️ Advanced Guards**: Pre-execution validation and security controls
- **🚫 Hallucination Prevention**: Fact-based responses with source attribution
- **📋 Correlation ID Tracking**: Full request tracing for debugging and security
- **Performance**: ~1-2s response time with caching optimization, handles large CloudFormation templates without timeout

### AWS Pricing Calculator
- **💲 Real-Time Pricing**: Uses AWS Pricing API for accurate cost calculations
- **📋 47 AWS Services**: EC2, RDS, Lambda, S3, ECS, ALB, CloudWatch, and more
- **🆓 Free Tier Support**: Automatically applies AWS Free Tier allowances
- **📊 CloudFormation Integration**: Estimates costs from YAML/JSON templates
- **🔄 Cross-Account Support**: Price stacks in different AWS accounts
- **📈 Monthly Estimates**: Detailed cost breakdowns per service

### MCP Gateway
- **Server Routing**: Routes requests to appropriate MCP servers (ECS/IAC)
- **Process Management**: Manages MCP server processes and communication
- **Protocol Translation**: Converts HTTP requests to MCP protocol

### MCP Servers (Embedded)
- **ECS Server**: List clusters, services, tasks, troubleshoot deployments
- **IAC Server**: Analyze CloudFormation stacks, troubleshoot deployments
- **Module Resolution**: Fixed PYTHONPATH issues for proper imports

### Infrastructure
- **ECS Fargate**: Serverless container execution
- **Application Load Balancer**: Health checks and routing (2 ALBs: broker + gateway)
- **ECR**: Container image registry
- **CloudWatch**: Logging and monitoring

## 💡 Usage Examples

### PR Comments
```bash
# Analyze infrastructure
/ask List all ECS clusters and their status

# Troubleshoot CloudFormation
/ask Check the CloudFormation stack sample-demo for any issues
```

### Direct API Calls
```bash
# Via Broker (recommended)
curl -X POST http://your-broker-alb-url/ask \
  -H "Content-Type: application/json" \
  -d '{
    "ask_text": "List ECS tasks in cluster mcp-cluster",
    "shim_url": "http://your-gateway-alb-url",
    "account_id": "YOUR-ACCOUNT-ID", 
    "region": "us-east-1",
    "metadata": {"source": "api"}
  }'

# Direct Gateway Call
curl -X POST http://your-gateway-alb-url/call-tool \
  -H "Content-Type: application/json" \
  -d '{
    "server": "ecs",
    "tool": "ecs_call_tool", 
    "params": {
      "tool": "ecs_resource_management",
      "params": {
        "api_operation": "ListClusters",
        "api_params": {},
        "account_id": "YOUR-ACCOUNT-ID",
        "region": "us-east-1"
      }
    }
  }'
```

## 🔧 Configuration Requirements

### Required AWS Resources
- **ECS Cluster**: `mcp-cluster`
- **VPC**: With public/private subnets
- **Security Groups**: Allow HTTP traffic between services
- **IAM Roles**: 
  - `ecsTaskExecutionRole` (ECS task execution)
  - `McpServerTaskRole` (AWS API access)
- **ECR Repositories**: 
  - `broker-service`
  - `mcp-gateway`
  - `github-runner`

### Environment Variables
- **Broker Service**: No special env vars required
- **MCP Gateway**: Uses embedded MCP servers with fixed PYTHONPATH
- **GitHub Actions**: Uses repository secrets for AWS credentials

## 🚨 Troubleshooting

### Common Issues

1. **Module Import Errors (Fixed)**
   - **Issue**: `ModuleNotFoundError: No module named 'awslabs.aws_iac_mcp_server'`
   - **Solution**: Gateway now uses explicit PYTHONPATH for IAC server: `env PYTHONPATH=/app/aws-iac-mcp-server:/app python /app/aws-iac-mcp-server/awslabs/aws_iac_mcp_server/server.py`

2. **Gateway Health Check Failures**
   - Check ALB target group health
   - Verify security group allows traffic on port 8080
   - Check ECS service status

3. **Broker Timeout Issues**
   - Increased timeout to 2 minutes for complex operations
   - Check gateway ALB connectivity from broker

### Debug Commands
```bash
# Check ECS service status
aws ecs describe-services --cluster mcp-cluster --services broker-service mcp-gateway

# View logs
aws logs get-log-events --log-group-name /ecs/broker-service --log-stream-name LATEST
aws logs get-log-events --log-group-name /ecs/mcp-gateway --log-stream-name LATEST

# Test ALB health
curl http://your-broker-alb-url/health
curl http://your-gateway-alb-url/health

# Test MCP servers directly
aws ecs run-task --cluster mcp-cluster --task-definition github-runner:3 --launch-type FARGATE --network-configuration "awsvpcConfiguration={assignPublicIp=ENABLED,securityGroups=[sg-YOUR-ID],subnets=[subnet-YOUR-ID]}" --overrides '{"containerOverrides":[{"name":"github-runner","command":["curl","-X","POST","http://YOUR-GATEWAY-ALB/call-tool","-H","Content-Type: application/json","-d","{\"server\":\"ecs\",\"tool\":\"ecs_call_tool\",\"params\":{\"tool\":\"ecs_resource_management\",\"params\":{\"api_operation\":\"ListClusters\",\"api_params\":{},\"account_id\":\"YOUR-ACCOUNT-ID\",\"region\":\"us-east-1\"}}}"]}]}'
```

## 🔄 Development Workflow

1. **Local Testing**: Test MCP servers individually before deployment
2. **Build Images**: Build and push to ECR
3. **Deploy Services**: Update ECS services with new task definitions
4. **Test Integration**: Verify broker → gateway → MCP server flow
5. **GitHub Integration**: Test via PR comments

## 🚀 Deployment Metrics Integration

The unified broker now includes real-time GitHub Actions deployment tracking:

### Available Deployment Tools

- **`deploy_find_latest`**: Find latest deployment runs for a repository
- **`deploy_get_summary`**: Get detailed deployment summary with timing and status
- **`deploy_get_run`**: Get specific deployment run details
- **`deploy_get_steps`**: Get deployment step details and logs
- **`deploy_find_active`**: Find currently running deployments

### Usage Examples

```bash
# Get latest deployment for current repository (uses metadata)
"Get the latest deployment summary"

# Get specific deployment details
"Get deployment summary for run 20490462868"

# Find running deployments
"Show me any deployments currently running"

# Get deployment with steps
"Get deployment summary with run and step details for run_id 20490462868"
```

### Metadata Integration

When called from GitHub Actions, the broker automatically uses:
- **Repository**: From `github.repository` context
- **Run ID**: From `github.run_id` context
- **Auto-selection**: Prioritizes RUNNING deployments when no run_id specified

## 📈 Monitoring

- **CloudWatch Logs**: 
  - `/ecs/broker-service` - Broker service logs with detailed tool calling
  - `/ecs/mcp-gateway` - Gateway routing and MCP server management
  - `/ecs/github-runner` - Test execution logs
- **ECS Metrics**: CPU, memory, task health for both services
- **ALB Metrics**: Request count, latency, errors for both ALBs

## 🤝 Contributing

1. Fork the repository
2. Update configuration files with your AWS account details
3. Test locally using the debug commands above
4. Submit pull request
5. Comment `/ask test the system` to trigger validation

## 📄 License

MIT License - see LICENSE file for details
