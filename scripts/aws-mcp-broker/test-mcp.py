#!/usr/bin/env python3
import asyncio
from mcp.server import Server
from mcp.types import Tool
import mcp.server.stdio

server = Server("test-mcp")

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="test_tool",
            description="Test tool",
            inputSchema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    return [{"type": "text", "text": f"Called {name} with {arguments}"}]

async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
