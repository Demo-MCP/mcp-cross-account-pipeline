#!/usr/bin/env python3
import json
import sys
import requests
import boto3
import argparse
from typing import Dict, Any

def call_bedrock(ask_text: str, tools: list, shim_url: str) -> str:
    """Call Bedrock with tool definitions and handle tool calls"""
    
    bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
    
    system_prompt = f"""You are an AWS infrastructure assistant. You can help with:
- CloudFormation stack status and deployments (use iac_call_tool)
- ECS service and task status (use ecs_call_tool)

Available tools:
{json.dumps(tools, indent=2)}

Always provide helpful, accurate information about AWS resources."""

    messages = [
        {
            "role": "user", 
            "content": ask_text
        }
    ]
    
    # Use Claude 3 Haiku (cheapest)
    response = bedrock.invoke_model(
        modelId='anthropic.claude-3-haiku-20240307-v1:0',
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "system": system_prompt,
            "messages": messages,
            "tools": tools
        })
    )
    
    result = json.loads(response['body'].read())
    
    # Handle tool calls
    if result.get('content') and any(block.get('type') == 'tool_use' for block in result['content']):
        for block in result['content']:
            if block.get('type') == 'tool_use':
                tool_name = block['name']
                tool_input = block['input']
                
                # Execute tool call via shim
                if tool_name == 'iac_call_tool':
                    tool_result = call_shim_tool(shim_url, 'iac', tool_input['tool'], tool_input['params'])
                elif tool_name == 'ecs_call_tool':
                    tool_result = call_shim_tool(shim_url, 'ecs', tool_input['tool'], tool_input['params'])
                else:
                    tool_result = {"error": f"Unknown tool: {tool_name}"}
                
                # Send tool result back to Bedrock
                messages.append({
                    "role": "assistant",
                    "content": result['content']
                })
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": block['id'],
                            "content": json.dumps(tool_result)
                        }
                    ]
                })
                
                # Get final response
                final_response = bedrock.invoke_model(
                    modelId='anthropic.claude-3-haiku-20240307-v1:0',
                    body=json.dumps({
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 1000,
                        "system": system_prompt,
                        "messages": messages
                    })
                )
                
                final_result = json.loads(final_response['body'].read())
                return extract_text_content(final_result['content'])
    
    return extract_text_content(result['content'])

def extract_text_content(content):
    """Extract text from Bedrock response content"""
    if isinstance(content, list):
        for block in content:
            if block.get('type') == 'text':
                return block['text']
    return str(content)

def call_shim_tool(shim_url: str, server: str, tool: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Call MCP tool via HTTP shim"""
    try:
        response = requests.post(
            f"{shim_url}/call-tool",
            json={
                "server": server,
                "tool": tool,
                "params": params
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def get_available_tools(shim_url: str) -> list:
    """Get available tools from both MCP servers"""
    tools = []
    
    # Define simplified tool schemas for Bedrock
    tools.extend([
        {
            "name": "iac_call_tool",
            "description": "Call Infrastructure as Code (CloudFormation) tools",
            "input_schema": {
                "type": "object",
                "properties": {
                    "tool": {"type": "string", "description": "Tool name (e.g., describe_stacks, describe_stack_events)"},
                    "params": {
                        "type": "object",
                        "properties": {
                            "account_id": {"type": "string"},
                            "region": {"type": "string"},
                            "stack_name": {"type": "string", "description": "CloudFormation stack name"}
                        },
                        "required": ["account_id", "region"]
                    }
                },
                "required": ["tool", "params"]
            }
        },
        {
            "name": "ecs_call_tool", 
            "description": "Call ECS (Elastic Container Service) tools",
            "input_schema": {
                "type": "object",
                "properties": {
                    "tool": {"type": "string", "description": "Tool name (e.g., describe_services, list_tasks)"},
                    "params": {
                        "type": "object",
                        "properties": {
                            "account_id": {"type": "string"},
                            "region": {"type": "string"},
                            "cluster": {"type": "string", "description": "ECS cluster name"},
                            "service": {"type": "string", "description": "ECS service name"}
                        },
                        "required": ["account_id", "region"]
                    }
                },
                "required": ["tool", "params"]
            }
        }
    ])
    
    return tools

def main():
    parser = argparse.ArgumentParser(description='MCP Broker for GitHub workflows')
    parser.add_argument('--ask', required=True, help='Question to ask')
    parser.add_argument('--shim-url', default='http://internal-mcp-internal-alb-2059913293.us-east-1.elb.amazonaws.com', help='MCP shim URL')
    parser.add_argument('--account-id', default='500330120558', help='AWS account ID')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    
    args = parser.parse_args()
    
    try:
        tools = get_available_tools(args.shim_url)
        result = call_bedrock(args.ask, tools, args.shim_url)
        print(result)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
