#!/bin/bash
# Advanced Kiro Deployment Commands

# Rollback shortcuts
alias krollback='/System/Volumes/Data/Users/suhaibchisti/.local/bin/kiro-cli chat "rollback last deployment"'
alias krollback-prod='/System/Volumes/Data/Users/suhaibchisti/.local/bin/kiro-cli chat "rollback production to last successful"'

# Multi-environment deployment
alias kdeploy-pipeline='/System/Volumes/Data/Users/suhaibchisti/.local/bin/kiro-cli chat "deploy to staging then production with approval"'

# Status and monitoring
alias kstatus='/System/Volumes/Data/Users/suhaibchisti/.local/bin/kiro-cli chat "show latest deployment status"'
alias klogs='/System/Volumes/Data/Users/suhaibchisti/.local/bin/kiro-cli chat "show deployment logs for latest run"'

# Emergency commands
alias kemergency-stop='/System/Volumes/Data/Users/suhaibchisti/.local/bin/kiro-cli chat "stop current deployment"'
alias kemergency-rollback='/System/Volumes/Data/Users/suhaibchisti/.local/bin/kiro-cli chat "emergency rollback production"'

# Approval workflow
alias kapprove='/System/Volumes/Data/Users/suhaibchisti/.local/bin/kiro-cli chat "approve pending deployment"'
alias kreject='/System/Volumes/Data/Users/suhaibchisti/.local/bin/kiro-cli chat "reject pending deployment"'

echo "🚀 Advanced Kiro deployment commands loaded!"
echo ""
echo "Available commands:"
echo "  📦 Deployment:"
echo "    kdeploy              - Smart deploy"
echo "    kdeploy-staging      - Deploy to staging"  
echo "    kdeploy-prod         - Deploy to production"
echo "    kdeploy-pipeline     - Multi-env with approval"
echo ""
echo "  🔄 Rollback:"
echo "    krollback            - Rollback last deployment"
echo "    krollback-prod       - Rollback production"
echo ""
echo "  📊 Monitoring:"
echo "    kstatus              - Deployment status"
echo "    klogs                - Deployment logs"
echo ""
echo "  ⚡ Emergency:"
echo "    kemergency-stop      - Stop current deployment"
echo "    kemergency-rollback  - Emergency rollback"
echo ""
echo "  ✅ Approval:"
echo "    kapprove             - Approve pending deployment"
echo "    kreject              - Reject pending deployment"
