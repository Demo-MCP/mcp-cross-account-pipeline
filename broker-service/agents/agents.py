"""
Strands-based agents for tiered access control
"""
import json
from strands import Agent, tool
from strands.models import BedrockModel
from typing import Dict, Any, List
from .tool_policy import USER_ALLOWED_TOOL_NAMES, ALL_ADMIN_TOOLS, is_tool_allowed
from .tool_wrappers import execute_tool
from .prompts import USER_AGENT_PROMPT, ADMIN_AGENT_PROMPT, TOOL_DESCRIPTIONS
from .param_resolution import resolve_with_aliases
from schemas import CostAnalysis, PRAnalysis, DeploymentStatus
from observability import measure_execution

# Global context for tool execution
_tool_context = {}

# Define actual tool functions that Strands can execute

@tool(name="ecs_call_tool", description="Call ECS APIs with api_operation and api_params")
def ecs_call_tool(api_operation: str = "ListClusters", api_params: dict = None) -> str:
    """Call ECS tools with proper parameter structure
    
    Args:
        api_operation: The ECS API operation to execute (CamelCase)
        api_params: Dictionary of parameters to pass to the API operation
    """
    # Get context parameters from metadata (fallback values)
    metadata = _tool_context.get("metadata", {})
    aws_ctx = _tool_context.get("aws", {})
    
    # Extract infrastructure parameters from context
    account_id = aws_ctx.get("account_id", "500330120558")
    region = aws_ctx.get("region", "us-east-1")
    
    if api_params is None:
        api_params = {}
    
    print(f"[DEBUG] ecs_call_tool - api_operation: {api_operation}, account_id: {account_id}, region: {region}")
    
    # Prepare final parameters for MCP call
    final_params = {
        "api_operation": api_operation,
        "api_params": api_params,
        "account_id": account_id,
        "region": region
    }
    
    with measure_execution("ecs_call_tool", _tool_context.get("tier", "unknown"), metadata):
        result = execute_tool("ecs_call_tool", final_params, _tool_context)
    return format_tool_result("ecs_call_tool", result)

@tool(name="iac_call_tool", description="Query CloudFormation templates by stack_name")
def iac_call_tool(stack_name: str = "") -> str:
    """Query infrastructure as code templates
    
    Args:
        stack_name: CloudFormation stack name to query
    """
    # Get context parameters from metadata (fallback values)
    metadata = _tool_context.get("metadata", {})
    aws_ctx = _tool_context.get("aws", {})
    
    # Extract infrastructure parameters from context
    account_id = aws_ctx.get("account_id", "500330120558")
    region = aws_ctx.get("region", "us-east-1")
    
    print(f"[DEBUG] iac_call_tool - stack_name: {stack_name}, account_id: {account_id}, region: {region}")
    
    # Prepare final parameters for MCP call
    final_params = {
        "stack_name": stack_name,
        "account_id": account_id,
        "region": region
    }
    
    with measure_execution("iac_call_tool", _tool_context.get("tier", "unknown"), metadata):
        result = execute_tool("iac_call_tool", final_params, _tool_context)
    return format_tool_result("iac_call_tool", result)

@tool(name="deploy_get_run", description="Get deployment run details by run_id")
def deploy_get_run_tool(run_id: str) -> str:
    """Get deployment run details"""
    with measure_execution("deploy_get_run", _tool_context.get("tier", "unknown"), _tool_context.get("metadata", {})):
        result = execute_tool("deploy_get_run", {"run_id": run_id}, _tool_context)
    return format_tool_result("deploy_get_run", result)

@tool(name="deploy_get_steps", description="Get deployment steps by run_id")
def deploy_get_steps_tool(run_id: str) -> str:
    """Get deployment steps"""
    # Get limit from metadata context, default to 200
    metadata = _tool_context.get("metadata", {})
    limit = metadata.get("limit", 200)
    
    with measure_execution("deploy_get_steps", _tool_context.get("tier", "unknown"), metadata):
        result = execute_tool("deploy_get_steps", {"run_id": run_id, "limit": limit}, _tool_context)
    return format_tool_result("deploy_get_steps", result)

