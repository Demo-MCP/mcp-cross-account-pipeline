#!/usr/bin/env python3
import asyncio
import json
import os
import subprocess
import boto3
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio

server = Server("aws-mcp-broker")

def get_git_context():
    """Auto-detect Git repository context including PR info"""
    context = {
        'repository': 'unknown',
        'branch': 'unknown', 
        'commit': 'unknown',
        'actor': os.environ.get('USER', 'local-user'),
        'pr_number': None,
        'deploy_config': {}
    }
    
    try:
        # Get current repo info
        try:
            repo_url = subprocess.check_output(['git', 'config', '--get', 'remote.origin.url'], 
                                             stderr=subprocess.DEVNULL).decode().strip()
            
            # Extract repo name from URL
            if 'github.com' in repo_url:
                if repo_url.startswith('git@'):
                    # SSH format: git@github.com:owner/repo.git
                    context['repository'] = repo_url.split(':')[1].replace('.git', '')
                else:
                    # HTTPS format: https://github.com/owner/repo.git
                    context['repository'] = repo_url.split('github.com/')[-1].replace('.git', '')
            else:
                context['repository'] = os.path.basename(os.getcwd())
                
            print(f"[DEBUG] Repository: {context['repository']}")
        except Exception as e:
            print(f"[DEBUG] Failed to get repository: {e}")
        
        try:
            context['branch'] = subprocess.check_output(['git', 'branch', '--show-current'], 
                                           stderr=subprocess.DEVNULL).decode().strip()
            print(f"[DEBUG] Branch: {context['branch']}")
        except Exception as e:
            print(f"[DEBUG] Failed to get branch: {e}")
        
        try:
            context['commit'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], 
                                           stderr=subprocess.DEVNULL).decode().strip()
            print(f"[DEBUG] Commit: {context['commit'][:8]}")
        except Exception as e:
            print(f"[DEBUG] Failed to get commit: {e}")
        
        # Try to detect PR number from branch or recent commits
        try:
            # Method 1: Check if branch follows PR naming convention
            if context['branch'].startswith('pr-') or context['branch'].startswith('pull-'):
                pr_num = ''.join(filter(str.isdigit, context['branch']))
                if pr_num:
                    context['pr_number'] = int(pr_num)
            
            # Method 2: Use GitHub CLI to find PR for current branch
            if not context['pr_number'] and context['branch'] not in ['main', 'master', 'unknown']:
                try:
                    pr_list = subprocess.check_output([
                        'gh', 'pr', 'list', '--head', context['branch'], '--json', 'number'
                    ], stderr=subprocess.DEVNULL).decode().strip()
                    
                    import json
                    prs = json.loads(pr_list)
                    if prs and len(prs) > 0:
                        context['pr_number'] = int(prs[0].get('number'))
                        print(f"[DEBUG] Found PR: {context['pr_number']}")
                except Exception as e:
                    print(f"[DEBUG] Failed to get PR via gh: {e}")
                
        except Exception as e:
            print(f"[DEBUG] PR detection failed: {e}")
        
        # Load deployment configuration
        try:
            context['deploy_config'] = load_deploy_config()
            print(f"[DEBUG] Loaded deploy config")
        except Exception as e:
            print(f"[DEBUG] Failed to load deploy config: {e}")
            
        return context
        
    except Exception as e:
        print(f"[DEBUG] Git context detection failed: {e}")
        return context

def load_deploy_config():
    """Load .kiro/deploy.json configuration"""
    import json
    
    config_paths = [
        '.kiro/deploy.json',
        '../.kiro/deploy.json',
        '../../.kiro/deploy.json'
    ]
    
    for config_path in config_paths:
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    return json.load(f)
        except:
            continue
    
    # Default configuration
    return {
        "environments": {
            "main": {"account": "prod", "region": "us-east-1"},
            "dev": {"account": "staging", "region": "us-east-1"},
            "staging": {"account": "staging", "region": "us-west-2"}
        },
        "branch_mapping": {
            "main": "production",
            "dev": "staging", 
            "staging": "staging"
        }
    }

