#!/usr/bin/env python3
import json
import os
import requests
import boto3
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List
from tool_policy import is_tool_allowed
from agents.correlation import get_or_create_correlation_id, add_correlation_headers
from agents.tool_policy import get_denied_tool_response

app = FastAPI(title="MCP Broker Service")

# Correlation ID Middleware
class CorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Extract or create correlation ID
        correlation_id = get_or_create_correlation_id(
            dict(request.headers),
            getattr(request.state, 'metadata', {}),
            getattr(request.state, 'prompt', '')
        )
        
        # Store in request state
        request.state.correlation_id = correlation_id
        
        # Process request
        response = await call_next(request)
        
        # Add to response headers
        response.headers['x-correlation-id'] = correlation_id
        
        return response

app.add_middleware(CorrelationMiddleware)

# Cache tools at startup to avoid delays on each request
_cached_tools = None

def initialize_tools():
    """Initialize tools cache at startup"""
    global _cached_tools
    _cached_tools = get_available_tools()
    print(f"[STARTUP] Cached {len(_cached_tools)} tools")

def get_filtered_tools(tier: str) -> List[Dict]:
    """Get tools filtered by tier policy with fail-closed security"""
    if not _cached_tools:
        initialize_tools()
    
    from agents.tool_policy import is_tool_allowed
    
    filtered_tools = []
    for tool in _cached_tools:
        tool_name = tool["toolSpec"]["name"]
        if is_tool_allowed(tool_name, tier):
            filtered_tools.append(tool)
    
    print(f"[TOOLS] {tier} tier: {len(filtered_tools)}/{len(_cached_tools)} tools allowed")
    return filtered_tools

@app.on_event("startup")
async def startup_event():
    initialize_tools()

class AskRequest(BaseModel):
    ask_text: str  # Changed from question to ask_text for workflow alignment
    shim_url: str = "http://internal-mcp-internal-alb-2059913293.us-east-1.elb.amazonaws.com"
    account_id: str = "500330120558"
    region: str = "us-east-1"
    metadata: Dict[str, Any] = {}

class AdminRequest(BaseModel):
    ask_text: str
    shim_url: str = "http://internal-mcp-internal-alb-2059913293.us-east-1.elb.amazonaws.com"
    account_id: str = "500330120558"
    region: str = "us-east-1"
    metadata: Dict[str, Any] = {}

@app.get("/health")
async def health_check():
    return {"status": "OK", "service": "MCP Broker"}

@app.get("/tools")
async def list_tools():
    """Debug endpoint to list available tools by tier"""
    from agents.tool_policy import get_tool_counts_by_tier, USER_ALLOWED_TOOL_NAMES, ALL_ADMIN_TOOLS
    
    counts = get_tool_counts_by_tier()
    
    return {
        "user_tools": list(USER_ALLOWED_TOOL_NAMES),
        "admin_tools": list(ALL_ADMIN_TOOLS),
        "counts": counts,
        "total_available": len(_cached_tools) if _cached_tools else 0
    }

@app.post("/ask")
async def ask_question(request: AskRequest, req: Request):
    try:
        # Store metadata and prompt for correlation ID
        req.state.metadata = request.metadata
        req.state.prompt = request.ask_text
        
        correlation_id = req.state.correlation_id
        print(f"[ASK] Question: {request.ask_text} | Correlation: {correlation_id}")
        return await handle_request(request, tier="user", correlation_id=correlation_id)
    except Exception as e:
        print(f"Error in /ask: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin")