@tool(name="deploy_find_latest", description="Find latest deployment runs")
def deploy_find_latest_tool() -> str:
    """Find latest deployment"""
    # Get repository and limit from metadata context
    metadata = _tool_context.get("metadata", {})
    repository = metadata.get("repository") or metadata.get("repo", "")
    limit = metadata.get("limit", 10)
    
    print(f"[DEBUG] deploy_find_latest - repository: {repository}, limit: {limit}")
    
    if not repository:
        return format_tool_result("deploy_find_latest", {"error": "Repository is required"})
    
    params = {"repository": repository, "limit": limit}
    with measure_execution("deploy_find_latest", _tool_context.get("tier", "unknown"), metadata):
        result = execute_tool("deploy_find_latest", params, _tool_context)
    return format_tool_result("deploy_find_latest", result)

@tool(name="deploy_find_active", description="Find active/running deployment runs")
def deploy_find_active_tool() -> str:
    """Find active deployments"""
    # Get repository and limit from metadata context
    metadata = _tool_context.get("metadata", {})
    repository = metadata.get("repository", "") or metadata.get("repo", "")
    limit = metadata.get("limit", 10)
    
    print(f"[DEBUG] deploy_find_active - repository: {repository}, limit: {limit}")
    
    params = {"repository": repository, "limit": limit}
    with measure_execution("deploy_find_active", _tool_context.get("tier", "unknown"), metadata):
        result = execute_tool("deploy_find_active", params, _tool_context)
    return format_tool_result("deploy_find_active", result)

@tool(name="deploy_get_summary", description="Get deployment summary by run_id")
def deploy_get_summary_tool(run_id: str) -> str:
    """Get deployment summary"""
    with measure_execution("deploy_get_summary", _tool_context.get("tier", "unknown"), _tool_context.get("metadata", {})):
        result = execute_tool("deploy_get_summary", {"run_id": run_id}, _tool_context)
    return format_tool_result("deploy_get_summary", result)

@tool(name="pricingcalc_estimate_from_cfn", description="Calculate pricing from CloudFormation template")
def pricingcalc_estimate_from_cfn_tool(template_content: str) -> str:
    """Estimate pricing from CloudFormation template"""
    # Get region from metadata context, default to us-east-1
    metadata = _tool_context.get("metadata", {})
    region = metadata.get("region", "us-east-1")
    
    params = {"template_content": template_content, "region": region}
    with measure_execution("pricingcalc_estimate_from_cfn", _tool_context.get("tier", "unknown"), metadata):
        result = execute_tool("pricingcalc_estimate_from_cfn", params, _tool_context)
    return format_tool_result("pricingcalc_estimate_from_cfn", result)

@tool(name="pricingcalc_estimate_with_custom_specs", description="Calculate pricing with custom specifications")
def pricingcalc_estimate_with_custom_specs_tool(custom_specs: str) -> str:
    """Estimate pricing with custom specifications"""
    # Get region from metadata context, default to us-east-1
    metadata = _tool_context.get("metadata", {})
    region = metadata.get("region", "us-east-1")
    
    params = {"custom_specs": custom_specs, "region": region}
    with measure_execution("pricingcalc_estimate_with_custom_specs", _tool_context.get("tier", "unknown"), metadata):
        result = execute_tool("pricingcalc_estimate_with_custom_specs", params, _tool_context)
    return format_tool_result("pricingcalc_estimate_with_custom_specs", result)