def make_broker_request(tool_name, arguments, context):
    """Make authenticated request to AWS MCP Broker"""
    try:
        sts = boto3.client('sts')
        role = sts.assume_role(
            RoleArn=os.environ['AWS_ROLE_ARN'],
            RoleSessionName='kiro-mcp',
            ExternalId=os.environ['AWS_ROLE_EXTERNAL_ID']
        )
        
        creds = role['Credentials']
        url = f"{os.environ['FETCH_BASE_URL']}/ask"
        
        # Format as ask_text with context
        query = arguments.get('query', '')
        ask_text = f"Repository: {context['repository']}, Branch: {context['branch']}, User: {context['actor']}. Use {tool_name}: {query}"
        
        # Build metadata with git context
        metadata = {
            "repository": context['repository'],
            "branch": context['branch'],
            "actor": context['actor']
        }
        
        # Add pr_number to metadata if available
        if context.get('pr_number'):
            metadata["pr_number"] = context['pr_number']
        
        payload = {
            "ask_text": ask_text,
            "metadata": metadata
        }
        
        request = AWSRequest(
            method='POST',
            url=url,
            data=json.dumps(payload),
            headers={'Content-Type': 'application/json'}
        )
        
        session = boto3.Session(
            aws_access_key_id=creds['AccessKeyId'],
            aws_secret_access_key=creds['SecretAccessKey'],
            aws_session_token=creds['SessionToken']
        )
        
        SigV4Auth(session.get_credentials(), 'execute-api', os.environ['AWS_REGION']).add_auth(request)
        
        response = requests.post(url, data=request.body, headers=dict(request.headers), timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            return result.get('final_response', str(result))
        else:
            return f"Error {response.status_code}: {response.text}"
            
    except Exception as e:
        return f"Error: {str(e)}"

@server.list_tools()
async def list_tools():
    """Dynamically fetch tools from broker"""
    try:
        tools_response = requests.get(f"{os.environ['FETCH_BASE_URL']}/tools", timeout=10)
        tools_data = tools_response.json()
        
        git_context = get_git_context()
        context_info = f"\nAuto-context: {git_context['repository']} ({git_context['branch']}) by {git_context['actor']}"
        
        mcp_tools = []
        
        # Get user tools from the response
        user_tools = tools_data.get('user_tools', [])
        
        # Add local-only tools
        local_tools = ["deploy_local"]
        all_tools = user_tools + local_tools
        
        for tool_name in all_tools:
            # Create enhanced tool descriptions with smart defaults
            if tool_name == "deploy_local":
                config = git_context.get('deploy_config', {})
                branch = git_context['branch']
                
                # Determine smart environment
                branch_mapping = config.get('branch_mapping', {})
                smart_env = branch_mapping.get(branch, "staging")
                
                # Get region for environment
                environments = config.get('environments', {})
                env_config = environments.get(smart_env, {})
                smart_region = env_config.get('region', 'us-east-1')
                
                description = f"🚀 Local Deploy - Zero-config deployment\n"
                description += f"Current: {git_context['repository']} ({branch})"
                if git_context.get('pr_number'):
                    description += f" PR #{git_context['pr_number']}"
                description += f"\nAuto-detected: {smart_env} environment in {smart_region}"
                description += f"\nJust say: 'deploy local' (uses smart defaults)"
                
                mcp_tools.append(Tool(
                    name=tool_name,
                    description=description,
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "repository": {"type": "string", "description": f"Repository (auto: {git_context['repository']})"},
                            "environment": {"type": "string", "description": f"Environment (auto: {smart_env})"},
                            "region": {"type": "string", "description": f"AWS region (auto: {smart_region})"},
                            "pr_number": {"type": "string", "description": f"PR number (auto: {git_context.get('pr_number', 'detected from branch')})"}
                        },
                        "required": []
                    }
                ))
            else:
                description = f"AWS {tool_name.replace('_', ' ').title()}" + context_info
            
            mcp_tools.append(Tool(
                name=tool_name,
                description=description,
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string", 
                            "description": f"Query or parameters for {tool_name}"
                        }
                    },
                    "required": ["query"]
                }
            ))
        
        return mcp_tools
        
    except Exception as e:
        print(f"[ERROR] list_tools failed: {str(e)}")
        import traceback
        traceback.print_exc()
        # Fallback: return basic tools if cloud fetch fails
        return [
            Tool(
                name="deploy_local",
                description="Deploy locally by posting deploy comment to PR",
                inputSchema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
            ),
            Tool(
                name="deploy_status", 
                description="Check deployment status",
                inputSchema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
            ),
            Tool(
                name="aws_fallback",
                description=f"AWS query (broker error: {str(e)})",
                inputSchema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
            )
        ]

