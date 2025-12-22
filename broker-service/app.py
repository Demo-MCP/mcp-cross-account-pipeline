#!/usr/bin/env python3
import json
import requests
import boto3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List

app = FastAPI(title="MCP Broker Service")

class AskRequest(BaseModel):
    ask_text: str  # Changed from question to ask_text for workflow alignment
    shim_url: str = "http://internal-mcp-internal-alb-2059913293.us-east-1.elb.amazonaws.com"
    account_id: str = "500330120558"
    region: str = "us-east-1"
    metadata: Dict[str, Any] = {}

@app.get("/health")
async def health_check():
    return {"status": "OK", "service": "MCP Broker"}

@app.post("/ask")
async def ask_question(request: AskRequest):
    try:
        print(f"[ASK] Question: {request.ask_text}")
        tools = get_available_tools()
        result = call_bedrock(request.ask_text, tools, request.shim_url, request.account_id, request.region, request.metadata)
        print(f"[ASK] Response: {result}")
        return {"answer": result}  # Changed from response to answer for workflow alignment
    except Exception as e:
        print(f"Error in /ask: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def call_bedrock(ask_text: str, tools: list, shim_url: str, account_id: str, region: str, metadata: Dict[str, Any]) -> str:
    bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
    
    # System prompt is passed separately in Converse API
    system_prompts = [{"text": "You are an AWS infrastructure assistant. For ECS operations, use ecs_call_tool with tool='ecs_resource_management'. ALWAYS include api_operation (e.g., 'ListClusters', 'DescribeServices') and api_params object. For ListClusters, use empty api_params: {}. For DescribeServices, put cluster name and services array in api_params. Example: {\"tool\": \"ecs_resource_management\", \"params\": {\"api_operation\": \"ListClusters\", \"api_params\": {}, \"account_id\": \"500330120558\", \"region\": \"us-east-1\"}}. For CloudFormation, use iac_call_tool with tool='troubleshoot_cloudformation_deployment'. Always include account_id='500330120558' and region='us-east-1'."}]
    
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

def get_available_tools() -> list:
    """Corrected toolSpec format for Nova Pro"""
    return [
        {
            "toolSpec": {
                "name": "iac_call_tool",
                "description": "Call Infrastructure as Code tools",
                "inputSchema": {
                    "json": { # Required 'json' wrapper
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
                            "tool": {"type": "string", "description": "Always use 'ecs_resource_management'"},
                            "params": {
                                "type": "object",
                                "properties": {
                                    "api_operation": {"type": "string", "description": "ECS API operation like 'ListClusters', 'DescribeServices'"},
                                    "api_params": {
                                        "type": "object",
                                        "description": "Parameters for the API operation",
                                        "properties": {
                                            "cluster": {"type": "string"},
                                            "services": {"type": "array", "items": {"type": "string"}}
                                        }
                                    },
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
