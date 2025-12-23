# MCP Cross-Account Pipeline

End-to-end AWS infrastructure analysis pipeline using Model Context Protocol (MCP) servers with cross-account support and Nova Pro AI integration.

## 🏗️ Architecture

```
GitHub PR Comment → GitHub Actions → Broker Service → MCP Gateway → MCP Servers → AWS APIs → Nova Pro Analysis
```

## ✨ Features

* **Nova Pro Integration**: Advanced AI tool calling with agentic loops
* **Cross-Account Support**: Dynamic role assumption per API call
* **MCP Protocol**: Standardized AI tool integration with gateway routing
* **ECS Fargate**: Serverless container execution
* **GitHub Integration**: PR comment triggers and responses
* **Multi-Service**: ECS and Infrastructure-as-Code analysis

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

# Test broker service
curl -X POST http://YOUR-BROKER-ALB-URL/ask \
  -H "Content-Type: application/json" \
  -d '{"ask_text": "List all ECS clusters in my account", "shim_url": "http://YOUR-GATEWAY-ALB-URL", "account_id": "YOUR-ACCOUNT-ID", "region": "us-east-1", "metadata": {"source": "test"}}'
```

## 📁 Repository Structure

```
├── broker-service/           # Nova Pro broker service
│   ├── broker.py            # FastAPI broker with Nova Pro integration
│   ├── Dockerfile           # Container configuration
│   └── requirements.txt     # Python dependencies
├── mcp-gateway/             # MCP protocol gateway
│   ├── gateway.py           # FastAPI gateway routing MCP servers
│   └── Dockerfile           # Container configuration
├── ecs-mcp-server/          # ECS MCP server (embedded)
├── aws-iac-mcp-server/      # Infrastructure MCP server (embedded)
├── platform_aws_context/   # AWS context utilities
├── scripts/                 # Deployment task definitions
├── .github/workflows/       # GitHub Actions
└── sample-stack.yaml        # Demo CloudFormation template
```

## 🔧 Key Components

### Broker Service
- **Nova Pro Integration**: Uses `bedrock.converse()` API with agentic loops
- **Tool Calling**: Routes to ECS and IAC MCP servers via gateway
- **Performance**: ~4-5s response time with proper routing

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