async def admin_question(request: AdminRequest, req: Request):
    try:
        # Store metadata and prompt for correlation ID
        req.state.metadata = request.metadata
        req.state.prompt = request.ask_text
        
        correlation_id = req.state.correlation_id
        print(f"[ADMIN] Question: {request.ask_text} | Correlation: {correlation_id}")
        return await handle_request(request, tier="admin", correlation_id=correlation_id)
    except Exception as e:
        print(f"Error in /admin: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def handle_request(request, tier: str, correlation_id: str):
    """Shared handler for both /ask and /admin endpoints"""
    import time
    start_time = time.time()
    
    # A) Filter tools by tier before sending to model
    filtered_tools = get_filtered_tools(tier)
    tools_called = []
    denied_tool_calls = []
    
    result = call_bedrock(request.ask_text, filtered_tools, request.shim_url, request.account_id, request.region, request.metadata, tier, tools_called, denied_tool_calls, correlation_id)
    
    total_ms = int((time.time() - start_time) * 1000)
    
    return {
        "answer": result,
        "debug": {
            "tier": tier,
            "correlation_id": correlation_id,
            "tools_advertised_count": len(filtered_tools),
            "tools_called": tools_called,
            "denied_tool_calls": denied_tool_calls,
            "total_ms": total_ms
        }
    }

def call_bedrock(ask_text: str, tools: list, shim_url: str, account_id: str, region: str, metadata: Dict[str, Any], tier: str, tools_called: List[str], denied_tool_calls: List[str], correlation_id: str) -> str:
    bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
    
    # System prompt is passed separately in Converse API
    system_prompts = [{"text": "You are an AWS infrastructure assistant. For ECS operations, use ecs_call_tool with tool='ecs_resource_management'. ALWAYS include api_operation (e.g., 'ListClusters', 'DescribeServices') and api_params object. For ListClusters, use empty api_params: {}. For DescribeServices, put cluster name and services array in api_params. Example: {\"tool\": \"ecs_resource_management\", \"params\": {\"api_operation\": \"ListClusters\", \"api_params\": {}, \"account_id\": \"500330120558\", \"region\": \"us-east-1\"}}. For CloudFormation, use iac_call_tool with tool='troubleshoot_cloudformation_deployment'. Example: {\"tool\": \"troubleshoot_cloudformation_deployment\", \"params\": {\"stack_name\": \"my-stack\", \"account_id\": \"500330120558\", \"region\": \"us-east-1\"}}. Always include account_id='500330120558' and region='us-east-1', if this information is not provided."}]
    
    # Initialize message history
    messages = [{"role": "user", "content": [{"text": ask_text}]}]
    
    # Logic: Loop until the model provides a final text answer
    iteration = 0
    while iteration < 10:
        iteration += 1
        print(f"[BEDROCK] Iteration {iteration} | Correlation: {correlation_id}")
        
        # Use Converse API for Nova Pro
        response = bedrock.converse(
            modelId='us.amazon.nova-pro-v1:0',
            messages=messages,
            system=system_prompts,
            toolConfig={"tools": tools},
            inferenceConfig={
                "maxTokens": 4096, 
                "temperature": 0  # Greedy decoding prevents JSON "invalid sequence"
            }
        )
        
        print(f"[BEDROCK] Stop reason: {response['stopReason']}")
        
        output_message = response['output']['message']
        messages.append(output_message)
        
        # Stop if the model is done or hit a limit
        if response['stopReason'] != 'tool_use':
            # Extract final text answer
            for block in output_message['content']:
                if 'text' in block:
                    return block['text']
            return "No text response received from model."

        # Handle tool calls
        tool_results = []
        for block in output_message['content']:
            if 'toolUse' in block:
                tool_use = block['toolUse']
                tool_name = tool_use['name']
                tool_input = tool_use['input']
                
                print(f"Executing tool: {tool_name}")
                print(f"[BEDROCK] Tool input: {tool_input}")

                # B) Enforce tool execution gating - fail closed
                if not is_tool_allowed(tool_name, tier):
                    error_response = get_denied_tool_response(tool_name, tier, correlation_id)
                    print(f"[SECURITY] {error_response['message']} | Correlation: {correlation_id}")
                    denied_tool_calls.append(tool_name)
                    
                    tool_results.append({
                        "toolResult": {
                            "toolUseId": tool_use['toolUseId'],
                            "content": [{"json": error_response}],
                            "status": "error"
                        }
                    })
                    continue
                
                # Tool is allowed, track it and execute
                tools_called.append(tool_name)

                # Route to appropriate MCP backend
                if tool_name.startswith('pr_'):
                    # Route PR tools to PR Context MCP
                    result_data = call_mcp_tool(f"{shim_url}/pr", tool_name, tool_input, metadata, correlation_id)
                elif tool_name.startswith('pricingcalc_'):
                    # Route pricing calculator tools to pricing MCP server
                    result_data = call_pricing_tool(tool_name, tool_input, correlation_id)
                elif tool_name.startswith('deploy_'):
                    # Route deployment metrics tools to metrics MCP server
                    # Extract missing parameters from metadata
                    if metadata:
                        # Always prefer metadata repository over Bedrock's guess
                        if 'repository' in metadata:
                            tool_input['repository'] = metadata['repository']
                        elif 'repository' not in tool_input or '/' not in tool_input.get('repository', ''):
                            # No metadata repo and Bedrock didn't provide org/repo format, use default
                            tool_input['repository'] = 'Demo-MCP/mcp-cross-account-pipeline'
                        
                        # If run_id not provided, check metadata
                        if 'run_id' not in tool_input and 'run_id' in metadata:
                            tool_input['run_id'] = metadata['run_id']
                    else:
                        # No metadata, use default if repository not provided or doesn't look like org/repo
                        if 'repository' not in tool_input or '/' not in tool_input.get('repository', ''):
                            tool_input['repository'] = 'Demo-MCP/mcp-cross-account-pipeline'
                    
                    # If still no run_id, try to auto-select from latest runs
                    if 'run_id' not in tool_input and tool_name in ['deploy_get_summary', 'deploy_get_run', 'deploy_get_steps']:
                        try:
                            repo_name = tool_input['repository']
                            # First try to find RUNNING deployments
                            latest_runs_result = call_metrics_tool('deploy_find_latest', {'repository': repo_name, 'limit': 10})
                            if isinstance(latest_runs_result, dict) and 'result' in latest_runs_result:
                                result_text = latest_runs_result['result']
                                # Look for RUNNING status in the result
                                if 'RUNNING' in result_text:
                                    # Extract run_id from RUNNING deployment
                                    lines = result_text.split('\n')
                                    for i, line in enumerate(lines):
                                        if 'RUNNING' in line and i > 0:
                                            # Look for Run ID in previous lines
                                            for j in range(i-1, max(i-5, -1), -1):
                                                if 'Run ID:' in lines[j]:
                                                    run_id = lines[j].split('Run ID:')[1].strip()
                                                    tool_input['run_id'] = run_id
                                                    print(f"[METRICS] Auto-selected RUNNING deployment: {run_id}")
                                                    break
                                            break
                                else:
                                    # No RUNNING deployment, use latest (first in list)
                                    lines = result_text.split('\n')
                                    for line in lines:
                                        if 'Run ID:' in line:
                                            run_id = line.split('Run ID:')[1].strip()
                                            tool_input['run_id'] = run_id
                                            print(f"[METRICS] Auto-selected latest deployment: {run_id}")
                                            break
                        except Exception as e:
                            print(f"[METRICS] Could not auto-select run: {e}")
                    
                    result_data = call_metrics_tool(tool_name, tool_input, correlation_id)
                else:
                    # Route to existing MCP servers via gateway
                    server_type = 'iac' if 'iac' in tool_name else 'ecs'
                    result_data = call_shim_tool(
                        shim_url, 
                        server_type, 
                        tool_input.get('tool', ''), 
                        {**tool_input.get('params', {}), 'account_id': account_id, 'region': region, '_metadata': metadata},
                        correlation_id
                    )
                
                print(f"[BEDROCK] Tool result: {result_data}")
                
                # Format the result for the next turn
                tool_results.append({
                    "toolResult": {
                        "toolUseId": tool_use['toolUseId'],
                        "content": [{"json": result_data}],
                        "status": "success"
                    }
                })
        
        # Add tool results to conversation and loop back
        messages.append({"role": "user", "content": tool_results})

    return "Reached maximum iteration limit."

def call_shim_tool(shim_url: str, server: str, tool: str, params: Dict[str, Any], correlation_id: str) -> Dict[str, Any]:
    try:
        print(f"[SHIM] Calling {server}/{tool} | Correlation: {correlation_id}")
        
        headers = add_correlation_headers({"Content-Type": "application/json"}, correlation_id)
        
        response = requests.post(
            f"{shim_url}/call-tool",
            json={"server": server, "tool": tool, "params": params},
            headers=headers,
            timeout=120
        )
        response.raise_for_status()
        print(f"[SHIM] Success: {server}/{tool} | Correlation: {correlation_id}")
        return response.json()
    except requests.exceptions.Timeout:
        error_msg = f"Timeout calling {server}/{tool} after 120 seconds | Correlation: {correlation_id}"
        print(f"[SHIM] {error_msg}")
        return {"error": error_msg}
    except Exception as e:
        error_msg = f"Error calling {server}/{tool}: {str(e)} | Correlation: {correlation_id}"
        print(f"[SHIM] {error_msg}")
        return {"error": error_msg}

def call_metrics_tool(tool_name: str, tool_input: Dict[str, Any], correlation_id: str) -> Dict[str, Any]:
    """Call deployment metrics MCP server directly via ALB"""
    try:
        # Get ALB URL from environment or use actual ALB
        alb_url = os.environ.get('ALB_URL', 'http://internal-mcp-internal-alb-2059913293.us-east-1.elb.amazonaws.com')
        
        print(f"[METRICS] Calling {tool_name} | Correlation: {correlation_id}")
        
        # Format as MCP JSON-RPC 2.0 request
        mcp_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": tool_input
            }
        }
        
        headers = add_correlation_headers({"Content-Type": "application/json"}, correlation_id)
        
        response = requests.post(
            f"{alb_url}/metrics",
            json=mcp_request,
            headers=headers,
            timeout=50
        )
        response.raise_for_status()
        
        result = response.json()
        print(f"[METRICS] Success: {tool_name} | Correlation: {correlation_id}")
        
        # Extract result from MCP response
        if 'result' in result and 'content' in result['result']:
            content = result['result']['content']
            if isinstance(content, list) and len(content) > 0:
                if 'text' in content[0]:
                    # For text responses, wrap in JSON structure for Bedrock
                    text_content = content[0]['text']
                    try:
                        # Try to parse as JSON first
                        return json.loads(text_content)
                    except:
                        # If not JSON, wrap text in a structured object
                        return {"result": text_content, "type": "text"}
                elif 'json' in content[0]:
                    return content[0]['json']
            return content
        return result.get('result', result)
        
    except Exception as e:
        print(f"[METRICS] Error calling {tool_name}: {e} | Correlation: {correlation_id}")
        return {"error": str(e)}

