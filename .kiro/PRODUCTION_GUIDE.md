# Production Deployment Guide

Complete guide for production-ready deployments with Kiro MCP.

## 🚀 Deployment Workflows

### Standard Deployment
```bash
# Smart deployment (uses branch context)
kiro "deploy"

# Specific environment
kiro "deploy to production"
```

### Multi-Environment Pipeline
```bash
# Deploy to staging, then production with approval
kiro "deploy to staging then production with approval"

# Custom pipeline
kiro "deploy to dev then staging then production"
```

### Rollback Operations
```bash
# Rollback last deployment
kiro "rollback"

# Rollback to specific version
kiro "rollback to run_id 12345"

# Emergency rollback
kiro "emergency rollback production"
```

## 🔒 Approval Workflows

### Production Approvals
Production deployments require approval when `require_approval: true`:

1. **Deploy Request**: `kiro "deploy to production"`
2. **Approval Required**: Deployment pauses, notifications sent
3. **Approve**: `kiro "approve pending deployment"`
4. **Deploy**: Continues automatically after approval

### Approval Policies
```json
// .kiro/deploy.json
{
  "deployment_policies": {
    "production": {
      "require_approval": true,
      "approvers": ["@devops-team", "@tech-leads"],
      "business_hours_only": true
    }
  }
}
```

## 📊 Monitoring & Observability

### Real-Time Status
```bash
kiro "show deployment status"           # Current deployments
kiro "show deployment logs"             # Recent logs
kiro "show ECS service health"          # Service status
kiro "show CloudFormation stack status" # Infrastructure status
```

### Auto-Diagnostics
When deployments fail, Kiro automatically:
- ✅ Checks CloudFormation stack events
- ✅ Analyzes ECS service health
- ✅ Reviews task failures and logs
- ✅ Suggests specific remediation steps

## 🔔 Notifications

### Slack Integration
```json
{
  "notifications": {
    "slack_webhook": "https://hooks.slack.com/services/YOUR/WEBHOOK",
    "notify_on": ["success", "failure", "approval_required"]
  }
}
```

### Notification Events
- **Deployment Started**: "🚀 Deploying to production..."
- **Approval Required**: "⏳ Production deployment needs approval"
- **Deployment Success**: "✅ Production deployment completed"
- **Deployment Failed**: "❌ Production deployment failed - auto-diagnosis attached"

## 🛡️ Safety Features

### Automatic Rollback
```json
{
  "deployment_policies": {
    "staging": {
      "auto_rollback_on_failure": true
    }
  }
}
```

### Business Hours Protection
```json
{
  "deployment_policies": {
    "production": {
      "business_hours_only": true,
      "timezone": "America/New_York",
      "hours": "09:00-17:00",
      "days": ["monday", "tuesday", "wednesday", "thursday", "friday"]
    }
  }
}
```

### Rollback Windows
```json
{
  "deployment_policies": {
    "production": {
      "rollback_window": "24h"
    }
  }
}
```

## 🚨 Emergency Procedures

### Emergency Stop
```bash
kiro "stop current deployment"
```

### Emergency Rollback
```bash
kiro "emergency rollback production"
```

### Health Check Override
```bash
kiro "deploy to production skip health checks"
```

## 📈 Advanced Features

### Blue-Green Deployments
```bash
kiro "deploy to production using blue-green"
```

### Canary Deployments
```bash
kiro "deploy to production with 10% canary"
```

### Scheduled Deployments
```bash
kiro "schedule deployment to production at 2am EST"
```

## 🔧 Configuration Examples

### Complete Production Config
```json
{
  "environments": {
    "production": {
      "account": "prod",
      "region": "us-east-1",
      "auto_deploy": false,
      "require_approval": true
    }
  },
  "deployment_policies": {
    "production": {
      "require_approval": true,
      "approvers": ["@devops-team"],
      "business_hours_only": true,
      "rollback_window": "24h",
      "auto_rollback_on_failure": false
    }
  },
  "notifications": {
    "slack_webhook": "https://hooks.slack.com/...",
    "notify_on": ["success", "failure", "approval_required"],
    "email": ["devops@company.com"]
  },
  "health_checks": {
    "timeout": 600,
    "endpoints": ["/health", "/ready", "/metrics"]
  }
}
```

## 🎯 Best Practices

1. **Always test in staging first**
2. **Use approval workflows for production**
3. **Monitor deployments in real-time**
4. **Keep rollback plans ready**
5. **Configure proper notifications**
6. **Test rollback procedures regularly**
7. **Use business hours protection**
8. **Maintain deployment documentation**
