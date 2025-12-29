"""
Intent guards to prevent tool substitution
"""
import re
from typing import Optional, Dict, Any
from .param_resolution import extract_parameters_with_bedrock
from .tool_policy import USER_ALLOWED_TOOL_NAMES

def detect_intent(prompt: str) -> str:
    """Detect high-level intent from prompt"""
    prompt_lower = prompt.lower()
    
    # PR intent patterns
    pr_patterns = [
        r'(?i)\b(?:pull request|pr)\b',
        r'(?i)\banalyze.*pr\b',
        r'(?i)\bsummarize.*pr\b',
        r'(?i)\breview.*pr\b',
        r'(?i)\bdiff.*pr\b'
    ]
    
    # Pricing intent patterns  
    pricing_patterns = [
        r'(?i)\b(?:cost|price|pricing|estimate)\b',
        r'(?i)\bmonthly.*cost\b',
        r'(?i)\bhow much\b',
        r'(?i)\bbudget\b'
    ]
    
    # Deployment intent patterns
    deploy_patterns = [
        r'(?i)\b(?:deployment|deploy)\b',
        r'(?i)\bworkflow.*status\b',
        r'(?i)\brun.*status\b',
        r'(?i)\blatest.*deployment\b'
    ]
    
    for pattern in pr_patterns:
        if re.search(pattern, prompt):
            return "pr"
            
    for pattern in pricing_patterns:
        if re.search(pattern, prompt):
            return "pricing"
            
    for pattern in deploy_patterns:
        if re.search(pattern, prompt):
            return "deployment"
    
    return "general"

def check_intent_guards(ctx: dict) -> Optional[dict]:
    """
    Check intent guards before agent execution
    Returns error response if guard triggered, None if allowed
    """
    prompt = ctx.get("prompt", "")
    tier = ctx.get("tier", "user")
    metadata = ctx.get("metadata", {})
    
    intent = detect_intent(prompt)
    
    # PR intent guards
    if intent == "pr":
        # Check if PR number is available
        user_params = extract_parameters_with_bedrock(prompt, "pr_get_diff")
        pr_number = metadata.get("pr_number") or user_params.get("pr_number")
        if not pr_number:
            return {
                "error_type": "MISSING_PARAMS",
                "missing": ["pr_number"],
                "message": "PR analysis requires a pull request number. Provide it in metadata or specify like 'Analyze PR #9'."
            }
        
        # Check if user tier has PR tools available
        if tier == "user":
            pr_tools_available = any(tool.startswith("pr_") for tool in USER_ALLOWED_TOOL_NAMES)
            if not pr_tools_available:
                return {
                    "error_type": "DENIED_CAPABILITY", 
                    "capability": "pr_analysis",
                    "tier": tier,
                    "message": "PR analysis tools not available on /ask endpoint. Use /admin for PR analysis capabilities."
                }
    
    # Pricing intent guards
    elif intent == "pricing":
        # For stack pricing, ensure we have stack identifier
        if "stack" in prompt.lower():
            stack_name = metadata.get("stack_name")
            if not stack_name:
                # Try to extract from prompt using Nova
                pricing_params = {"stack_name": "string - CloudFormation stack name"}
                user_params = extract_parameters_with_bedrock(prompt, pricing_params, metadata)
                stack_name = user_params.get("stack_name")
                if not stack_name:
                    return {
                        "error_type": "MISSING_PARAMS",
                        "missing": ["stack_name"],
                        "message": "Stack pricing requires a stack name. Provide it in metadata or specify like 'Get pricing for my-stack'."
                    }
    
    # Deployment intent guards  
    elif intent == "deployment":
        # Ensure repository is available for deployment queries
        repository = metadata.get("repository") or metadata.get("repo")
        if not repository:
            return {
                "error_type": "MISSING_PARAMS", 
                "missing": ["repository"],
                "message": "Deployment queries require a repository. Provide it in metadata."
            }
    
    return None  # No guard triggered, proceed
