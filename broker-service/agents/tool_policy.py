"""
Tool policy configuration for tier-based access control
"""

# Explicit allowlist for user tier (fail-closed security)
USER_ALLOWED_TOOL_NAMES = {
    # AWS infrastructure read-only
    "ecs_call_tool",
    "iac_call_tool",
    
    # Deployment metrics (safe read-only)
    "deploy_get_run",
    "deploy_get_steps", 
    "deploy_find_latest",
    "deploy_find_active",
    "deploy_get_summary",
    
    # Basic pricing (template-based only)
    "pricingcalc_estimate_from_cfn",
    "pricingcalc_estimate_with_custom_specs"
}

# Admin-only tools (in addition to all user tools)
ADMIN_ONLY_TOOLS = [
    "pr_get_diff",
    "pr_summarize", 
    "pricingcalc_estimate_from_stack"
]

# All tools available to admin tier
ALL_ADMIN_TOOLS = list(USER_ALLOWED_TOOL_NAMES) + ADMIN_ONLY_TOOLS

def is_tool_allowed(tool_name: str, tier: str) -> bool:
    """Check if tool is allowed for tier (fail-closed)"""
    if tier == "admin":
        return True  # Admin gets all tools
    return tool_name in USER_ALLOWED_TOOL_NAMES

def get_denied_tool_response(tool_name: str, tier: str) -> dict:
    """Standard response for denied tool access"""
    return {
        "error_type": "DENIED_TOOL",
        "tool": tool_name,
        "tier": tier,
        "message": f"Tool '{tool_name}' not available on /ask endpoint. Use /admin for full access."
    }
