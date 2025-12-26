#!/usr/bin/env python3
"""
Tool policy configuration for broker service
"""

# Default deny approach - only explicitly allowed tools are available to users
DEFAULT_DENY = True

# Tools available to regular users via /ask endpoint
USER_ALLOWED_TOOLS = {
    # AWS infra read-only basics
    "ecs_call_tool",
    "iac_call_tool",
    
    # Deployment metrics read-only
    "deploy_get_run",
    "deploy_get_steps", 
    "deploy_find_latest",
    "deploy_find_active",
    "deploy_get_summary",
    
    # Pricing (safe ones)
    "pricingcalc_estimate_from_cfn",
    "pricingcalc_estimate_with_custom_specs"
}

# Admin gets all tools (including PR tools that are NOT in USER_ALLOWED_TOOLS)
ADMIN_ALLOWED_TOOLS = "ALL"

def is_tool_allowed(tool_name: str, tier: str) -> bool:
    """Check if a tool is allowed for the given tier"""
    if tier == "admin":
        return True  # Admin gets everything
    return tool_name in USER_ALLOWED_TOOLS  # Users only get approved subset
