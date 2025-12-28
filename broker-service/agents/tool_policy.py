"""
Tool policy and tier-based access control
"""

# User tier gets safe, read-only tools
USER_ALLOWED_TOOL_NAMES = {
    # Deployment tools (read-only)
    "deploy_find_latest",
    "deploy_get_summary", 
    "deploy_get_run",
    "deploy_get_steps",
    
    # ECS tools (read-only)
    "ecs_call_tool",
    
    # IAC tools (read-only)
    "iac_call_tool",
    
    # Pricing tools (safe calculations)
    "pricingcalc_estimate_from_stack"
}

# Admin tier gets ALL tools (including sensitive ones)
ADMIN_ONLY_TOOLS = {
    # PR tools (can access sensitive code/diffs)
    "pr_get_diff",
    "pr_summarize",
    "pr_get_context"
}

# All tools available to admin
ALL_ADMIN_TOOLS = USER_ALLOWED_TOOL_NAMES | ADMIN_ONLY_TOOLS


def is_tool_allowed(tool_name: str, tier: str) -> bool:
    """
    Check if tool is allowed for the given tier
    
    Args:
        tool_name: Name of the tool to check
        tier: "user" or "admin"
    
    Returns:
        True if allowed, False if denied
    """
    if tier == "admin":
        return tool_name in ALL_ADMIN_TOOLS
    elif tier == "user":
        return tool_name in USER_ALLOWED_TOOL_NAMES
    else:
        # Unknown tier - fail closed
        return False


def get_denied_tool_response(tool_name: str, tier: str, correlation_id: str) -> dict:
    """Generate standardized denied tool response"""
    return {
        "error_type": "DENIED_TOOL",
        "tool": tool_name,
        "tier": tier,
        "correlation_id": correlation_id,
        "message": f"Tool '{tool_name}' not available on /{tier} endpoint. Use /admin for full access."
    }


def get_tool_counts_by_tier() -> dict:
    """Get tool counts for debugging"""
    return {
        "user_tools": len(USER_ALLOWED_TOOL_NAMES),
        "admin_only_tools": len(ADMIN_ONLY_TOOLS), 
        "total_admin_tools": len(ALL_ADMIN_TOOLS)
    }
