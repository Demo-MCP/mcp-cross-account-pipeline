"""
Strands-based broker service with tier-based security
"""
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

from agents.param_resolution import build_request_context
from agents.guards import check_intent_guards
from agents.agents import build_user_agent, build_admin_agent
from agents.tool_policy import USER_ALLOWED_TOOL_NAMES, ALL_ADMIN_TOOLS
from schemas import CostAnalysis, PRAnalysis, DeploymentStatus

app = FastAPI(title="MCP Strands Broker Service")

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
async def ask_endpoint(request: BrokerRequest):
    """User tier endpoint with restricted tools"""
    print(f"🔍 USER PROMPT: {request.ask_text}")
    start_time = time.time()
    
    try:
        # Build request context
        ctx = build_request_context(request.dict(), tier="user")
        ctx["prompt"] = request.ask_text  # Add prompt for structured output detection
        
        # Check intent guards
        guard_result = check_intent_guards(ctx)
        if guard_result:
            return {
                "answer": f"Request blocked: {guard_result['message']}",
                "debug": {
                    "tier": "user",
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
                "tools_advertised_count": len(USER_ALLOWED_TOOL_NAMES),
                "total_ms": int((time.time() - start_time) * 1000)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin") 
async def admin_endpoint(request: BrokerRequest):
    """Admin tier endpoint with full tool access"""
    print(f"🔍 ADMIN PROMPT: {request.ask_text}")
    start_time = time.time()
    
    try:
        # Build request context
        ctx = build_request_context(request.dict(), tier="admin")
        ctx["prompt"] = request.ask_text  # Add prompt for structured output detection
        
        # Admin tier skips most guards (has full access)
        # But still check for missing critical params
        guard_result = check_intent_guards(ctx)
        if guard_result and guard_result.get("error_type") == "MISSING_PARAMS":
            return {
                "answer": f"Missing information: {guard_result['message']}",
                "debug": {
                    "tier": "admin",
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
                "tools_advertised_count": len(ALL_ADMIN_TOOLS),
                "total_ms": int((time.time() - start_time) * 1000)
            }
        }
        
        return {
            "answer": answer,
            "debug": {
                "tier": "admin",
                "tools_advertised_count": len(ALL_ADMIN_TOOLS),
                "total_ms": int((time.time() - start_time) * 1000)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tools")
async def list_tools():
    """Debug endpoint to list available tools"""
    from agents.tool_policy import USER_ALLOWED_TOOL_NAMES
    
    all_tools = list(USER_ALLOWED_TOOL_NAMES) + ["pr_get_diff", "pr_summarize", "pricingcalc_estimate_from_stack"]
    
    return {
        "user_tools": list(USER_ALLOWED_TOOL_NAMES),
        "admin_tools": all_tools,
        "user_count": len(USER_ALLOWED_TOOL_NAMES),
        "admin_count": len(all_tools)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
