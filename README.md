# MCP Cross-Account Pipeline

End-to-end AWS infrastructure analysis pipeline using Model Context Protocol (MCP) servers with cross-account support and Nova Pro AI integration.

## 🏗️ Architecture

```
GitHub PR Comment → GitHub Actions → ECS Fargate → MCP Servers → AssumeRole → AWS APIs → Nova Pro Analysis
```

## ✨ Features

* **Nova Pro Integration**: Advanced AI tool calling with agentic loops
* **Cross-Account Support**: Dynamic role assumption per API call
* **MCP Protocol**: Standardized AI tool integration
* **ECS Fargate**: Serverless container execution
* **GitHub Integration**: PR comment triggers and responses
* **Multi-Service**: ECS and Infrastructure-as-Code analysis

## 🚀 Quick Deploy from Scratch

### Prerequisites
- AWS CLI configured with admin permissions
- Docker installed
- GitHub repository with Actions enabled

### 1. Setup IAM Roles
```bash
# Create cross-account IAM roles
./scripts/setup-iam-roles.sh
```

### 2. Build and Push Images
```bash
# Build broker service
cd broker-service
docker build -t broker-service .
docker tag broker-service:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/broker-service:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/broker-service:latest

# Build MCP servers
cd ../ecs-mcp-server
docker build -t ecs-mcp-server .
docker tag ecs-mcp-server:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/ecs-mcp-server:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/ecs-mcp-server:latest
```

### 3. Deploy Infrastructure
```bash
# Deploy ECS cluster and ALB
aws cloudformation deploy \
  --template-file ecs-mcp-server/awslabs/ecs_mcp_server/templates/ecs_infrastructure.json \
  --stack-name mcp-infrastructure \
  --capabilities CAPABILITY_IAM

# Register task definitions
aws ecs register-task-definition --cli-input-json file://broker-task.json

# Deploy services
./scripts/deploy-ecs-service.sh
```

### 4. Configure GitHub Actions
```bash
# Set repository secrets:
# - AWS_ACCESS_KEY_ID
# - AWS_SECRET_ACCESS_KEY  
# - AWS_REGION (us-east-1)
# - GITHUB_TOKEN
```

### 5. Test End-to-End
```bash
# Test the pipeline
./scripts/test-pipeline.sh

# Or comment on any PR:
# /analyze-infrastructure
# /troubleshoot-ecs
```

## 📁 Repository Structure

```
├── broker-service/           # Nova Pro broker service
│   ├── app.py               # FastAPI broker with Nova Pro integration
│   ├── Dockerfile           # Container configuration
│   └── broker-task.json     # ECS task definition
├── ecs-mcp-server/          # ECS MCP server
├── aws-iac-mcp-server/      # Infrastructure MCP server
├── mcp-gateway/             # MCP protocol gateway
├── scripts/                 # Deployment scripts
├── .github/workflows/       # GitHub Actions
└── sample-stack.yaml        # Demo CloudFormation template
```

## 🔧 Key Components

### Broker Service
- **Nova Pro Integration**: Uses `bedrock.converse()` API with agentic loops
- **Tool Calling**: Supports ECS and IAC MCP servers
- **Performance**: ~10.6s response time, 2-iteration completion

### MCP Servers
- **ECS Server**: List clusters, services, tasks, troubleshoot deployments
- **IAC Server**: Analyze CloudFormation, CDK, Terraform templates
- **Cross-Account**: Dynamic role assumption per request

### Infrastructure
- **ECS Fargate**: Serverless container execution
- **Application Load Balancer**: Health checks and routing
- **ECR**: Container image registry
- **CloudWatch**: Logging and monitoring

## 💡 Usage Examples

### PR Comments
```bash
# Analyze infrastructure
/analyze-infrastructure

# Troubleshoot ECS issues  
/troubleshoot-ecs cluster-name

# Cross-account analysis
/cross-account 123456789012 analyze-infrastructure
```

### Direct API Calls
```bash
curl -X POST http://your-alb-url/ask \
  -H "Content-Type: application/json" \
  -d '{
    "ask_text": "List ECS tasks in cluster mcp-cluster",
    "account_id": "500330120558", 
    "region": "us-east-1"
  }'
```

## 🔒 Security

- **IAM Roles**: Least privilege access with cross-account trust
- **VPC**: Private subnets with NAT gateway
- **ALB**: HTTPS termination and security groups
- **Secrets**: GitHub Actions secrets for credentials

## 💰 Cost Optimization

- **Fargate**: Pay-per-use, no idle costs
- **Spot Instances**: Optional for development
- **Auto Scaling**: Scale to zero when not in use
- **Estimated Cost**: ~$30/month continuous, ~$0.04/hour on-demand

## 🚨 Troubleshooting

### Common Issues
1. **Tool Calling Errors**: Check schema alignment between broker and MCP servers
2. **Health Check Failures**: Verify ALB target group configuration
3. **Cross-Account Access**: Ensure IAM roles have proper trust relationships
4. **Nova Pro Errors**: Check inference parameters and token limits

### Debug Commands
```bash
# Check ECS service status
aws ecs describe-services --cluster mcp-cluster --services broker-service

# View logs
aws logs get-log-events --log-group-name /ecs/broker-service

# Test ALB health
curl http://your-alb-url/health
```

## 🔄 Development Workflow

1. **Local Testing**: Use `docker-compose` for local development
2. **PR Creation**: Triggers GitHub Actions pipeline
3. **Deployment**: Automatic ECS service updates
4. **Monitoring**: CloudWatch logs and metrics
5. **Rollback**: ECS service revision management

## 📈 Monitoring

- **CloudWatch Logs**: Application and container logs
- **ECS Metrics**: CPU, memory, task health
- **ALB Metrics**: Request count, latency, errors
- **Custom Metrics**: Tool calling performance, Nova Pro usage

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Test with `./scripts/test-pipeline.sh`
4. Submit pull request
5. Comment `/test` to trigger validation

## 📄 License

MIT License - see LICENSE file for details

## Metadata Support

### Recent Updates (Tag: with-metadata-support)

**Broker Service**
- Added `metadata` field to `AskRequest` model
- Updated `call_bedrock()` to pass `account_id`, `region`, and `metadata` to MCP tools
- Enhanced tool calls to include metadata context

**ECS MCP Server** 
- Added `_metadata` parameter to `ecs_resource_management` tool
- Supports metadata flow through `account_context` for cross-account operations
- Enables tracking of GitHub actor, repo, PR number, and run ID

**Benefits**
- End-to-end metadata tracking from GitHub workflows to AWS resources
- Enhanced auditing and context-aware operations
- Better troubleshooting with request traceability