@tool(name="pricingcalc_estimate_from_stack", description="Estimate costs for an existing CloudFormation stack.")
def pricingcalc_estimate_from_stack_tool(stack_name: str) -> str:
    """
    Estimate costs for a stack. 
    NOTE: account_id and region are handled automatically via context.
    """
    # Debug: Print everything we can see
    print(f"[DEBUG] === PRICING TOOL CALLED ===")
    print(f"[DEBUG] Input stack_name: '{stack_name}'")
    print(f"[DEBUG] Full _tool_context: {_tool_context}")
    
    # Pull the data Nova is blind to from the verified request context
    aws_ctx = _tool_context.get("aws", {})
    metadata = _tool_context.get("metadata", {})
    
    print(f"[DEBUG] AWS context: {aws_ctx}")
    print(f"[DEBUG] Metadata: {metadata}")
    
    # Merge user input with request-level data
    final_params = {
        "stack_name": stack_name,
        "account_id": aws_ctx.get("account_id"),  # From top-level request
        "region": aws_ctx.get("region")           # From top-level request
    }
    
    print(f"[DEBUG] Final params for MCP: {final_params}")
    
    # Validate we have all required parameters
    if not final_params["stack_name"]:
        error_msg = json.dumps({"error": "MISSING_STACK_NAME", "message": "Stack name is required"})
        print(f"[DEBUG] Error: {error_msg}")
        return error_msg
        
    if not final_params["account_id"] or not final_params["region"]:
        error_msg = json.dumps({"error": "MISSING_AWS_CONTEXT", "message": f"Missing AWS context: account_id={final_params['account_id']}, region={final_params['region']}"})
        print(f"[DEBUG] Error: {error_msg}")
        return error_msg
    
    # Execute with full payload
    with measure_execution("pricingcalc_estimate_from_stack", _tool_context.get("tier", "unknown"), metadata):
        result = execute_tool("pricingcalc_estimate_from_stack", final_params, _tool_context)
    
    print(f"[DEBUG] MCP result: {result}")
    return format_tool_result("pricingcalc_estimate_from_stack", result)

@tool(name="pr_get_diff", description="Get pull request diff by repo, pr_number, actor, run_id, and optional options")
def pr_get_diff_tool(repo: str, pr_number: int, actor: str, run_id: str, options: dict = None) -> str:
    """Get pull request diff and changes"""
    params = {"repo": repo, "pr_number": pr_number, "actor": actor, "run_id": run_id}
    if options:
        params["options"] = options
    with measure_execution("pr_get_diff", _tool_context.get("tier", "unknown"), _tool_context.get("metadata", {})):
        result = execute_tool("pr_get_diff", params, _tool_context)
    return format_tool_result("pr_get_diff", result)

@tool(name="pr_summarize", description="Analyze PR security by repo, pr_number, actor, run_id, diff, changed_files, and optional options")
@tool(name="deploy_run", description="Run deployment workflow by repo, workflow, and optional branch")
def deploy_run_tool(repo: str, workflow: str, branch: str = "main") -> str:
    """Run deployment workflow"""
    with measure_execution("deploy_run", _tool_context.get("tier", "unknown"), _tool_context.get("metadata", {})):
        result = execute_tool("deploy_run", {"repo": repo, "workflow": workflow, "branch": branch}, _tool_context)
    return format_tool_result("deploy_run", result)

@tool(name="deploy_status", description="Check deployment status by repo and run_id")
def deploy_status_tool(repo: str, run_id: str) -> str:
    """Check deployment status"""
    with measure_execution("deploy_status", _tool_context.get("tier", "unknown"), _tool_context.get("metadata", {})):
        result = execute_tool("deploy_status", {"repo": repo, "run_id": run_id}, _tool_context)
    return format_tool_result("deploy_status", result)

@tool(name="pricingcalc_estimate", description="Calculate AWS pricing by service, region, and additional parameters")
def pricingcalc_estimate_tool(service: str, region: str = "us-east-1", **kwargs) -> str:
    """Calculate AWS pricing estimates"""
    params = {"service": service, "region": region, **kwargs}
    with measure_execution("pricingcalc_estimate", _tool_context.get("tier", "unknown"), _tool_context.get("metadata", {})):
        result = execute_tool("pricingcalc_estimate", params, _tool_context)
    return format_tool_result("pricingcalc_estimate", result)

