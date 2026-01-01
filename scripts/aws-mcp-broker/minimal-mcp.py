#!/usr/bin/env python3
import asyncio
import json
import os
import subprocess
import requests
from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio

server = Server("aws-mcp-broker")

@server.list_tools()
async def list_tools():
    """Fetch cloud tools and add local tools"""
    try:
        # Fetch cloud tools
        response = requests.get("https://d0yrd186v6.execute-api.us-east-1.amazonaws.com/prod/tools", timeout=10)
        data = response.json()
        
        tools = []
        
        # Add cloud tools
        for tool_name in data.get('user_tools', []):
            tools.append(Tool(
                name=tool_name,
                description=f"Cloud tool: {tool_name}",
                inputSchema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
            ))
        
        # Add local deploy_local tool
        tools.append(Tool(
            name="deploy_local",
            description="Deploy locally by posting deploy comment to PR",
            inputSchema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
        ))
        
        return tools
        
    except Exception as e:
        # Fallback with basic tools
        return [
            Tool(
                name="deploy_local",
                description="Deploy locally by posting deploy comment to PR",
                inputSchema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
            ),
            Tool(
                name="error_info",
                description=f"MCP Error: {str(e)}",
                inputSchema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
            )
        ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """Handle tool calls"""
    if name == "deploy_local":
        return [TextContent(type="text", text="Deploy local tool called - basic test")]
    elif name == "error_info":
        return [TextContent(type="text", text=f"Error info: {arguments}")]
    else:
        return [TextContent(type="text", text=f"Cloud tool {name} called with {arguments}")]

async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
