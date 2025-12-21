from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, Literal
import json
import subprocess
import asyncio
import os
import uvicorn

app = FastAPI(title="MCP Gateway", version="1.0.0")

# Global subprocess managers
mcp_processes = {}

class ListToolsRequest(BaseModel):
    server: Literal["ecs", "iac"]

class CallToolRequest(BaseModel):
    server: Literal["ecs", "iac"]
    tool: str
    params: Dict[str, Any]

@app.get("/health")
async def health_check():
    return {"status": "OK", "service": "MCP Gateway"}

@app.post("/list-tools")
async def list_tools(request: ListToolsRequest):
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {}
    }
    return await call_mcp_server(request.server, mcp_request)

@app.post("/call-tool")
async def call_tool(request: CallToolRequest):
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": request.tool,
            "arguments": request.params
        }
    }
    return await call_mcp_server(request.server, mcp_request)

async def call_mcp_server(server_type: str, mcp_request: dict):
    try:
        # Get or create subprocess for this server type
        process = await get_mcp_process(server_type)
        
        # Send request to subprocess
        request_json = json.dumps(mcp_request) + '\n'
        process.stdin.write(request_json.encode())
        await process.stdin.drain()
        
        # Read response with timeout
        response_line = await asyncio.wait_for(
            process.stdout.readline(),
            timeout=30.0
        )
        
        if not response_line:
            raise Exception(f"No response from {server_type} MCP server")
        
        response = json.loads(response_line.decode().strip())
        return response
        
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail=f"{server_type} MCP server timeout")
    except Exception as e:
        # Restart the process if it failed
        if server_type in mcp_processes:
            try:
                mcp_processes[server_type].terminate()
            except:
                pass
            del mcp_processes[server_type]
        
        raise HTTPException(status_code=500, detail=f"{server_type} MCP server error: {str(e)}")

async def get_mcp_process(server_type: str):
    if server_type not in mcp_processes or mcp_processes[server_type].returncode is not None:
        # Start new process
        if server_type == "ecs":
            cmd = ['python', '-m', 'awslabs.ecs_mcp_server.main']
            cwd = '/app/ecs-mcp-server'
        elif server_type == "iac":
            cmd = ['python', '-m', 'awslabs.aws_iac_mcp_server.server']
            cwd = '/app/aws-iac-mcp-server'
        else:
            raise Exception(f"Unknown server type: {server_type}")
        
        env = os.environ.copy()
        env['PYTHONPATH'] = '/app:/app/platform_aws_context:/app/ecs-mcp-server:/app/aws-iac-mcp-server'
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=env
        )
        
        mcp_processes[server_type] = process
        
        # Wait a moment for the process to initialize
        await asyncio.sleep(1)
    
    return mcp_processes[server_type]

@app.on_event("shutdown")
async def shutdown_event():
    # Clean up subprocesses
    for process in mcp_processes.values():
        try:
            process.terminate()
            await process.wait()
        except:
            pass

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
