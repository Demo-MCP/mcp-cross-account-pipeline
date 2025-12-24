#!/usr/bin/env python3
"""
Query metrics from RDS to verify workflow data is being written.
Usage: python3 tools/query_metrics.py
"""

import os
import psycopg2
from datetime import datetime

# Database connection parameters
DB_HOST = "mcp-metrics-db.c8n6ce6mmzmc.us-east-1.rds.amazonaws.com"
DB_PORT = 5432
DB_NAME = "mcp_metrics"
DB_USER = "metrics_user"
DB_PASSWORD = os.environ.get("DB_PASSWORD", "MySecurePassword123")

def query_recent_jobs():
    """Query recent job metrics"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        
        with conn.cursor() as cur:
            print("=== Recent Job Metrics ===")
            cur.execute("""
                SELECT run_id, repository, job_status, job_start_time, job_end_time, workflow_name
                FROM job_metrics 
                ORDER BY job_start_time DESC 
                LIMIT 10
            """)
            
            rows = cur.fetchall()
            if not rows:
                print("No job metrics found")
                return
                
            for row in rows:
                run_id, repo, status, start_time, end_time, workflow = row
                print(f"Run ID: {run_id}")
                print(f"  Repository: {repo}")
                print(f"  Workflow: {workflow}")
                print(f"  Status: {status}")
                print(f"  Start: {start_time}")
                print(f"  End: {end_time}")
                print()
                
    except Exception as e:
        print(f"Error querying database: {e}")
    finally:
        if conn:
            conn.close()

def query_job_steps(run_id):
    """Query steps for a specific job"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        
        with conn.cursor() as cur:
            print(f"=== Steps for Run ID: {run_id} ===")
            cur.execute("""
                SELECT step_index, step_name, step_status, step_start_time, step_end_time
                FROM job_step_metrics 
                WHERE run_id = %s 
                ORDER BY step_index
            """, (run_id,))
            
            rows = cur.fetchall()
            if not rows:
                print("No step metrics found for this run")
                return
                
            for row in rows:
                index, name, status, start_time, end_time = row
                print(f"Step {index}: {name}")
                print(f"  Status: {status}")
                print(f"  Start: {start_time}")
                print(f"  End: {end_time}")
                print()
                
    except Exception as e:
        print(f"Error querying database: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    query_recent_jobs()
