#!/usr/bin/env python3
import json
import os
import requests
import boto3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List

app = FastAPI(title="MCP Broker Service")

# Cache tools at startup to avoid delays on each request
_cached_tools = None

def initialize_tools():
    """Initialize tools cache at startup"""
    global _cached_tools
    _cached_tools = get_available_tools()
    print(f"[STARTUP] Cached {len(_cached_tools)} tools")

@app.on_event("startup")
async def startup_event():
    initialize_tools()

class AskRequest(BaseModel):
    ask_text: str  # Changed from question to ask_text for workflow alignment
    shim_url: str = "http://internal-mcp-internal-alb-2059913293.us-east-1.elb.amazonaws.com"
    account_id: str = "500330120558"
    region: str = "us-east-1"
    metadata: Dict[str, Any] = {}

@app.get("/health")
async def health_check():
    return {"status": "OK", "service": "MCP Broker"}

@app.get("/tools")
async def list_tools():
    """List all available tools for debugging"""
    return {"tools": [tool["toolSpec"]["name"] for tool in _cached_tools], "count": len(_cached_tools)}

@app.post("/ask")
async def ask_question(request: AskRequest):
    try:
        print(f"[ASK] Question: {request.ask_text}")
        result = call_bedrock(request.ask_text, _cached_tools, request.shim_url, request.account_id, request.region, request.metadata)
        print(f"[ASK] Response: {result}")
        return {"answer": result}  # Changed from response to answer for workflow alignment
    except Exception as e:
        print(f"Error in /ask: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def call_bedrock(ask_text: str, tools: list, shim_url: str, account_id: str, region: str, metadata: Dict[str, Any]) -> str:
    bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
    
    # System prompt is passed separately in Converse API
    system_prompts = [{"text": "You are an AWS infrastructure assistant. For ECS operations, use ecs_call_tool with tool='ecs_resource_management'. ALWAYS include api_operation (e.g., 'ListClusters', 'DescribeServices') and api_params object. For ListClusters, use empty api_params: {}. For DescribeServices, put cluster name and services array in api_params. Example: {\"tool\": \"ecs_resource_management\", \"params\": {\"api_operation\": \"ListClusters\", \"api_params\": {}, \"account_id\": \"500330120558\", \"region\": \"us-east-1\"}}. For CloudFormation, use iac_call_tool with tool='troubleshoot_cloudformation_deployment'. Example: {\"tool\": \"troubleshoot_cloudformation_deployment\", \"params\": {\"stack_name\": \"my-stack\", \"account_id\": \"500330120558\", \"region\": \"us-east-1\"}}. Always include account_id='500330120558' and region='us-east-1', if this information is not provided."}]
    
    # Initialize message history
    messages = [{"role": "user", "content": [{"text": ask_text}]}]
    
    # Logic: Loop until the model provides a final text answer
    iteration = 0
    while iteration < 10:
        iteration += 1
        print(f"[BEDROCK] Iteration {iteration}")
        
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

                # Call your shim/Fargate backend
                if tool_name.startswith('pricingcalc_'):
                    # Route pricing calculator tools to pricing MCP server
                    result_data = call_pricing_tool(tool_name, tool_input)
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
                    
                    result_data = call_metrics_tool(tool_name, tool_input)
                else:
                    # Route to existing MCP servers via gateway
                    server_type = 'iac' if 'iac' in tool_name else 'ecs'
                    result_data = call_shim_tool(
                        shim_url, 
                        server_type, 
                        tool_input.get('tool', ''), 
                        {**tool_input.get('params', {}), 'account_id': account_id, 'region': region, '_metadata': metadata}
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

def call_shim_tool(shim_url: str, server: str, tool: str, params: Dict[str, Any]) -> Dict[str, Any]:
    try:
        print(f"[SHIM] Calling {server}/{tool} with timeout=120s")
        response = requests.post(
            f"{shim_url}/call-tool",
            json={"server": server, "tool": tool, "params": params},
            timeout=120
        )
        response.raise_for_status()
        print(f"[SHIM] Success: {server}/{tool}")
        return response.json()
    except requests.exceptions.Timeout:
        error_msg = f"Timeout calling {server}/{tool} after 120 seconds"
        print(f"[SHIM] {error_msg}")
        return {"error": error_msg}
    except Exception as e:
        error_msg = f"Error calling {server}/{tool}: {str(e)}"
        print(f"[SHIM] {error_msg}")
        return {"error": error_msg}

def call_metrics_tool(tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Call deployment metrics MCP server directly via ALB"""
    try:
        # Get ALB URL from environment or use actual ALB
        alb_url = os.environ.get('ALB_URL', 'http://internal-mcp-internal-alb-2059913293.us-east-1.elb.amazonaws.com')
        
        print(f"[METRICS] Calling {tool_name} with timeout=50s")
        
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
        
        response = requests.post(
            f"{alb_url}/metrics",
            json=mcp_request,
            headers={"Content-Type": "application/json"},
            timeout=50
        )
        response.raise_for_status()
        
        result = response.json()
        print(f"[METRICS] Success: {tool_name}")
        
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
        print(f"[METRICS] Error calling {tool_name}: {e}")
        return {"error": str(e)}

def call_pricing_tool(tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Call pricing calculator MCP server directly via ALB"""
    try:
        # Get ALB URL from environment or use actual ALB
        alb_url = os.environ.get('ALB_URL', 'http://internal-mcp-internal-alb-2059913293.us-east-1.elb.amazonaws.com')
        
        print(f"[PRICING] Calling {tool_name} with timeout=90s")
        
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
        
        response = requests.post(
            f"{alb_url}/pricingcalc",
            json=mcp_request,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        response.raise_for_status()
        
        result = response.json()
        print(f"[PRICING] Success: {tool_name}")
        
        # Extract result from MCP response - pricing tools return direct JSON
        return result
        
    except Exception as e:
        print(f"[PRICING] Error calling {tool_name}: {e}")
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
    except Exception as e:
        print(f"[TOOLS] Error fetching metrics tools: {e}")
    
    return tools

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