def call_mcp_tool(mcp_url: str, tool_name: str, tool_input: Dict[str, Any], metadata: Dict[str, Any] = None, correlation_id: str = None) -> Dict[str, Any]:
    """Call MCP service tool directly"""
    try:
        print(f"[MCP] Calling {mcp_url} tool {tool_name} | Correlation: {correlation_id}")
        
        # Map parameters for PR tools
        if tool_name.startswith('pr_') and metadata:
            mapped_input = {
                'repo': metadata.get('repository', 'Demo-MCP/mcp-cross-account-pipeline'),
                'pr_number': metadata.get('pr_number', tool_input.get('pr_number')),
                'actor': metadata.get('actor', 'admin'),
                'run_id': metadata.get('run_id', '12345')
            }
            # Add any additional parameters from tool_input
            for key, value in tool_input.items():
                if key not in mapped_input:
                    mapped_input[key] = value
            tool_input = mapped_input
        
        headers = add_correlation_headers({"Content-Type": "application/json"}, correlation_id)
        
        response = requests.post(
            mcp_url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": tool_input
                }
            },
            headers=headers,
            timeout=120
        )
        response.raise_for_status()
        result = response.json()
        
        if "error" in result:
            return {"error": result["error"]["message"]}
        
        return result.get("result", {})
        
    except requests.exceptions.Timeout:
        return {"error": f"MCP tool {tool_name} timed out after 120 seconds | Correlation: {correlation_id}"}
    except Exception as e:
        return {"error": f"MCP tool {tool_name} failed: {str(e)} | Correlation: {correlation_id}"}