@tool(name="pricingcalc_compare", description="Compare pricing across regions by service and regions list")
def pricingcalc_compare_tool(service: str, regions: List[str], **kwargs) -> str:
    """Compare pricing across regions"""
    params = {"service": service, "regions": regions, **kwargs}
    with measure_execution("pricingcalc_compare", _tool_context.get("tier", "unknown"), _tool_context.get("metadata", {})):
        result = execute_tool("pricingcalc_compare", params, _tool_context)
    return format_tool_result("pricingcalc_compare", result)

@tool(name="repo_list", description="List repositories by optional organization name")
def repo_list_tool(org: str = None) -> str:
    """List repositories"""
    params = {"org": org} if org else {}
    with measure_execution("repo_list", _tool_context.get("tier", "unknown"), _tool_context.get("metadata", {})):
        result = execute_tool("repo_list", params, _tool_context)
    return format_tool_result("repo_list", result)

@tool(name="repo_info", description="Get repository information by repo name")
def repo_info_tool(repo: str) -> str:
    """Get repository information"""
    with measure_execution("repo_info", _tool_context.get("tier", "unknown"), _tool_context.get("metadata", {})):
        result = execute_tool("repo_info", {"repo": repo}, _tool_context)
    return format_tool_result("repo_info", result)

@tool(name="pr_analyze", description="Comprehensive PR analysis with security scanning, best practices review, and Checkov integration. Use this for all PR analysis requests.")
def pr_analyze_tool(repo_hint: str = "") -> str:
    """
    Combined tool: Programmatically handles large data transfers.
    Keeps large diffs out of LLM context during the planning phase.
    """
    metadata = _tool_context.get("metadata", {})
    repo = metadata.get("repository") or repo_hint
    pr_num = metadata.get("pr_number")
    actor = metadata.get("actor", "")
    run_id = metadata.get("run_id", "")

    print(f"[DEBUG] pr_analyze - Internal handoff for repo: {repo}, pr: {pr_num}")

    # Step 1: Programmatic retrieval - keeps large diff out of Nova's context
    diff_response = execute_tool("pr_get_diff", {
        "repo": repo,
        "pr_number": pr_num,
        "actor": actor,
        "run_id": run_id
    }, _tool_context)
    
    if isinstance(diff_response, dict) and "error" in diff_response:
        return json.dumps(diff_response)
    
    # Parse diff result
    try:
        if isinstance(diff_response, dict) and "result" in diff_response:
            diff_data = json.loads(diff_response["result"]) if isinstance(diff_response["result"], str) else diff_response["result"]
        else:
            diff_data = json.loads(diff_response) if isinstance(diff_response, str) else diff_response
        
        diff_text = diff_data.get("diff", "")
        changed_files = diff_data.get("changed_files", [])
        
        if not diff_text and not changed_files:
            return json.dumps({"result": "No changes found in pull request"})
        
        # Step 2: Smart summary for Nova - lightweight context only
        file_summary = ", ".join([f"{f['path']} (+{f.get('additions', 0)}/-{f.get('deletions', 0)})" for f in changed_files])
        print(f"[DEBUG] Internal Handoff: Analyzing {len(changed_files)} files: {file_summary}")

        # Step 3: Direct programmatic analysis - bypass Nova's thinking phase
        analysis_result = execute_tool("pr_summarize", {
            "repo": repo,
            "pr_number": pr_num,
            "actor": actor,
            "run_id": run_id,
            "diff": diff_text,  # Passed directly to backend tool
            "changed_files": changed_files
        }, _tool_context)
        
        # Step 4: Return only final analysis to Nova - no raw diff content
        if isinstance(analysis_result, dict) and "result" in analysis_result:
            return json.dumps(analysis_result["result"])
        return json.dumps(analysis_result)
        
    except Exception as e:
        return json.dumps({"error": f"Failed to process PR data: {str(e)}"})

