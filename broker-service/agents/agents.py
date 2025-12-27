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
from schemas import CostAnalysis, PRAnalysis, DeploymentStatus
from observability import measure_execution

# Global context for tool execution
_tool_context = {}

# Define actual tool functions that Strands can execute

@tool(name="ecs_call_tool", description="Call ECS tools")
def ecs_call_tool(tool: str = "ecs_resource_management", params: dict = None, **kwargs) -> str:
    """Call ECS tools with proper parameter structure
    
    Args:
        tool: Should be 'ecs_resource_management'
        params: Dictionary containing api_operation, api_params, account_id, region
    """
    if params is None:
        params = {"api_operation": "ListClusters", "api_params": {}, "account_id": "500330120558", "region": "us-east-1"}
    
    # Extract the parameters for our internal execute_tool call
    final_params = {
        "api_operation": params.get("api_operation", "ListClusters"),
        "api_params": params.get("api_params", {}),
        "account_id": params.get("account_id", "500330120558"),
        "region": params.get("region", "us-east-1")
    }
    
    with measure_execution("ecs_call_tool", _tool_context.get("tier", "unknown"), _tool_context.get("metadata", {})):
        result = execute_tool("ecs_call_tool", final_params, _tool_context)
    return format_tool_result("ecs_call_tool", result)

@tool(name="iac_call_tool", description="Query infrastructure as code templates")
def iac_call_tool(tool: str = "troubleshoot_cloudformation_deployment", params: dict = None, **kwargs) -> str:
    """Query infrastructure as code templates
    
    Args:
        tool: Should be 'troubleshoot_cloudformation_deployment'
        params: Dictionary containing stack_name, account_id, region
    """
    if params is None:
        params = {"stack_name": "", "account_id": "500330120558", "region": "us-east-1"}
    
    # Extract the parameters for our internal execute_tool call
    final_params = {
        "stack_name": params.get("stack_name", ""),
        "account_id": params.get("account_id", "500330120558"),
        "region": params.get("region", "us-east-1")
    }
    
    with measure_execution("iac_call_tool", _tool_context.get("tier", "unknown"), _tool_context.get("metadata", {})):
        result = execute_tool("iac_call_tool", final_params, _tool_context)
    return format_tool_result("iac_call_tool", result)

@tool(name="deploy_get_run", description="Get deployment run details")
def deploy_get_run_tool(run_id: str) -> str:
    """Get deployment run details"""
    with measure_execution("deploy_get_run", _tool_context.get("tier", "unknown"), _tool_context.get("metadata", {})):
        result = execute_tool("deploy_get_run", {"run_id": run_id}, _tool_context)
    return format_tool_result("deploy_get_run", result)

@tool(name="deploy_get_steps", description="Get deployment steps")
def deploy_get_steps_tool(run_id: str, limit: int = 200) -> str:
    """Get deployment steps"""
    with measure_execution("deploy_get_steps", _tool_context.get("tier", "unknown"), _tool_context.get("metadata", {})):
        result = execute_tool("deploy_get_steps", {"run_id": run_id, "limit": limit}, _tool_context)
    return format_tool_result("deploy_get_steps", result)

@tool(name="deploy_find_latest", description="Find latest deployment")
def deploy_find_latest_tool(repository: str, limit: int = 10) -> str:
    """Find latest deployment"""
    with measure_execution("deploy_find_latest", _tool_context.get("tier", "unknown"), _tool_context.get("metadata", {})):
        result = execute_tool("deploy_find_latest", {"repository": repository, "limit": limit}, _tool_context)
    return format_tool_result("deploy_find_latest", result)

@tool(name="deploy_find_active", description="Find active deployments")
def deploy_find_active_tool(repository: str = "", limit: int = 10) -> str:
    """Find active deployments"""
    with measure_execution("deploy_find_active", _tool_context.get("tier", "unknown"), _tool_context.get("metadata", {})):
        result = execute_tool("deploy_find_active", {"repository": repository, "limit": limit}, _tool_context)
    return format_tool_result("deploy_find_active", result)

@tool(name="deploy_get_summary", description="Get deployment summary")
def deploy_get_summary_tool(run_id: str) -> str:
    """Get deployment summary"""
    with measure_execution("deploy_get_summary", _tool_context.get("tier", "unknown"), _tool_context.get("metadata", {})):
        result = execute_tool("deploy_get_summary", {"run_id": run_id}, _tool_context)
    return format_tool_result("deploy_get_summary", result)

@tool(name="pricingcalc_estimate_from_cfn", description="Estimate pricing from CloudFormation template")
def pricingcalc_estimate_from_cfn_tool(template_content: str, region: str = "us-east-1") -> str:
    """Estimate pricing from CloudFormation template"""
    params = {"template_content": template_content, "region": region}
    with measure_execution("pricingcalc_estimate_from_cfn", _tool_context.get("tier", "unknown"), _tool_context.get("metadata", {})):
        result = execute_tool("pricingcalc_estimate_from_cfn", params, _tool_context)
    return format_tool_result("pricingcalc_estimate_from_cfn", result)

