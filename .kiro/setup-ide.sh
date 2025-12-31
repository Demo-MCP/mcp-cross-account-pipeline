#!/bin/bash
# IDE Integration Setup Script
# Sets up Git hooks and IDE shortcuts for seamless deployment

echo "🔧 Setting up Kiro IDE Integration..."

# Make hooks executable
chmod +x .kiro/hooks/post-push.sh

# Install Git hook
if [ -d ".git/hooks" ]; then
    echo "📎 Installing Git post-push hook..."
    cp .kiro/hooks/post-push.sh .git/hooks/post-push
    chmod +x .git/hooks/post-push
    echo "✅ Git hook installed"
else
    echo "⚠️  Not a Git repository - skipping Git hook"
fi

# Create VS Code tasks (if .vscode exists)
if [ -d ".vscode" ] || [ "$1" = "--vscode" ]; then
    mkdir -p .vscode
    echo "📝 Creating VS Code tasks..."
    
    cat > .vscode/tasks.json << 'EOF'
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Deploy with Kiro",
            "type": "shell",
            "command": "/System/Volumes/Data/Users/suhaibchisti/.local/bin/kiro-cli",
            "args": ["chat", "deploy"],
            "group": "build",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "new"
            },
            "problemMatcher": []
        },
        {
            "label": "Deploy to Staging",
            "type": "shell", 
            "command": "/System/Volumes/Data/Users/suhaibchisti/.local/bin/kiro-cli",
            "args": ["chat", "deploy to staging"],
            "group": "build"
        },
        {
            "label": "Deploy to Production",
            "type": "shell",
            "command": "/System/Volumes/Data/Users/suhaibchisti/.local/bin/kiro-cli", 
            "args": ["chat", "deploy to production"],
            "group": "build"
        }
    ]
}
EOF
    echo "✅ VS Code tasks created"
fi

# Create shell aliases
echo "📋 Creating shell aliases..."
cat >> ~/.bashrc << 'EOF' 2>/dev/null || true

# Kiro deployment aliases
alias kdeploy='/System/Volumes/Data/Users/suhaibchisti/.local/bin/kiro-cli chat "deploy"'
alias kdeploy-staging='/System/Volumes/Data/Users/suhaibchisti/.local/bin/kiro-cli chat "deploy to staging"'
alias kdeploy-prod='/System/Volumes/Data/Users/suhaibchisti/.local/bin/kiro-cli chat "deploy to production"'
EOF

cat >> ~/.zshrc << 'EOF' 2>/dev/null || true

# Kiro deployment aliases  
alias kdeploy='/System/Volumes/Data/Users/suhaibchisti/.local/bin/kiro-cli chat "deploy"'
alias kdeploy-staging='/System/Volumes/Data/Users/suhaibchisti/.local/bin/kiro-cli chat "deploy to staging"'
alias kdeploy-prod='/System/Volumes/Data/Users/suhaibchisti/.local/bin/kiro-cli chat "deploy to production"'
EOF

echo "✅ Shell aliases added"

echo ""
echo "🎉 IDE Integration Setup Complete!"
echo ""
echo "Available shortcuts:"
echo "  📋 VS Code: Cmd+Shift+P → 'Tasks: Run Task' → 'Deploy with Kiro'"
echo "  🖥️  Terminal: kdeploy, kdeploy-staging, kdeploy-prod"
echo "  🔄 Git: Auto-deploy on push (if enabled in .kiro/deploy.json)"
echo ""
echo "💡 Restart your terminal to use the new aliases"
