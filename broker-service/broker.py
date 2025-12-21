#!/usr/bin/env python3
import json
import requests
import boto3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List

app = FastAPI(title="MCP Broker Service")

class AskRequest(BaseModel):
    question: str
    shim_url: str = "http://internal-mcp-internal-alb-2059913293.us-east-1.elb.amazonaws.com"
    account_id: str = "500330120558"
    region: str = "us-east-1"

@app.get("/health")
async def health_check():
    return {"status": "OK", "service": "MCP Broker"}

@app.post("/ask")
async def ask_question(request: AskRequest):
    try:
        tools = get_available_tools()
        result = call_bedrock(request.question, tools, request.shim_url)
        return {"response": result}
    except Exception as e:
        print(f"Error in /ask: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def call_bedrock(ask_text: str, tools: list, shim_url: str) -> str:
    bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
    
    # System prompt is passed separately in Converse API
    system_prompts = [{"text": "You are an AWS infrastructure assistant. Help with CloudFormation (iac_call_tool) and ECS (ecs_call_tool)."}]
    
    # Initialize message history
    messages = [{"role": "user", "content": [{"text": ask_text}]}]
    
    # Logic: Loop until the model provides a final text answer
    while True:
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

                # Call your shim/Fargate backend
                server_type = 'iac' if 'iac' in tool_name else 'ecs'
                result_data = call_shim_tool(
                    shim_url, 
                    server_type, 
                    tool_input.get('tool', ''), 
                    tool_input.get('params', {})
                )
                
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

def call_shim_tool(shim_url: str, server: str, tool: str, params: Dict[str, Any]) -> Dict[str, Any]:
    try:
        response = requests.post(
            f"{shim_url}/call-tool",
            json={"server": server, "tool": tool, "params": params},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

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
                            "tool": {"type": "string"},
                            "params": {
                                "type": "object",
                                "properties": {
                                    "account_id": {"type": "string"},
                                    "region": {"type": "string"},
                                    "cluster": {"type": "string"},
                                    "service": {"type": "string"}
                                },
                                "required": ["account_id", "region"]
                            }
                        },
                        "required": ["tool", "params"]
                    }
                }
            }
        }
    ]