@tool(name="pricingcalc_estimate_with_custom_specs", description="Estimate pricing with custom specifications")
def pricingcalc_estimate_with_custom_specs_tool(template_content: str, custom_specs: str, region: str = "us-east-1") -> str:
    """Estimate pricing with custom specifications"""
    params = {"template_content": template_content, "custom_specs": custom_specs, "region": region}
    with measure_execution("pricingcalc_estimate_with_custom_specs", _tool_context.get("tier", "unknown"), _tool_context.get("metadata", {})):
        result = execute_tool("pricingcalc_estimate_with_custom_specs", params, _tool_context)
    return format_tool_result("pricingcalc_estimate_with_custom_specs", result)

@tool(name="pricingcalc_estimate_from_stack", description="Estimate pricing from existing stack")
def pricingcalc_estimate_from_stack_tool(stack_name: str, account_id: str, region: str = "us-east-1") -> str:
    """Estimate pricing from existing stack"""
    params = {"stack_name": stack_name, "account_id": account_id, "region": region}
    with measure_execution("pricingcalc_estimate_from_stack", _tool_context.get("tier", "unknown"), _tool_context.get("metadata", {})):
        result = execute_tool("pricingcalc_estimate_from_stack", params, _tool_context)
    return format_tool_result("pricingcalc_estimate_from_stack", result)

@tool(name="pr_get_diff", description="Get pull request diff and changes")
def pr_get_diff_tool(repo: str, pr_number: int, actor: str, run_id: str, options: dict = None) -> str:
    """Get pull request diff and changes"""
    params = {"repo": repo, "pr_number": pr_number, "actor": actor, "run_id": run_id}
    if options:
        params["options"] = options
    with measure_execution("pr_get_diff", _tool_context.get("tier", "unknown"), _tool_context.get("metadata", {})):
        result = execute_tool("pr_get_diff", params, _tool_context)
    return format_tool_result("pr_get_diff", result)

@tool(name="pr_summarize", description="Analyze pull request for security and best practices")
def pr_summarize_tool(repo: str, pr_number: int, actor: str, run_id: str, diff: str, changed_files: list, options: dict = None) -> str:
    """Analyze pull request for security and best practices"""
    params = {"repo": repo, "pr_number": pr_number, "actor": actor, "run_id": run_id, "diff": diff, "changed_files": changed_files}
    if options:
        params["options"] = options
    with measure_execution("pr_summarize", _tool_context.get("tier", "unknown"), _tool_context.get("metadata", {})):
        result = execute_tool("pr_summarize", params, _tool_context)
    return format_tool_result("pr_summarize", result)

@tool(name="deploy_run", description="Run deployment workflow")
def deploy_run_tool(repo: str, workflow: str, branch: str = "main") -> str:
    """Run deployment workflow"""
    with measure_execution("deploy_run", _tool_context.get("tier", "unknown"), _tool_context.get("metadata", {})):
        result = execute_tool("deploy_run", {"repo": repo, "workflow": workflow, "branch": branch}, _tool_context)
    return format_tool_result("deploy_run", result)

@tool(name="deploy_status", description="Check deployment status")
def deploy_status_tool(repo: str, run_id: str) -> str:
    """Check deployment status"""
    with measure_execution("deploy_status", _tool_context.get("tier", "unknown"), _tool_context.get("metadata", {})):
        result = execute_tool("deploy_status", {"repo": repo, "run_id": run_id}, _tool_context)
    return format_tool_result("deploy_status", result)

@tool(name="pricingcalc_estimate", description="Calculate AWS pricing estimates")
def pricingcalc_estimate_tool(service: str, region: str = "us-east-1", **kwargs) -> str:
    """Calculate AWS pricing estimates"""
    params = {"service": service, "region": region, **kwargs}
    with measure_execution("pricingcalc_estimate", _tool_context.get("tier", "unknown"), _tool_context.get("metadata", {})):
        result = execute_tool("pricingcalc_estimate", params, _tool_context)
    return format_tool_result("pricingcalc_estimate", result)

@tool(name="pricingcalc_compare", description="Compare pricing across regions")
def pricingcalc_compare_tool(service: str, regions: List[str], **kwargs) -> str:
    """Compare pricing across regions"""
    params = {"service": service, "regions": regions, **kwargs}
    with measure_execution("pricingcalc_compare", _tool_context.get("tier", "unknown"), _tool_context.get("metadata", {})):
        result = execute_tool("pricingcalc_compare", params, _tool_context)
    return format_tool_result("pricingcalc_compare", result)

@tool(name="repo_list", description="List repositories")
def repo_list_tool(org: str = None) -> str:
    """List repositories"""
    params = {"org": org} if org else {}
    with measure_execution("repo_list", _tool_context.get("tier", "unknown"), _tool_context.get("metadata", {})):
        result = execute_tool("repo_list", params, _tool_context)
    return format_tool_result("repo_list", result)

@tool(name="repo_info", description="Get repository information")
def repo_info_tool(repo: str) -> str:
    """Get repository information"""
    with measure_execution("repo_info", _tool_context.get("tier", "unknown"), _tool_context.get("metadata", {})):
        result = execute_tool("repo_info", {"repo": repo}, _tool_context)
    return format_tool_result("repo_info", result)

@tool(name="workflow_list", description="List workflows for repository")
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
        if "error" in result:
            return f"Error: {result['error']}"
        elif "result" in result:
            actual_result = result["result"]
            
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
