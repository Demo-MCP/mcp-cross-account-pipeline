"""
Tool wrappers with execution firewall and metadata-first parameter resolution
"""
import requests
import json
from typing import Dict, Any, Optional
from .tool_policy import is_tool_allowed, get_denied_tool_response
from .param_resolution import resolve_required_params, MissingParamsError, get_missing_params_response

def execute_tool(tool_name: str, model_args: dict, ctx: dict) -> dict:
    """
    Universal tool execution wrapper with firewall and parameter resolution
    """
    tier = ctx.get("tier", "user")
    
    # Step 1: Tool firewall (fail-closed security)
    if not is_tool_allowed(tool_name, tier):
        return get_denied_tool_response(tool_name, tier)
    
    # Step 2: Resolve required parameters (metadata-first)
    try:
        resolved_params = resolve_required_params(tool_name, model_args, ctx)
    except MissingParamsError as e:
        return get_missing_params_response(e.missing_params, e.tool_name)
    
    # Step 3: Merge with model args (metadata wins on conflicts)
    final_args = merge_params(resolved_params, model_args, ctx)
    
    # Step 4: Route to appropriate backend
    try:
        if tool_name.startswith("pr_"):
            return call_mcp_tool("pr", tool_name, final_args, ctx)
        elif tool_name.startswith("deploy_"):
            return call_mcp_tool("metrics", tool_name, final_args, ctx)
        elif tool_name.startswith("pricingcalc_"):
            return call_mcp_tool("pricingcalc", tool_name, final_args, ctx)
        elif tool_name in ["ecs_call_tool", "iac_call_tool"]:
            return call_legacy_gateway(tool_name, final_args, ctx)
        else:
            return {"error": f"Unknown tool routing for {tool_name}"}
    except Exception as e:
        return {"error": f"Tool execution failed: {str(e)}"}

def merge_params(resolved: dict, model_args: dict, ctx: dict) -> dict:
    """Merge parameters with metadata taking precedence"""
    final = model_args.copy()
    
    # Metadata-resolved params always win
    final.update(resolved)
    
    # Ensure AWS context is always from resolved
    aws_ctx = ctx.get("aws", {})
    final.update({
        "account_id": aws_ctx.get("account_id"),
        "region": aws_ctx.get("region")
    })
    
    return final

def call_mcp_tool(service: str, tool_name: str, args: dict, ctx: dict) -> dict:
    """Call MCP service tool"""
    aws_ctx = ctx.get("aws", {})
    base_url = aws_ctx.get("shim_url", "http://internal-mcp-internal-alb-2059913293.us-east-1.elb.amazonaws.com")
    
    # Route to correct MCP service
    service_urls = {
        "pr": f"{base_url}/pr",
        "metrics": f"{base_url}/metrics", 
        "pricingcalc": f"{base_url}/pricingcalc"
    }
    
    url = service_urls.get(service)
    if not url:
        return {"error": f"Unknown MCP service: {service}"}
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": args
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()
        
        if result is None:
            return {"error": f"MCP tool {tool_name} returned null response"}
        
        if "error" in result:
            error_msg = result["error"]
            if isinstance(error_msg, dict):
                return {"error": error_msg.get("message", "MCP tool error")}
            else:
                return {"error": str(error_msg)}
        
        return {"result": result.get("result", {})}
        
    except requests.exceptions.Timeout:
        return {"error": f"MCP tool {tool_name} timed out"}
    except Exception as e:
        return {"error": f"MCP call failed: {str(e)}"}

def call_legacy_gateway(tool_name: str, args: dict, ctx: dict) -> dict:
    """Call legacy gateway for ECS/IAC tools using /call-tool endpoint"""
    aws_ctx = ctx.get("aws", {})
    shim_url = aws_ctx.get("shim_url", "http://internal-mcp-internal-alb-2059913293.us-east-1.elb.amazonaws.com")
    
    try:
        if tool_name == "ecs_call_tool":
            payload = {
                "server": "ecs",
                "tool": "ecs_resource_management", 
                "params": {
                    "api_operation": args.get("api_operation", "ListClusters"),
                    "api_params": args.get("api_params", {}),
                    "account_id": args.get("account_id", "500330120558"),
                    "region": args.get("region", "us-east-1")
                }
            }
        elif tool_name == "iac_call_tool":
            payload = {
                "server": "iac",
                "tool": "troubleshoot_cloudformation_deployment",
                "params": {
                    "stack_name": args.get("stack_name", ""),
                    "account_id": args.get("account_id", "500330120558"),
                    "region": args.get("region", "us-east-1")
                }
            }
        else:
            return {"error": f"Unknown legacy tool: {tool_name}"}
        
        response = requests.post(f"{shim_url}/call-tool", json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        return {"error": f"Legacy gateway call failed: {str(e)}"}

    try:
        response = requests.post(f"{shim_url}/", json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        
        return {"result": result}
        
    except Exception as e:
        return {"error": f"Legacy gateway call failed: {str(e)}"}
    except Exception as e:
        return {"error": f"Legacy gateway call failed: {str(e)}"}
