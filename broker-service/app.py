from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import json
import requests
import boto3
import time
import uvicorn

app = FastAPI(title="MCP Broker Service", version="1.0.0")

class AskRequest(BaseModel):
    ask_text: str
    account_id: str = "500330120558"
    region: str = "us-east-1"
    metadata: Dict[str, Any] = {}
    shim_url: str = "http://internal-mcp-internal-alb-2059913293.us-east-1.elb.amazonaws.com"

class AskResponse(BaseModel):
    answer: str
    debug: Dict[str, Any]

@app.get("/health")
async def health_check():
    return {"ok": True}

@app.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    start_time = time.time()
    debug = {}
    
    try:
        # Get available tools
        tools = get_tool_definitions()
        
        # First Bedrock call
        bedrock_start = time.time()
        bedrock_response = call_bedrock_with_tools(request.ask_text, tools)
        debug["bedrock_first_call_ms"] = int((time.time() - bedrock_start) * 1000)
        
        # Check if model wants to use tools
        if has_tool_calls(bedrock_response):
            # Execute tool calls
            shim_start = time.time()
            tool_results = []
            
            for tool_call in extract_tool_calls(bedrock_response):
                tool_result = execute_tool_call(tool_call, request, debug)
                tool_results.append(tool_result)
            
            debug["shim_call_ms"] = int((time.time() - shim_start) * 1000)
            
            # Final Bedrock call with tool results
            final_start = time.time()
            final_response = call_bedrock_with_results(request.ask_text, tools, bedrock_response, tool_results)
            debug["bedrock_final_call_ms"] = int((time.time() - final_start) * 1000)
            
            answer = extract_text_from_response(final_response)
        else:
            answer = extract_text_from_response(bedrock_response)
        
        debug["total_ms"] = int((time.time() - start_time) * 1000)
        
        return AskResponse(answer=answer, debug=debug)
        
    except Exception as e:
        debug["error"] = str(e)
        debug["total_ms"] = int((time.time() - start_time) * 1000)
        return AskResponse(answer=f"Error: {str(e)}", debug=debug)

def get_tool_definitions():
    return [
        {
            "name": "iac_call_tool",
            "description": "Call Infrastructure as Code (CloudFormation) tools for stack status and deployments",
            "input_schema": {
                "type": "object",
                "properties": {
                    "tool": {"type": "string", "description": "Tool name (e.g., describe_stacks, describe_stack_events)"},
                    "params": {
                        "type": "object",
                        "properties": {
                            "stack_name": {"type": "string", "description": "CloudFormation stack name"}
                        }
                    }
                },
                "required": ["tool", "params"]
            }
        },
        {
            "name": "ecs_call_tool",
            "description": "Call ECS (Elastic Container Service) tools for service and task status",
            "input_schema": {
                "type": "object",
                "properties": {
                    "tool": {"type": "string", "description": "Tool name (e.g., describe_services, list_tasks)"},
                    "params": {
                        "type": "object",
                        "properties": {
                            "cluster": {"type": "string", "description": "ECS cluster name"},
                            "service": {"type": "string", "description": "ECS service name"}
                        }
                    }
                },
                "required": ["tool", "params"]
            }
        }
    ]

def call_bedrock_with_tools(ask_text: str, tools: list):
    bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
    
    system_prompt = """You are an AWS infrastructure assistant. You can help with:
- CloudFormation stack status and deployments (use iac_call_tool)
- ECS service and task status (use ecs_call_tool)

Always provide helpful, accurate information about AWS resources."""

    response = bedrock.invoke_model(
        modelId='anthropic.claude-3-haiku-20240307-v1:0',
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "system": system_prompt,
            "messages": [{"role": "user", "content": ask_text}],
            "tools": tools
        })
    )
    
    return json.loads(response['body'].read())

def has_tool_calls(bedrock_response):
    content = bedrock_response.get('content', [])
    return any(block.get('type') == 'tool_use' for block in content)

def extract_tool_calls(bedrock_response):
    tool_calls = []
    for block in bedrock_response.get('content', []):
        if block.get('type') == 'tool_use':
            tool_calls.append(block)
    return tool_calls

def execute_tool_call(tool_call, request: AskRequest, debug: dict):
    tool_name = tool_call['name']
    tool_input = tool_call['input']
    
    # Inject required parameters
    params = tool_input.get('params', {})
    params['account_id'] = request.account_id
    params['region'] = request.region
    params['_metadata'] = request.metadata
    
    # Determine server type
    server = 'iac' if tool_name == 'iac_call_tool' else 'ecs'
    
    try:
        response = requests.post(
            f"{request.shim_url}/call-tool",
            json={
                "server": server,
                "tool": tool_input['tool'],
                "params": params
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        debug[f"shim_error_{tool_name}"] = str(e)
        return {"error": str(e)}

def call_bedrock_with_results(ask_text: str, tools: list, first_response: dict, tool_results: list):
    bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
    
    # Build conversation with tool results
    messages = [
        {"role": "user", "content": ask_text},
        {"role": "assistant", "content": first_response['content']}
    ]
    
    # Add tool results
    for i, result in enumerate(tool_results):
        tool_call = extract_tool_calls(first_response)[i]
        messages.append({
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": tool_call['id'],
                "content": json.dumps(result)[:2000]  # Limit size
            }]
        })
    
    response = bedrock.invoke_model(
        modelId='anthropic.claude-3-haiku-20240307-v1:0',
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": messages
        })
    )
    
    return json.loads(response['body'].read())

def extract_text_from_response(bedrock_response):
    content = bedrock_response.get('content', [])
    for block in content:
        if block.get('type') == 'text':
            return block['text']
    return "No text response from model"

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
