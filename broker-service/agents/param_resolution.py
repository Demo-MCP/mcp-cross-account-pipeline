"""
Metadata-first parameter resolution - prevents parameter invention
"""
import re
from typing import Dict, Any, Optional, List

def build_request_context(request_data: dict, tier: str) -> dict:
    """Build request context from inbound request"""
    return {
        "tier": tier,
        "prompt": request_data.get("ask_text", ""),
        "metadata": request_data.get("metadata", {}),
        "aws": {
            "account_id": request_data.get("account_id", "500330120558"),
            "region": request_data.get("region", "us-east-1"),
            "shim_url": request_data.get("shim_url", "http://internal-mcp-internal-alb-2059913293.us-east-1.elb.amazonaws.com")
        }
    }

def extract_pr_number(prompt: str) -> Optional[int]:
    """Extract PR number from prompt using strict pattern matching"""
    pattern = r'(?i)(?:pull request|pr)\s*#?\s*(\d+)'
    match = re.search(pattern, prompt)
    if match:
        try:
            pr_num = int(match.group(1))
            return pr_num if pr_num > 0 else None
        except ValueError:
            pass
    return None

def extract_stack_name(prompt: str) -> Optional[str]:
    """Extract CloudFormation stack name from prompt"""
    # Look for common stack name patterns
    patterns = [
        r'(?i)stack\s+([a-zA-Z0-9-]+)',
        r'(?i)([a-zA-Z0-9-]+)\s+stack',
        r'(?i)cloudformation\s+([a-zA-Z0-9-]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, prompt)
        if match:
            stack_name = match.group(1)
            # Validate stack name format
            if re.match(r'^[a-zA-Z][a-zA-Z0-9-]*$', stack_name):
                return stack_name
    return None

def resolve_required_params(tool_name: str, model_args: dict, ctx: dict) -> dict:
    """
    Resolve required parameters using metadata-first approach
    Returns resolved params or raises MissingParamsError
    """
    resolved = {}
    missing = []
    
    # Always prefer metadata over model args
    metadata = ctx.get("metadata", {})
    aws_ctx = ctx.get("aws", {})
    
    # Common AWS parameters (always from context)
    resolved.update({
        "account_id": aws_ctx.get("account_id"),
        "region": aws_ctx.get("region"),
        "shim_url": aws_ctx.get("shim_url")
    })
    
    # Tool-specific parameter resolution
    if tool_name.startswith("pr_"):
        # PR tools require repo, pr_number, actor, run_id
        resolved["repo"] = metadata.get("repository") or metadata.get("repo")
        resolved["pr_number"] = metadata.get("pr_number")
        resolved["actor"] = metadata.get("actor") 
        resolved["run_id"] = metadata.get("run_id")
        
        # pr_summarize also requires diff and changed_files
        if tool_name == "pr_summarize":
            resolved["diff"] = metadata.get("diff")
            resolved["changed_files"] = metadata.get("changed_files", [])
        
        # Optional parameters
        resolved["options"] = metadata.get("options", {})
        
        # Fallback: extract PR number from prompt if missing
        if not resolved["pr_number"]:
            resolved["pr_number"] = extract_pr_number(ctx.get("prompt", ""))
            
        # Check for missing required params
        required_params = ["repo", "pr_number", "actor", "run_id"]
        if tool_name == "pr_summarize":
            required_params.extend(["diff", "changed_files"])
            
        for param in required_params:
            if not resolved.get(param):
                missing.append(param)
                
    elif tool_name.startswith("deploy_"):
        # Deploy tools have different parameter requirements
        if tool_name in ["deploy_find_latest", "deploy_find_active"]:
            # These tools need repository parameter
            resolved["repository"] = metadata.get("repository") or metadata.get("repo")
            if not resolved["repository"]:
                missing.append("repository")
        
        if tool_name in ["deploy_get_run", "deploy_get_steps", "deploy_get_summary"]:
            # These tools need run_id parameter
            resolved["run_id"] = metadata.get("run_id")
            if not resolved["run_id"]:
                missing.append("run_id")
        
        # Optional parameters
        if tool_name in ["deploy_get_steps"]:
            resolved["limit"] = metadata.get("limit", 200)
        elif tool_name in ["deploy_find_latest", "deploy_find_active"]:
            resolved["limit"] = metadata.get("limit", 10)
                
    elif tool_name in ["ecs_call_tool", "iac_call_tool"]:
        # ECS and IAC tools need account_id and region (already set above)
        # ECS tools may need api_operation and api_params from model args
        if tool_name == "ecs_call_tool":
            # Map common lowercase operations to proper AWS API names
            api_op = model_args.get("api_operation", "ListClusters")
            operation_map = {
                "list_clusters": "ListClusters",
                "describe_clusters": "DescribeClusters", 
                "list_services": "ListServices",
                "describe_services": "DescribeServices",
                "list_tasks": "ListTasks",
                "describe_tasks": "DescribeTasks"
            }
            resolved["api_operation"] = operation_map.get(api_op.lower(), api_op) if isinstance(api_op, str) else "ListClusters"
            resolved["api_params"] = model_args.get("api_params", {})
        elif tool_name == "iac_call_tool":
            resolved["stack_name"] = model_args.get("stack_name") or extract_stack_name(ctx.get("prompt", ""))
            if not resolved["stack_name"]:
                missing.append("stack_name")
                
    elif tool_name.startswith("pricingcalc_"):
        # Pricing tools have different parameter requirements
        if tool_name == "pricingcalc_estimate_from_cfn":
            resolved["template_content"] = metadata.get("template_content") or metadata.get("template")
            resolved["region"] = metadata.get("region", "us-east-1")
            if not resolved["template_content"]:
                missing.append("template_content")
                
        elif tool_name == "pricingcalc_estimate_with_custom_specs":
            resolved["template_content"] = metadata.get("template_content") or metadata.get("template")
            resolved["custom_specs"] = metadata.get("custom_specs")
            resolved["region"] = metadata.get("region", "us-east-1")
            if not resolved["template_content"]:
                missing.append("template_content")
            if not resolved["custom_specs"]:
                missing.append("custom_specs")
                
        elif tool_name == "pricingcalc_estimate_from_stack":
            resolved["stack_name"] = metadata.get("stack_name")
            resolved["account_id"] = metadata.get("account_id") or aws_ctx.get("account_id")
            resolved["region"] = metadata.get("region") or aws_ctx.get("region", "us-east-1")
            if not resolved["stack_name"]:
                missing.append("stack_name")
            if not resolved["account_id"]:
                missing.append("account_id")
    
    if missing:
        raise MissingParamsError(missing, tool_name)
    
    return resolved
    return {k: v for k, v in resolved.items() if v is not None}

class MissingParamsError(Exception):
    """Raised when required parameters are missing"""
    def __init__(self, missing_params: List[str], tool_name: str):
        self.missing_params = missing_params
        self.tool_name = tool_name
        super().__init__(f"Missing required parameters for {tool_name}: {missing_params}")

def get_missing_params_response(missing_params: List[str], tool_name: str) -> dict:
    """Standard response for missing parameters"""
    return {
        "error_type": "MISSING_PARAMS",
        "tool": tool_name,
        "missing": missing_params,
        "message": f"Missing required parameters for {tool_name}: {', '.join(missing_params)}. Provide them in metadata or request."
    }
