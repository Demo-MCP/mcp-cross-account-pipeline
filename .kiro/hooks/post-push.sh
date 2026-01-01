#!/bin/bash
# Git post-push hook for automatic deployment prompts
# Place in .git/hooks/post-push or use .kiro/hooks/post-push.sh

BRANCH=$(git branch --show-current)
REPO=$(basename -s .git $(git config --get remote.origin.url))

# Load deployment config
CONFIG_FILE=".kiro/deploy.json"
AUTO_DEPLOY=false

if [ -f "$CONFIG_FILE" ]; then
    # Check if auto_deploy is enabled for this branch
    AUTO_DEPLOY=$(cat "$CONFIG_FILE" | python3 -c "
import json, sys
try:
    config = json.load(sys.stdin)
    environments = config.get('environments', {})
    branch_mapping = config.get('branch_mapping', {})
    env = branch_mapping.get('$BRANCH', 'staging')
    env_config = environments.get(env, {})
    print(env_config.get('auto_deploy', False))
except:
    print(False)
" 2>/dev/null)
fi

echo "🚀 Push completed to $REPO ($BRANCH)"

if [ "$AUTO_DEPLOY" = "True" ]; then
    echo "🤖 Auto-deploy enabled for this branch"
    echo "⏳ Triggering deployment..."
    
    # Use full path to Kiro CLI
    if [ -f "/System/Volumes/Data/Users/suhaibchisti/.local/bin/kiro-cli" ]; then
        /System/Volumes/Data/Users/suhaibchisti/.local/bin/kiro-cli chat "deploy" --no-interactive
    elif command -v kiro-cli >/dev/null 2>&1; then
        kiro-cli chat "deploy" --no-interactive
    else
        echo "💡 Kiro CLI not found. Run manually: kiro 'deploy'"
    fi
else
    echo "💡 Deploy manually with: kiro 'deploy'"
    echo "   Or enable auto_deploy in .kiro/deploy.json"
fi
