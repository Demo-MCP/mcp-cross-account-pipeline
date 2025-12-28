"""
Strands-based broker service with tier-based security and correlation ID tracking
"""
import time
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional

from agents.param_resolution import build_request_context
from agents.guards import check_intent_guards
from agents.agents import build_user_agent, build_admin_agent
from agents.tool_policy import USER_ALLOWED_TOOL_NAMES, ALL_ADMIN_TOOLS
from agents.correlation import get_or_create_correlation_id
from schemas import CostAnalysis, PRAnalysis, DeploymentStatus

app = FastAPI(title="MCP Strands Broker Service")

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

class BrokerRequest(BaseModel):
    ask_text: str
    account_id: str = "500330120558"
    region: str = "us-east-1"
    shim_url: str = "http://internal-mcp-internal-alb-2059913293.us-east-1.elb.amazonaws.com"
    metadata: Dict[str, Any] = {}

@app.get("/health")
async def health_check():
    return {"status": "OK", "service": "MCP Strands Broker"}

@app.post("/ask")
async def ask_endpoint(request: BrokerRequest, req: Request):
    """User tier endpoint with restricted tools"""
    # Store metadata and prompt for correlation ID
    req.state.metadata = request.metadata
    req.state.prompt = request.ask_text
    
    correlation_id = req.state.correlation_id
    print(f"🔍 USER PROMPT: {request.ask_text} | Correlation: {correlation_id}")
    start_time = time.time()
    
    try:
        # Build request context
        ctx = build_request_context(request.dict(), tier="user")
        ctx["prompt"] = request.ask_text
        ctx["correlation_id"] = correlation_id
        
        # Check intent guards
        guard_result = check_intent_guards(ctx)
        if guard_result:
            return {
                "answer": f"Request blocked: {guard_result['message']}",
                "debug": {
                    "tier": "user",
                    "correlation_id": correlation_id,
                    "guard_triggered": guard_result["error_type"],
                    "total_ms": int((time.time() - start_time) * 1000)
                }
            }
        
        # Build and execute user agent with structured output
        agent = build_user_agent(ctx)
        prompt_lower = request.ask_text.lower()
        
        # Apply structured output based on intent
        if any(word in prompt_lower for word in ["cost", "price", "pricing", "estimate"]):
            try:
                answer = agent(request.ask_text, output_type=CostAnalysis)
            except:
                answer = agent(request.ask_text)
        else:
            answer = agent(request.ask_text)
        
        return {
            "answer": answer,
            "debug": {
                "tier": "user",
                "correlation_id": correlation_id,
                "tools_advertised_count": len(USER_ALLOWED_TOOL_NAMES),
                "total_ms": int((time.time() - start_time) * 1000)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin") 
async def admin_endpoint(request: BrokerRequest, req: Request):
    """Admin tier endpoint with full tool access"""
    # Store metadata and prompt for correlation ID
    req.state.metadata = request.metadata
    req.state.prompt = request.ask_text
    
    correlation_id = req.state.correlation_id
    print(f"🔍 ADMIN PROMPT: {request.ask_text} | Correlation: {correlation_id}")
    start_time = time.time()
    
    try:
        # Build request context
        ctx = build_request_context(request.dict(), tier="admin")
        ctx["prompt"] = request.ask_text
        ctx["correlation_id"] = correlation_id
        
        # Admin tier skips most guards (has full access)
        # But still check for missing critical params
        guard_result = check_intent_guards(ctx)
        if guard_result and guard_result.get("error_type") == "MISSING_PARAMS":
            return {
                "answer": f"Missing information: {guard_result['message']}",
                "debug": {
                    "tier": "admin",
                    "correlation_id": correlation_id,
                    "guard_triggered": guard_result["error_type"], 
                    "total_ms": int((time.time() - start_time) * 1000)
                }
            }
        
        # Build and execute admin agent with structured output
        agent = build_admin_agent(ctx)
        prompt_lower = request.ask_text.lower()
        
        # Apply structured output based on intent
        if any(word in prompt_lower for word in ["cost", "price", "pricing", "estimate"]):
            try:
                answer = agent(request.ask_text, output_type=CostAnalysis)
            except Exception as e:
                print(f"Structured output failed: {e}")
                answer = agent(request.ask_text)
        elif any(word in prompt_lower for word in ["pull request", "pr", "security"]):
            try:
                answer = agent(request.ask_text, output_type=PRAnalysis)
            except Exception as e:
                print(f"Structured output failed: {e}")
                answer = agent(request.ask_text)
        else:
            answer = agent(request.ask_text)
        
        return {
            "answer": answer.content if hasattr(answer, 'content') else answer,
            "structured_data": answer.structured_output if hasattr(answer, 'structured_output') else None,
            "debug": {
                "tier": "admin",
                "correlation_id": correlation_id,
                "tools_advertised_count": len(ALL_ADMIN_TOOLS),
                "total_ms": int((time.time() - start_time) * 1000)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tools")
async def list_tools():
    """Debug endpoint to list available tools by tier"""
    from agents.tool_policy import get_tool_counts_by_tier
    
    counts = get_tool_counts_by_tier()
    
    return {
        "user_tools": list(USER_ALLOWED_TOOL_NAMES),
        "admin_tools": list(ALL_ADMIN_TOOLS),
        "counts": counts
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