@tool(name="pr_get_diff", description="Get pull request diff and changed files")
def pr_get_diff_tool() -> str:
    """Get PR diff and changed files from GitHub"""
    # Get context parameters from metadata (fallback values)
    metadata = _tool_context.get("metadata", {})
    
    # User input takes precedence, context provides fallback
    final_repo = metadata.get("repository") or metadata.get("repo", "")
    final_pr_number = metadata.get("pr_number")
    final_actor = metadata.get("actor", "")
    final_run_id = metadata.get("run_id", "")
    
    print(f"[DEBUG] pr_get_diff - repo: {final_repo}, pr_number: {final_pr_number}, actor: {final_actor}, run_id: {final_run_id}")
    
    if not all([final_repo, final_pr_number, final_actor, final_run_id]):
        return format_tool_result("pr_get_diff", {"error": f"Missing required parameters: repo={final_repo}, pr_number={final_pr_number}, actor={final_actor}, run_id={final_run_id}"})
    
    # Prepare final parameters
    final_params = {
        "repo": final_repo,
        "pr_number": final_pr_number,
        "actor": final_actor,
        "run_id": final_run_id
    }

    with measure_execution("pr_get_diff", _tool_context.get("tier", "unknown"), metadata):
        result = execute_tool("pr_get_diff", final_params, _tool_context)
    
    # Return clean result without JSON-RPC wrapper that confuses Nova
    if isinstance(result, dict) and "result" in result:
        return json.dumps(result["result"])
    return json.dumps(result)

@tool(name="pr_summarize", description="Internal tool used by pr_analyze for security scanning - do not call directly")
def pr_summarize_tool(diff: str, changed_files: list) -> str:
    """Analyze pull request for security and best practices"""
    # Get context parameters from metadata (fallback values)
    metadata = _tool_context.get("metadata", {})
    
    # User input takes precedence, context provides fallback
    final_repo = metadata.get("repository") or metadata.get("repo", "")
    final_pr_number = metadata.get("pr_number")
    final_actor = metadata.get("actor", "")
    final_run_id = metadata.get("run_id", "")
    
    print(f"[DEBUG] pr_summarize - repo: {final_repo}, pr_number: {final_pr_number}, actor: {final_actor}, run_id: {final_run_id}")
    
    if not all([final_repo, final_pr_number, final_actor, final_run_id]):
        return format_tool_result("pr_summarize", {"error": f"Missing required parameters: repo={final_repo}, pr_number={final_pr_number}, actor={final_actor}, run_id={final_run_id}"})
    
    # Prepare final parameters
    final_params = {
        "repo": final_repo,
        "pr_number": final_pr_number,
        "actor": final_actor,
        "run_id": final_run_id,
        "diff": diff,
        "changed_files": changed_files
    }

    with measure_execution("pr_summarize", _tool_context.get("tier", "unknown"), metadata):
        result = execute_tool("pr_summarize", final_params, _tool_context)
    
    # Return clean result without JSON-RPC wrapper that confuses Nova
    if isinstance(result, dict) and "result" in result:
        return json.dumps(result["result"])
    return json.dumps(result)

@tool(name="workflow_list", description="List workflows by repository name")
def workflow_list_tool(repo: str) -> str:
    """List workflows for repository"""
    with measure_execution("workflow_list", _tool_context.get("tier", "unknown"), _tool_context.get("metadata", {})):
        result = execute_tool("workflow_list", {"repo": repo}, _tool_context)
    return format_tool_result("workflow_list", result)

# Map tool names to functions
ALL_TOOL_FUNCTIONS = {
    "ecs_call_tool": ecs_call_tool,
    "iac_call_tool": iac_call_tool,
    "deploy_get_run": deploy_get_run_tool,
    "deploy_get_steps": deploy_get_steps_tool,
    "deploy_find_latest": deploy_find_latest_tool,
    "deploy_find_active": deploy_find_active_tool,
    "deploy_get_summary": deploy_get_summary_tool,
    "pricingcalc_estimate_from_cfn": pricingcalc_estimate_from_cfn_tool,
    "pricingcalc_estimate_with_custom_specs": pricingcalc_estimate_with_custom_specs_tool,
    "pricingcalc_estimate_from_stack": pricingcalc_estimate_from_stack_tool,
    "pr_get_diff": pr_get_diff_tool,
    "pr_analyze": pr_analyze_tool,
    "pr_summarize": pr_summarize_tool,
    "deploy_run": deploy_run_tool,
    "deploy_status": deploy_status_tool,
    "pricingcalc_estimate": pricingcalc_estimate_tool,
    "pricingcalc_compare": pricingcalc_compare_tool,
    "repo_list": repo_list_tool,
    "repo_info": repo_info_tool,
    "workflow_list": workflow_list_tool,
}

