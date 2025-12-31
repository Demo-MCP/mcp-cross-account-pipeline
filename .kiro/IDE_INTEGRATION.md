# Kiro IDE Integration

Universal IDE integration for seamless deployment across any editor.

## Quick Setup

```bash
# Run in your project root
chmod +x .kiro/setup-ide.sh
./.kiro/setup-ide.sh
```

## IDE-Specific Setup

### VS Code / Cursor
- **Tasks**: `Cmd+Shift+P` → "Tasks: Run Task" → "Deploy with Kiro"
- **Keybinding**: Add to `keybindings.json`:
```json
{
    "key": "cmd+shift+d",
    "command": "workbench.action.tasks.runTask",
    "args": "Deploy with Kiro"
}
```

### Terminal / Any IDE
```bash
kdeploy              # Deploy with smart defaults
kdeploy-staging      # Deploy to staging
kdeploy-prod         # Deploy to production
```

### Git Integration
- **Auto-deploy**: Enabled via `.kiro/deploy.json` → `auto_deploy: true`
- **Manual prompt**: Shows after every `git push`

## IDE Extensions (Future)

### VS Code Extension Features
- Deploy button in status bar
- Real-time deployment progress
- Branch-aware deploy targets
- One-click rollback

### JetBrains Plugin Features  
- Deploy action in toolbar
- Integrated deployment logs
- Smart environment detection

## Configuration

### Enable Auto-Deploy
```json
// .kiro/deploy.json
{
  "environments": {
    "dev": {
      "auto_deploy": true
    }
  }
}
```

### Custom Keybindings
```json
// VS Code keybindings.json
[
  {
    "key": "cmd+d",
    "command": "workbench.action.tasks.runTask", 
    "args": "Deploy with Kiro"
  }
]
```

## Workflow Examples

### Development Flow
1. `git commit -m "Add feature"`
2. `git push` → Auto-deploy prompt appears
3. Choose: Deploy now or skip

### Production Flow  
1. Merge to `main` branch
2. `git push` → Auto-deploy to production (if enabled)
3. Real-time progress in IDE

### Emergency Deploy
1. `Cmd+Shift+D` (VS Code) or `kdeploy` (terminal)
2. Instant deployment with current context
