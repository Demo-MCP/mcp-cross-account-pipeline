"""
Metadata-first parameter resolution - prevents parameter invention
Enhanced with user-intent-first approach for explicit requests
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
    Resolve required parameters using metadata-first + user-intent-first approach
    Returns resolved params or raises MissingParamsError
    """
    resolved = {}
    missing = []
    
    # Always prefer metadata over model args for identity/infrastructure
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
        
        # PR Number - USER INTENT WINS (what they explicitly asked for)
        if "pr_number" in model_args:
            resolved["pr_number"] = model_args["pr_number"]  # ✅ User said "PR #7"
        elif "pr_number" in metadata:
            resolved["pr_number"] = metadata["pr_number"]    # Fallback to context PR
        else:
            # Try extracting from prompt
            resolved["pr_number"] = extract_pr_number(ctx.get("prompt", ""))
        
        resolved["actor"] = metadata.get("actor") 
        resolved["run_id"] = metadata.get("run_id")
        
        # pr_summarize also requires diff and changed_files
        if tool_name == "pr_summarize":
            resolved["diff"] = metadata.get("diff")
            resolved["changed_files"] = metadata.get("changed_files", [])
        
        # Optional parameters
        resolved["options"] = metadata.get("options", {})
            
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
            # Repository - user intent wins for cross-repo queries
            if "repository" in model_args:
                resolved["repository"] = model_args["repository"]  # ✅ User specified repo
            elif "repository" in metadata:
                resolved["repository"] = metadata["repository"]    # Fallback to context
            elif "repo" in metadata:
                resolved["repository"] = metadata["repo"]
            
            if not resolved.get("repository"):
                missing.append("repository")
        
        if tool_name in ["deploy_get_run", "deploy_get_steps", "deploy_get_summary"]:
            # Run ID - user intent wins for specific run queries
            if "run_id" in model_args:
                resolved["run_id"] = model_args["run_id"]  # ✅ User asked for specific run
            elif "run_id" in metadata:
                resolved["run_id"] = metadata["run_id"]    # Fallback to context
            
            if not resolved.get("run_id"):
                missing.append("run_id")
        
        # Optional parameters
        if tool_name in ["deploy_get_steps"]:
            resolved["limit"] = metadata.get("limit", 200)
        elif tool_name in ["deploy_find_latest", "deploy_find_active"]:
            resolved["limit"] = metadata.get("limit", 10)
                
    elif tool_name in ["ecs_call_tool", "iac_call_tool"]:
        # ECS and IAC tools need account_id and region (already set above)
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
            # Stack name - user intent wins
            if "stack_name" in model_args:
                resolved["stack_name"] = model_args["stack_name"]
            else:
                resolved["stack_name"] = extract_stack_name(ctx.get("prompt", ""))
            if not resolved["stack_name"]:
                missing.append("stack_name")
                
    elif tool_name.startswith("pricingcalc_"):
        # Pricing tools have different parameter requirements
        if tool_name == "pricingcalc_estimate_from_cfn":
            # Template content - user input first
            resolved["template_content"] = model_args.get("template_content") or model_args.get("template") or metadata.get("template_content") or metadata.get("template")
            resolved["region"] = metadata.get("region", "us-east-1")
            if not resolved["template_content"]:
                missing.append("template_content")
                
        elif tool_name == "pricingcalc_estimate_with_custom_specs":
            resolved["template_content"] = model_args.get("template_content") or model_args.get("template") or metadata.get("template_content") or metadata.get("template")
            resolved["custom_specs"] = model_args.get("custom_specs") or metadata.get("custom_specs")
            resolved["region"] = metadata.get("region", "us-east-1")
            if not resolved["template_content"]:
                missing.append("template_content")
            if not resolved["custom_specs"]:
                missing.append("custom_specs")
                
        elif tool_name == "pricingcalc_estimate_from_stack":
            # Stack name - user intent wins
            if "stack_name" in model_args:
                resolved["stack_name"] = model_args["stack_name"]
            else:
                resolved["stack_name"] = metadata.get("stack_name")
            resolved["account_id"] = metadata.get("account_id") or aws_ctx.get("account_id")
            resolved["region"] = metadata.get("region") or aws_ctx.get("region", "us-east-1")
            if not resolved["stack_name"]:
                missing.append("stack_name")
            if not resolved["account_id"]:
                missing.append("account_id")
    
    if missing:
        raise MissingParamsError(missing, tool_name)
    
    return {k: v for k, v in resolved.items() if v is not None}

class MissingParamsError(Exception):
    """Raised when required parameters are missing"""
    def __init__(self, missing_params: List[str], tool_name: str):
        self.missing_params = missing_params
        self.tool_name = tool_name
        super().__init__(f"Missing required parameters for {tool_name}: {missing_params}")

def get_missing_params_response(missing_params: List[str], tool_name: str, correlation_id: str = None) -> dict:
    """Standard response for missing parameters"""
    response = {
        "error_type": "MISSING_PARAMS",
        "tool": tool_name,
        "missing": missing_params,
        "message": f"Missing required parameters for {tool_name}: {', '.join(missing_params)}. Provide them in metadata or request."
    }
    if correlation_id:
        response["correlation_id"] = correlation_id
    return response