def build_user_agent(ctx: dict) -> Agent:
    """Build user agent with restricted tool set"""
    global _tool_context
    _tool_context = ctx
    
    model = BedrockModel(
        model_id="us.amazon.nova-pro-v1:0",
        temperature=0.3
    )
    
    allowed_tools = [ALL_TOOL_FUNCTIONS[name] for name in USER_ALLOWED_TOOL_NAMES if name in ALL_TOOL_FUNCTIONS]
    
    return Agent(
        model=model,
        tools=allowed_tools,
        system_prompt=USER_AGENT_PROMPT
    )

def build_admin_agent(ctx: dict) -> Agent:
    """Build admin agent with full tool set"""
    global _tool_context
    _tool_context = ctx
    
    model = BedrockModel(
        model_id="us.amazon.nova-pro-v1:0", 
        temperature=0.3
    )
    
    admin_tools = [ALL_TOOL_FUNCTIONS[name] for name in ALL_ADMIN_TOOLS if name in ALL_TOOL_FUNCTIONS]
    
    return Agent(
        model=model,
        tools=admin_tools,
        system_prompt=ADMIN_AGENT_PROMPT
    )

def format_tool_result(tool_name: str, result: Any) -> str:
    """Format tool results for LLM consumption"""
    if isinstance(result, dict):
        if "error" in result and result["error"] is not None:
            return f"Error: {result['error']}"
        elif "result" in result:
            actual_result = result["result"]
            
            # Handle MCP response format with content array
            if isinstance(actual_result, dict) and "content" in actual_result:
                content = actual_result["content"]
                if isinstance(content, list) and len(content) > 0:
                    first_content = content[0]
                    if isinstance(first_content, dict) and "text" in first_content:
                        return first_content["text"]
            
            # Handle different tool result formats
            if isinstance(actual_result, dict):
                if tool_name.startswith("pr_"):
                    if "diff" in actual_result:
                        return f"PR Diff Retrieved:\n{actual_result.get('summary', '')}\n\nFiles changed: {len(actual_result.get('files', []))}"
                    elif "analysis" in actual_result:
                        return f"PR Analysis:\n{actual_result.get('analysis', '')}"
                    else:
                        # Return the full result for PR tools
                        return json.dumps(actual_result, indent=2)
                elif tool_name.startswith("deploy_"):
                    if "status" in actual_result:
                        return f"Deployment Status: {actual_result.get('status')}\nRun ID: {actual_result.get('run_id', 'N/A')}"
                    else:
                        return json.dumps(actual_result, indent=2)
                elif tool_name.startswith("pricingcalc_"):
                    if "total_cost" in actual_result:
                        return f"Cost Estimate:\nLow: ${actual_result.get('low_cost', 0)}\nMedium: ${actual_result.get('medium_cost', 0)}\nHigh: ${actual_result.get('high_cost', 0)}"
                    else:
                        return json.dumps(actual_result, indent=2)
                else:
                    # Default: return JSON for structured data
                    return json.dumps(actual_result, indent=2)
            
            # Handle string results
            elif isinstance(actual_result, str):
                return actual_result
            else:
                return str(actual_result)[:1000]  # Truncate long results
        else:
            # No explicit result key, return the whole dict as JSON
            return json.dumps(result, indent=2)
    else:
        # Non-dict result
        if isinstance(result, str):
            return result
        else:
            return str(result)[:1000]