def call_pricing_tool(tool_name: str, tool_input: Dict[str, Any], correlation_id: str) -> Dict[str, Any]:
    """Call pricing calculator MCP server directly via ALB"""
    try:
        # Get ALB URL from environment or use actual ALB
        alb_url = os.environ.get('ALB_URL', 'http://internal-mcp-internal-alb-2059913293.us-east-1.elb.amazonaws.com')
        
        print(f"[PRICING] Calling {tool_name} | Correlation: {correlation_id}")
        
        # Format as MCP JSON-RPC 2.0 request
        mcp_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": tool_input
            }
        }
        
        headers = add_correlation_headers({"Content-Type": "application/json"}, correlation_id)
        
        response = requests.post(
            f"{alb_url}/pricingcalc",
            json=mcp_request,
            headers=headers,
            timeout=60
        )
        response.raise_for_status()
        
        result = response.json()
        print(f"[PRICING] Success: {tool_name} | Correlation: {correlation_id}")
        
        # Extract result from MCP response - pricing tools return direct JSON
        return result
        
    except Exception as e:
        print(f"[PRICING] Error calling {tool_name}: {e} | Correlation: {correlation_id}")
        return {"error": str(e)}

def get_available_tools() -> list:
    """Get tools - static IAC/ECS + dynamic metrics tools"""
    # Static IAC and ECS tools
    tools = [
        {
            "toolSpec": {
                "name": "iac_call_tool",
                "description": "Call Infrastructure as Code tools",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "tool": {"type": "string"},
                            "params": {
                                "type": "object",
                                "properties": {
                                    "account_id": {"type": "string"},
                                    "region": {"type": "string"},
                                    "stack_name": {"type": "string"}
                                },
                                "required": ["account_id", "region"]
                            }
                        },
                        "required": ["tool", "params"]
                    }
                }
            }
        },
        {
            "toolSpec": {
                "name": "ecs_call_tool",
                "description": "Call ECS tools",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "tool": {"type": "string"},
                            "params": {
                                "type": "object",
                                "properties": {
                                    "api_operation": {"type": "string"},
                                    "api_params": {"type": "object"},
                                    "account_id": {"type": "string"},
                                    "region": {"type": "string"}
                                },
                                "required": ["api_operation", "api_params", "account_id", "region"]
                            }
                        },
                        "required": ["tool", "params"]
                    }
                }
            }
        }
    ]
    
    # Dynamically fetch metrics tools
    try:
        alb_url = os.environ.get('ALB_URL', 'http://internal-mcp-internal-alb-2059913293.us-east-1.elb.amazonaws.com')
        response = requests.post(
            f"{alb_url}/metrics",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        if response.status_code == 200:
            result = response.json()
            if 'result' in result and 'tools' in result['result']:
                for tool in result['result']['tools']:
                    tools.append({
                        "toolSpec": {
                            "name": tool['name'],
                            "description": tool['description'],
                            "inputSchema": {"json": tool['inputSchema']}
                        }
                    })
                print(f"[TOOLS] Added {len(result['result']['tools'])} metrics tools")
    except Exception as e:
        print(f"[TOOLS] Failed to fetch metrics tools: {e}")
    
    # Dynamically fetch pricing calculator tools
    try:
        response = requests.post(
            f"{alb_url}/pricingcalc",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        if response.status_code == 200:
            result = response.json()
            if 'result' in result and 'tools' in result['result']:
                for tool in result['result']['tools']:
                    tools.append({
                        "toolSpec": {
                            "name": tool['name'],
                            "description": tool['description'],
                            "inputSchema": {"json": tool['inputSchema']}
                        }
                    })
                print(f"[TOOLS] Added {len(result['result']['tools'])} pricing calculator tools")
    except Exception as e:
        print(f"[TOOLS] Failed to fetch pricing calculator tools: {e}")
    
    # Dynamically fetch PR tools
    try:
        response = requests.post(
            f"{alb_url}/pr",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        if response.status_code == 200:
            result = response.json()
            if 'result' in result and 'tools' in result['result']:
                for tool in result['result']['tools']:
                    tools.append({
                        "toolSpec": {
                            "name": tool['name'],
                            "description": tool['description'],
                            "inputSchema": {"json": tool['inputSchema']}
                        }
                    })
                print(f"[TOOLS] Added {len(result['result']['tools'])} PR tools")
    except Exception as e:
        print(f"[TOOLS] Failed to fetch PR tools: {e}")
    
    return tools

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
