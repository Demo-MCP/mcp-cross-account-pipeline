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

@tool(name="pr_get_diff", description="Get pull request diff and changes")
def pr_get_diff_tool(repo: str, pr_number: int) -> str:
    """Get pull request diff and changes"""
    with measure_execution("pr_get_diff", _tool_context.get("tier", "unknown"), _tool_context.get("metadata", {})):
        result = execute_tool("pr_get_diff", {"repo": repo, "pr_number": pr_number}, _tool_context)
    return format_tool_result("pr_get_diff", result)

@tool(name="pr_summarize", description="Analyze pull request for security and best practices")
def pr_summarize_tool(repo: str, pr_number: int, diff: str = None) -> str:
    """Analyze pull request for security and best practices"""
    # If no diff provided, get it first
    if not diff:
        diff_result = pr_get_diff_tool(repo, pr_number)
        if diff_result.startswith("Error:"):
            return f"Cannot analyze PR: {diff_result}"
        diff = diff_result
    
    with measure_execution("pr_summarize", _tool_context.get("tier", "unknown"), _tool_context.get("metadata", {})):
        result = execute_tool("pr_summarize", {"repo": repo, "pr_number": pr_number, "diff": diff}, _tool_context)
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
