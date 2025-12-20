# Test MCP Cross-Account Analysis

This PR tests the MCP cross-account pipeline functionality.

## Test Commands
- `/analyze-infrastructure stack=test-stack account=500330120558`
- `/troubleshoot-ecs service=test-service account=500330120558`1
- `/ask what ECS services are running?`

## Expected Results
The GitHub Actions workflow should:
1. Parse the PR comment
2. Execute MCP servers with cross-account parameters  
3. Assume role in target account
4. Perform AWS API analysis
5. Post results back to this PR

## Architecture
```
GitHub PR Comment → Self-Hosted Runner → MCP Servers → AssumeRole → AWS APIs
```
