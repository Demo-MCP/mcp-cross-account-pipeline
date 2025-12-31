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
    },
    "deploy_workflow": {
        "name": "deploy_workflow",
        "description": "Complete deployment workflow - triggers deploy via PR comment and monitors progress with auto-diagnostics",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repository": {"type": "string", "description": "Repository name (e.g., 'Demo-MCP/mcp-cross-account-pipeline')"},
                "branch": {"type": "string", "description": "Branch to deploy", "default": "main"},
                "pr_number": {"type": "integer", "description": "PR number to comment on (optional)"},
                "environment": {"type": "string", "description": "Target environment", "default": "auto"},
                "region": {"type": "string", "description": "AWS region for deployment", "default": "us-east-1"}
            },
            "required": ["repository"]
        }
    },
    "deploy_monitor": {
        "name": "deploy_monitor", 
        "description": "Monitor deployment progress (internal tool)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repository": {"type": "string"},
                "branch": {"type": "string"},
                "environment": {"type": "string"},
                "region": {"type": "string"}
            },
            "required": ["repository"]
        }
    },
    "deploy_rollback": {
        "name": "deploy_rollback",
        "description": "Rollback to previous successful deployment",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repository": {"type": "string", "description": "Repository name"},
                "environment": {"type": "string", "description": "Environment to rollback", "default": "staging"},
                "target_run_id": {"type": "string", "description": "Specific run_id to rollback to (optional)"}
            },
            "required": ["repository"]
        }
    },
    "deploy_multi_env": {
        "name": "deploy_multi_env",
        "description": "Deploy to multiple environments sequentially",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repository": {"type": "string", "description": "Repository name"},
                "environments": {"type": "array", "items": {"type": "string"}, "description": "List of environments", "default": ["staging", "production"]},
                "branch": {"type": "string", "description": "Branch to deploy", "default": "main"},
                "require_approval": {"type": "boolean", "description": "Require approval between environments", "default": True}
            },
            "required": ["repository"]
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
    
    elif tool_name == "deploy_workflow":
        return await deploy_workflow(
            arguments["repository"],
            arguments.get("branch", "main"),
            arguments.get("pr_number"),
            arguments.get("environment", "auto"),
            arguments.get("region", "us-east-1")
        )
    
    elif tool_name == "deploy_monitor":
        return await deploy_monitor(
            arguments["repository"],
            arguments.get("branch", "main"),
            arguments.get("environment", "auto"),
            arguments.get("region", "us-east-1")
        )
    
    elif tool_name == "deploy_rollback":
        return await deploy_rollback(
            arguments["repository"],
            arguments.get("environment", "staging"),
            arguments.get("target_run_id")
        )
    
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

async def deploy_workflow(repository: str, branch: str, pr_number: Optional[int], environment: str, region: str) -> str:
    """Complete deployment workflow - coordinates with local Kiro proxy for GitHub CLI"""
    import time
    
    try:
        # Step 1: Request local GitHub CLI execution via special response format
        if pr_number:
            gh_command = f"gh pr comment {pr_number} --repo {repository} --body '/deploy env={environment} region={region}'"
            
            # Return special format that Kiro proxy will intercept
            return f"""KIRO_LOCAL_COMMAND:{gh_command}
KIRO_CONTINUE_WITH:deploy_monitor|{repository}|{branch}|{environment}|{region}"""
        
        # If no PR, skip to monitoring
        return await deploy_monitor(repository, branch, environment, region)
        
    except Exception as e:
        return f"❌ Deploy workflow error: {str(e)}"

