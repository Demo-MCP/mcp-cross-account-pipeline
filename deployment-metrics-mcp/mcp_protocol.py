from typing import Any, Dict, List, Optional
import logging
from db import get_db_connection
from datetime import datetime

logger = logging.getLogger(__name__)

# MCP Tools Registry
TOOLS = {
    "deploy_get_run": {
        "name": "deploy_get_run",
        "description": "Get deployment run details by run_id",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string", "description": "GitHub run ID"}
            },
            "required": ["run_id"]
        }
    },
    "deploy_get_steps": {
        "name": "deploy_get_steps",
        "description": "Get deployment steps for a run_id",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string", "description": "GitHub run ID"},
                "limit": {"type": "integer", "description": "Max steps to return", "default": 200}
            },
            "required": ["run_id"]
        }
    },
    "deploy_find_latest": {
        "name": "deploy_find_latest",
        "description": "Find latest deployment runs",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repository": {"type": "string", "description": "Repository name"},
                "limit": {"type": "integer", "description": "Max runs to return", "default": 10}
            },
            "required": ["repository"]
        }
    },
    "deploy_find_active": {
        "name": "deploy_find_active",
        "description": "Find active/running deployment runs",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repository": {"type": "string", "description": "Repository name", "default": ""},
                "limit": {"type": "integer", "description": "Max runs to return", "default": 10}
            }
        }
    },
    "deploy_get_summary": {
        "name": "deploy_get_summary",
        "description": "Get deployment summary with run and step details",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string", "description": "GitHub run ID"}
            },
            "required": ["run_id"]
        }
    }
}

async def handle_mcp_request(method: str, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Handle MCP JSON-RPC requests"""
    
    if method == "initialize":
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "deployment-metrics-mcp",
                "version": "1.0.0"
            }
        }
    
    elif method == "tools/list":
        return {
            "tools": list(TOOLS.values())
        }
    
    elif method == "tools/call":
        if not params or "name" not in params:
            raise ValueError("Missing tool name in params")
        
        tool_name = params["name"]
        arguments = params.get("arguments", {})
        
        if tool_name not in TOOLS:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        # Call the appropriate tool function
        result = await call_tool(tool_name, arguments)
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": result
                }
            ]
        }
    
    else:
        raise ValueError(f"Unknown method: {method}")

async def call_tool(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Execute tool and return formatted result"""
    
    if tool_name == "deploy_get_run":
        return await get_run_details(arguments["run_id"])
    
    elif tool_name == "deploy_get_steps":
        return await get_run_steps(arguments["run_id"], arguments.get("limit", 200))
    
    elif tool_name == "deploy_find_latest":
        return await find_latest_runs(arguments["repository"], arguments.get("limit", 10))
    
    elif tool_name == "deploy_find_active":
        return await find_active_runs(arguments.get("repository", ""), arguments.get("limit", 10))
    
    elif tool_name == "deploy_get_summary":
        return await get_run_summary(arguments["run_id"])
    
    else:
        raise ValueError(f"Tool not implemented: {tool_name}")

async def get_run_details(run_id: str) -> str:
    """Get deployment run details"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT run_id, repository, organization, branch, workflow_name, 
                       job_name, runner_name, job_status, job_start_time, 
                       job_end_time, job_duration_seconds, job_error_message
                FROM job_metrics 
                WHERE run_id = %s
            """, (run_id,))
            
            row = cur.fetchone()
            if not row:
                return f"No deployment run found with ID: {run_id}"
            
            return f"""Deployment Run Details:
Run ID: {row[0]}
Repository: {row[1]}
Organization: {row[2]}
Branch: {row[3]}
Workflow: {row[4]}
Job: {row[5]}
Runner: {row[6]}
Status: {row[7]}
Start Time: {row[8]}
End Time: {row[9]}
Duration: {row[10]} seconds
Error: {row[11] or 'None'}"""

async def get_run_steps(run_id: str, limit: int) -> str:
    """Get deployment steps for a run"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT step_name, step_index, step_status, 
                       step_start_time, step_end_time, step_duration_seconds
                FROM job_step_metrics 
                WHERE run_id = %s 
                ORDER BY step_index
                LIMIT %s
            """, (run_id, limit))
            
            rows = cur.fetchall()
            if not rows:
                return f"No steps found for run ID: {run_id}"
            
            result = f"Deployment Steps for Run {run_id}:\n"
            for row in rows:
                result += f"\nStep {row[1]}: {row[0]}"
                result += f"\n  Status: {row[2]}"
                result += f"\n  Start: {row[3]}"
                result += f"\n  End: {row[4]}"
                result += f"\n  Duration: {row[5]} seconds"
            
            return result

async def find_latest_runs(repository: str, limit: int) -> str:
    """Find latest deployment runs"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT run_id, workflow_name, job_status, job_start_time, 
                       job_end_time, branch
                FROM job_metrics 
                WHERE repository = %s 
                ORDER BY job_start_time DESC 
                LIMIT %s
            """, (repository, limit))
            
            rows = cur.fetchall()
            if not rows:
                return f"No deployment runs found for repository: {repository}"
            
            result = f"Latest Deployment Runs for {repository}:\n"
            for row in rows:
                result += f"\nRun ID: {row[0]}"
                result += f"\n  Workflow: {row[1]}"
                result += f"\n  Status: {row[2]}"
                result += f"\n  Branch: {row[5]}"
                result += f"\n  Start: {row[3]}"
                result += f"\n  End: {row[4]}"
            
            return result

async def find_active_runs(repository: str, limit: int) -> str:
    """Find active/running deployment runs"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            where_clause = "WHERE job_status = 'RUNNING'"
            params = [limit]
            
            if repository:
                where_clause += " AND repository = %s"
                params = [repository, limit]
            
            cur.execute(f"""
                SELECT run_id, repository, workflow_name, job_start_time, runner_name
                FROM job_metrics 
                {where_clause}
                ORDER BY job_start_time DESC 
                LIMIT %s
            """, params)
            
            rows = cur.fetchall()
            if not rows:
                return "No active deployment runs found"
            
            result = "Active Deployment Runs:\n"
            for row in rows:
                result += f"\nRun ID: {row[0]}"
                result += f"\n  Repository: {row[1]}"
                result += f"\n  Workflow: {row[2]}"
                result += f"\n  Started: {row[3]}"
                result += f"\n  Runner: {row[4]}"
            
            return result

async def get_run_summary(run_id: str) -> str:
    """Get comprehensive deployment summary"""
    # Get run details
    run_details = await get_run_details(run_id)
    
    # Get step count
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*), 
                       COUNT(CASE WHEN step_status = 'SUCCEEDED' THEN 1 END) as succeeded,
                       COUNT(CASE WHEN step_status = 'FAILED' THEN 1 END) as failed,
                       COUNT(CASE WHEN step_status = 'RUNNING' THEN 1 END) as running
                FROM job_step_metrics 
                WHERE run_id = %s
            """, (run_id,))
            
            step_stats = cur.fetchone()
            
    if step_stats and step_stats[0] > 0:
        summary = f"{run_details}\n\nStep Summary:"
        summary += f"\n  Total Steps: {step_stats[0]}"
        summary += f"\n  Succeeded: {step_stats[1]}"
        summary += f"\n  Failed: {step_stats[2]}"
        summary += f"\n  Running: {step_stats[3]}"
        return summary
    else:
        return f"{run_details}\n\nNo steps recorded for this run."
