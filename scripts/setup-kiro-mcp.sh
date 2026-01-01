#!/bin/bash

# Kiro MCP Server Setup Script
# Configures AWS MCP Broker as a Kiro agent

set -e

echo "🔧 Setting up Kiro MCP Server for AWS Broker..."

# Create Kiro config directory if it doesn't exist
KIRO_CONFIG_DIR="$HOME/.config/kiro"
echo "📁 Creating Kiro config directory: $KIRO_CONFIG_DIR"
mkdir -p "$KIRO_CONFIG_DIR"

# Backup existing config if it exists
if [ -f "$KIRO_CONFIG_DIR/mcp_servers.json" ]; then
    echo "💾 Backing up existing config to mcp_servers.json.backup"
    cp "$KIRO_CONFIG_DIR/mcp_servers.json" "$KIRO_CONFIG_DIR/mcp_servers.json.backup"
fi

# Create MCP server configuration
echo "⚙️ Creating MCP server configuration..."
cat > "$KIRO_CONFIG_DIR/mcp_servers.json" << 'EOF'
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
EOF

echo "✅ MCP server configuration created at: $KIRO_CONFIG_DIR/mcp_servers.json"

# Test AWS credentials
echo ""
echo "🔐 Testing AWS credentials..."
if aws sts get-caller-identity > /dev/null 2>&1; then
    echo "✅ AWS credentials are configured"
    
    # Test role assumption
    echo "🎭 Testing DevMcpInvokeRole assumption..."
    if aws sts assume-role \
        --role-arn "arn:aws:iam::500330120558:role/DevMcpInvokeRole" \
        --role-session-name "kiro-setup-test" \
        --external-id "dev-mcp-access" \
        --output text --query 'Credentials.AccessKeyId' > /dev/null 2>&1; then
        echo "✅ Successfully can assume DevMcpInvokeRole"
    else
        echo "❌ Cannot assume DevMcpInvokeRole - check your AWS permissions"
        echo "   You need permission to assume: arn:aws:iam::500330120558:role/DevMcpInvokeRole"
    fi
else
    echo "❌ AWS credentials not configured"
    echo "   Run: aws configure"
fi

# Test API Gateway endpoint
echo ""
echo "🌐 Testing API Gateway endpoint..."
if curl -s --max-time 10 "https://d0yrd186v6.execute-api.us-east-1.amazonaws.com/prod/tools" > /dev/null; then
    echo "✅ API Gateway endpoint is reachable"
    
    # Show available tools
    echo ""
    echo "🛠️ Available tools:"
    curl -s "https://d0yrd186v6.execute-api.us-east-1.amazonaws.com/prod/tools" | jq -r '.user_tools[]' | sed 's/^/  - /'
else
    echo "❌ API Gateway endpoint is not reachable"
fi

echo ""
echo "🎉 Kiro MCP setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Restart Kiro CLI if it's running"
echo "2. Run 'kiro-cli chat' to start a new session"
echo "3. Type '/tools' to see if AWS tools are available"
echo "4. Test with: 'List ECS clusters in account 500330120558'"
echo ""
echo "📖 For more details, see: KIRO_INTEGRATION.md"