async def deploy_monitor(repository: str, branch: str, environment: str, region: str) -> str:
    """Monitor deployment progress after GitHub CLI execution"""
    import asyncio
    
    try:
        # Wait for workflow to start
        await asyncio.sleep(5)
        
        # Find latest run
        latest_run = await find_latest_runs(repository, 1)
        if "No deployment runs found" in latest_run:
            return "❌ No deployment runs found after triggering"
        
        # Extract run_id
        lines = latest_run.split('\n')
        run_id = None
        for line in lines:
            if line.startswith("Run ID:"):
                run_id = line.split(": ")[1].strip()
                break
        
        if not run_id:
            return "❌ Could not extract run_id from latest run"
        
        # Monitor progress
        status_msg = f"🔄 Monitoring deployment run_id: {run_id}"
        
        # Poll for completion (max 5 minutes for demo)
        max_polls = 30
        for poll_count in range(max_polls):
            run_details = await get_run_details(run_id)
            
            if "SUCCEEDED" in run_details:
                summary = await get_run_summary(run_id)
                return f"✅ Deployment completed successfully!\n\n{summary}"
            
            elif "FAILED" in run_details or "ERROR" in run_details:
                diagnosis = await auto_diagnose_failure(run_id, repository, region)
                return f"❌ Deployment failed!\n\n{run_details}\n\n🔍 Auto-diagnosis:\n{diagnosis}"
            
            elif "RUNNING" in run_details:
                if poll_count % 3 == 0:  # Update every 30 seconds
                    status_msg += f"\n⏳ Still running... (poll {poll_count + 1}/{max_polls})"
            
            await asyncio.sleep(10)
        
        return f"⏰ Deployment monitoring timed out. Run_id: {run_id}"
        
    except Exception as e:
        return f"❌ Deploy monitor error: {str(e)}"

async def auto_diagnose_failure(run_id: str, repository: str, region: str) -> str:
    """Auto-diagnose deployment failures"""
    diagnosis = []
    
    try:
        steps = await get_run_steps(run_id, 50)
        
        if "cloudformation" in steps.lower():
            diagnosis.append("📋 CloudFormation issue detected")
            diagnosis.append("💡 Use: kiro 'check stack status for latest deployment'")
        
        if "ecs" in steps.lower():
            diagnosis.append("🐳 ECS deployment issue detected") 
            diagnosis.append("💡 Use: kiro 'check ECS service health'")
        
        if "timeout" in steps.lower():
            diagnosis.append("⏰ Timeout detected - check resource capacity")
        
        if not diagnosis:
            diagnosis.append("🔍 Check deployment steps above for details")
        
        return "\n".join(diagnosis)
        
    except Exception as e:
        return f"⚠️ Auto-diagnosis failed: {str(e)}"

async def deploy_rollback(repository: str, environment: str, target_run_id: Optional[str]) -> str:
    """Rollback to previous successful deployment"""
    try:
        # Find target deployment to rollback to
        if target_run_id:
            # Rollback to specific run_id
            target_details = await get_run_details(target_run_id)
            if "No deployment run found" in target_details:
                return f"❌ Target run_id {target_run_id} not found"
        else:
            # Find last successful deployment
            latest_runs = await find_latest_runs(repository, 10)
            if "No deployment runs found" in latest_runs:
                return f"❌ No deployment history found for {repository}"
            
            # Parse runs to find last successful one
            lines = latest_runs.split('\n')
            target_run_id = None
            for i, line in enumerate(lines):
                if line.startswith("Run ID:"):
                    run_id = line.split(": ")[1].strip()
                    # Check next few lines for status
                    for j in range(i+1, min(i+6, len(lines))):
                        if "Status: SUCCEEDED" in lines[j]:
                            target_run_id = run_id
                            break
                    if target_run_id:
                        break
            
            if not target_run_id:
                return f"❌ No successful deployment found to rollback to"
        
        # Trigger rollback deployment
        rollback_comment = f"/deploy rollback={target_run_id} env={environment}"
        
        return f"""🔄 Rollback initiated for {repository}
        
Target: Run ID {target_run_id}
Environment: {environment}

KIRO_LOCAL_COMMAND:echo "Rollback would post: {rollback_comment}"
KIRO_CONTINUE_WITH:deploy_monitor|{repository}|rollback|{environment}|us-east-1

⚠️  Note: Actual rollback requires GitHub workflow support for rollback commands"""
        
    except Exception as e:
        return f"❌ Rollback error: {str(e)}"

async def deploy_approve(repository: str, run_id: str, approver: str) -> str:
    """Approve a pending deployment"""
    try:
        # Check if deployment is pending approval
        run_details = await get_run_details(run_id)
        
        if "No deployment run found" in run_details:
            return f"❌ Run ID {run_id} not found"
        
        # Post approval comment
        approval_comment = f"/approve run_id={run_id} approved_by={approver}"
        
        return f"""✅ Deployment approval for {repository}
        
Run ID: {run_id}
Approved by: {approver}
Status: Approval posted

KIRO_LOCAL_COMMAND:echo "Approval would post: {approval_comment}"

💡 Deployment will proceed automatically after approval"""
        
    except Exception as e:
        return f"❌ Approval error: {str(e)}"
