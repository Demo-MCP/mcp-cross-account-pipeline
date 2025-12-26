#!/usr/bin/env python3
"""
PR Context MCP Server
Provides secure GitHub PR analysis without exposing tokens to broker
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging

from github_client import GitHubClient
from analyzer import PRAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="PR Context MCP Server")

# Initialize clients
github_client = GitHubClient()
pr_analyzer = PRAnalyzer()

class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: int
    method: str
    params: Optional[Dict[str, Any]] = None

class MCPResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: int
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

@app.get("/health")
async def health_check():
    """Health check endpoint for ALB"""
    return {"status": "OK", "service": "PR Context MCP"}

@app.post("/pr")
async def mcp_endpoint(request: MCPRequest):
    """Main MCP JSON-RPC endpoint"""
    try:
        logger.info(f"MCP request: {request.method}")
        
        if request.method == "tools/list":
            return MCPResponse(
                id=request.id,
                result={
                    "tools": [
                        {
                            "name": "pr_get_diff",
                            "description": "Get PR diff and changed files from GitHub",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "repo": {"type": "string", "description": "Repository in format org/repo"},
                                    "pr_number": {"type": "integer", "description": "Pull request number"},
                                    "actor": {"type": "string", "description": "GitHub username"},
                                    "run_id": {"type": "string", "description": "GitHub Actions run ID"},
                                    "options": {
                                        "type": "object",
                                        "properties": {
                                            "max_diff_bytes": {"type": "integer", "default": 1500000},
                                            "max_files": {"type": "integer", "default": 200}
                                        }
                                    }
                                },
                                "required": ["repo", "pr_number", "actor", "run_id"]
                            }
                        },
                        {
                            "name": "pr_summarize",
                            "description": "Analyze PR diff for security and operational risks",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "repo": {"type": "string", "description": "Repository in format org/repo"},
                                    "pr_number": {"type": "integer", "description": "Pull request number"},
                                    "actor": {"type": "string", "description": "GitHub username"},
                                    "run_id": {"type": "string", "description": "GitHub Actions run ID"},
                                    "diff": {"type": "string", "description": "Unified diff text"},
                                    "changed_files": {"type": "array", "description": "List of changed files"},
                                    "options": {
                                        "type": "object",
                                        "properties": {
                                            "include_security": {"type": "boolean", "default": True},
                                            "include_operational_risk": {"type": "boolean", "default": True},
                                            "max_findings": {"type": "integer", "default": 20}
                                        }
                                    }
                                },
                                "required": ["repo", "pr_number", "actor", "run_id", "diff", "changed_files"]
                            }
                        }
                    ]
                }
            )
        
        elif request.method == "tools/call":
            tool_name = request.params.get("name")
            arguments = request.params.get("arguments", {})
            
            if tool_name == "pr_get_diff":
                result = await handle_pr_get_diff(arguments)
                return MCPResponse(id=request.id, result=result)
            
            elif tool_name == "pr_summarize":
                result = await handle_pr_summarize(arguments)
                return MCPResponse(id=request.id, result=result)
            
            else:
                return MCPResponse(
                    id=request.id,
                    error={"code": -32601, "message": f"Unknown tool: {tool_name}"}
                )
        
        else:
            return MCPResponse(
                id=request.id,
                error={"code": -32601, "message": f"Unknown method: {request.method}"}
            )
    
    except Exception as e:
        logger.error(f"Error processing MCP request: {e}")
        return MCPResponse(
            id=request.id,
            error={"code": -32603, "message": f"Internal error: {str(e)}"}
        )

async def handle_pr_get_diff(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle pr_get_diff tool call"""
    repo = args.get("repo")
    pr_number = args.get("pr_number")
    actor = args.get("actor")
    run_id = args.get("run_id")
    options = args.get("options", {})
    
    # Validate required parameters
    if not all([repo, pr_number, actor, run_id]):
        raise ValueError("Missing required parameters: repo, pr_number, actor, run_id")
    
    # Security: Check repository allowlist
    if not github_client.is_repo_allowed(repo):
        raise ValueError(f"Repository {repo} not in allowlist")
    
    # Get PR diff from GitHub
    pr_data = await github_client.get_pr_diff(
        repo=repo,
        pr_number=pr_number,
        max_diff_bytes=options.get("max_diff_bytes", 1500000),
        max_files=options.get("max_files", 200)
    )
    
    # Add metadata
    pr_data["metadata"] = {
        "actor": actor,
        "run_id": run_id,
        "fetched_at": datetime.utcnow().isoformat() + "Z"
    }
    
    return pr_data

async def handle_pr_summarize(args: Dict[str, Any]) -> Dict[str, Any]:
    """Handle pr_summarize tool call"""
    repo = args.get("repo")
    pr_number = args.get("pr_number")
    actor = args.get("actor")
    run_id = args.get("run_id")
    diff = args.get("diff")
    changed_files = args.get("changed_files", [])
    options = args.get("options", {})
    
    # Validate required parameters
    if not all([repo, pr_number, actor, run_id, diff]):
        raise ValueError("Missing required parameters: repo, pr_number, actor, run_id, diff")
    
    # Security: Check repository allowlist
    if not github_client.is_repo_allowed(repo):
        raise ValueError(f"Repository {repo} not in allowlist")
    
    # Analyze PR diff
    analysis = await pr_analyzer.analyze_pr(
        repo=repo,
        pr_number=pr_number,
        diff=diff,
        changed_files=changed_files,
        include_security=options.get("include_security", True),
        include_operational_risk=options.get("include_operational_risk", True),
        max_findings=options.get("max_findings", 20)
    )
    
    return analysis

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
