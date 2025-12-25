from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional, Union
import json
import logging
from db import get_db_connection
from mcp_protocol import handle_mcp_request

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Deployment Metrics MCP Server")

class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Union[str, int]
    method: str
    params: Optional[Dict[str, Any]] = None

class JSONRPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: Union[str, int]
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

@app.get("/health")
async def health_check():
    """Health check endpoint for ALB"""
    try:
        # Test database connection
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return {"status": "healthy", "service": "deployment-metrics-mcp"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Database connection failed")

@app.post("/metrics")
async def mcp_endpoint(request: JSONRPCRequest):
    """MCP JSON-RPC endpoint"""
    try:
        logger.info(f"Received MCP request: {request.method}")
        
        # Handle MCP request
        result = await handle_mcp_request(request.method, request.params)
        
        return JSONRPCResponse(
            id=request.id,
            result=result
        )
        
    except Exception as e:
        logger.error(f"MCP request failed: {e}")
        return JSONRPCResponse(
            id=request.id,
            error={
                "code": -32603,
                "message": "Internal error",
                "data": str(e)
            }
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