async def handle_deploy_workflow_locally(git_context, arguments):
    """Handle deploy_workflow entirely locally - async pattern"""
    import time
    import re
    
    # Auto-fill parameters from Git context
    repository = arguments.get("repository") or git_context['repository']
    branch = arguments.get("branch") or git_context['branch']
    pr_number = arguments.get("pr_number") or git_context.get('pr_number')
    
    # Get environment from arguments or detect from branch
    environment = arguments.get("environment")
    if not environment:
        # Parse environment from query if user specified it
        query = arguments.get("query", "")
        if "deploy to " in query:
            env_part = query.split("deploy to ")[-1].strip()
            if env_part and env_part in ["dev", "staging", "production"]:
                environment = env_part
        
        # If still no environment, fall back to branch mapping
        if not environment:
            config = git_context.get('deploy_config', {})
            branch_mapping = config.get('branch_mapping', {})
            environment = branch_mapping.get(branch, "dev")
    
    # Step 1: Post /deploy comment to trigger GitHub Actions
    if not pr_number:
        return [TextContent(type="text", text="❌ No PR found for current branch. Create a PR first.")]
    
    try:
        # Post deploy comment
        deploy_comment = f"/deploy {environment}"
        result = subprocess.run([
            'gh', 'pr', 'comment', str(pr_number), '--body', deploy_comment
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        if result.returncode != 0:
            return [TextContent(type="text", text=f"❌ Failed to post deploy comment: {result.stderr}")]
        
        # Step 2: Automatically call deploy_status and return combined result
        try:
            print(f"[DEBUG] Attempting automatic deploy_status call for {repository}")
            # Wait briefly for GitHub Actions to start
            import time
            time.sleep(2)
            
            # Call deploy_status
            status_result = make_broker_request("deploy_status", {"query": f"{repository} pr_number={pr_number}"}, git_context)
            print(f"[DEBUG] Got status result: {status_result[:100]}...")
            
            return [TextContent(type="text", text=f"""🚀 **Deployment Started Successfully**

**Details:**
- Repository: {repository}
- Branch: {branch}
- Environment: {environment}
- PR: #{pr_number}

✅ **Deploy comment posted:** `{deploy_comment}`

---

📊 **Current Status:**
{status_result}

💡 **Next Steps:**
- Use: `deploy_get_run <run_id>` for detailed run info when available
- Use: `deploy_status {repository}` to refresh status""")]
        
        except Exception as status_error:
            print(f"[DEBUG] Auto-status failed: {status_error}")
            # If deploy_status fails, return the original working response
            return [TextContent(type="text", text=f"""🚀 **Deployment Started Successfully**

**Details:**
- Repository: {repository}
- Branch: {branch}
- Environment: {environment}
- PR: #{pr_number}

⏳ **Deployment is running in background...**

**Track Progress:**
- Use: `deploy_status {repository}` to check latest status
- Use: `deploy_get_run <run_id>` when run_id appears in PR comments
- Check PR #{pr_number} for run_id updates from GitHub Actions

✅ **Deploy comment posted:** `{deploy_comment}`

⚠️ **Note:** Auto-status check failed: {str(status_error)}""")]
        
    except Exception as e:
        return [TextContent(type="text", text=f"❌ Deployment failed: {str(e)}")]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """Proxy tool calls to broker with auto-context and local command execution"""
    git_context = get_git_context()
    
    # Handle deploy_local locally
    if name == "deploy_local":
        return await handle_deploy_workflow_locally(git_context, arguments)
    
    # Auto-fill missing parameters from Git context for other tools
    result = make_broker_request(name, arguments, git_context)
    
    # Check if broker wants us to execute a local command
    if result.startswith("KIRO_LOCAL_COMMAND:"):
        lines = result.split('\n')
        command_line = lines[0].replace("KIRO_LOCAL_COMMAND:", "")
        continue_line = lines[1] if len(lines) > 1 else ""
        
        # Execute GitHub CLI locally
        local_result = execute_local_command(command_line)
        
        # If there's a continuation, call it
        if continue_line.startswith("KIRO_CONTINUE_WITH:"):
            continue_params = continue_line.replace("KIRO_CONTINUE_WITH:", "").split("|")
            if len(continue_params) >= 4:
                tool_name = continue_params[0]
                if tool_name == "deploy_monitor":
                    # Call deploy_monitor with extracted params
                    monitor_args = {
                        "repository": continue_params[1],
                        "branch": continue_params[2], 
                        "environment": continue_params[3],
                        "region": continue_params[4]
                    }
                    monitor_result = make_broker_request("deploy_monitor", monitor_args, git_context)
                    return [TextContent(type="text", text=f"{local_result}\n\n{monitor_result}")]
        
        return [TextContent(type="text", text=local_result)]
    
    return [TextContent(type="text", text=result)]

def execute_local_command(command_str: str) -> str:
    """Execute command locally using user's credentials"""
    import subprocess
    import shlex
    
    try:
        # Parse command safely
        command_parts = shlex.split(command_str)
        
        # Execute with user's environment
        result = subprocess.run(
            command_parts,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=os.getcwd()
        )
        
        if result.returncode == 0:
            return f"✅ GitHub comment posted successfully"
        else:
            return f"❌ GitHub CLI failed: {result.stderr.strip()}"
            
    except subprocess.TimeoutExpired:
        return "❌ GitHub CLI timed out - check your authentication"
    except Exception as e:
        return f"❌ Local command error: {str(e)}"

async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
