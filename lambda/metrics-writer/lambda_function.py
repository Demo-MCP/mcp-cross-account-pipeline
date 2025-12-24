import json
import os
import psycopg2
from datetime import datetime
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_db_connection():
    return psycopg2.connect(
        host=os.environ['DB_HOST'],
        port=os.environ.get('DB_PORT', '5432'),
        database=os.environ['DB_NAME'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD']
    )

def lambda_handler(event, context):
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Handle direct Lambda invoke (from GitHub workflow)
        if 'action' in event:
            action = event['action']
            logger.info(f"Processing direct invoke action: {action}")
            
            conn = get_db_connection()
            cur = conn.cursor()
            
            if action == 'job_start':
                return handle_job_start(cur, conn, event)
            elif action == 'job_end':
                return handle_job_end(cur, conn, event)
            elif action == 'job_step':
                return handle_job_step(cur, conn, event)
            else:
                logger.error(f"Unknown action: {action}")
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': f'Unknown action: {action}'})
                }
        
        # Handle HTTP API Gateway events (from Function URL)
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event
        
        path = event.get('path', event.get('rawPath', ''))
        method = event.get('httpMethod', event.get('requestContext', {}).get('http', {}).get('method', 'POST'))
        
        logger.info(f"Processing {method} {path}")
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        if path == '/job/start':
            return handle_job_start(cur, conn, body)
        elif path == '/job/end':
            return handle_job_end(cur, conn, body)
        elif path == '/job/step':
            return handle_job_step(cur, conn, body)
        else:
            logger.error(f"Unknown path: {path}")
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Not found'})
            }
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

def handle_job_start(cur, conn, body):
    logger.info(f"Processing job_start for run_id: {body.get('run_id')}, repository: {body.get('repository')}")
    
    # UPSERT job_metrics by run_id - only use fields we actually have
    sql = """
    INSERT INTO job_metrics (
        run_id, repository, organization, branch, 
        runner_name, workflow_name, job_name, job_status, job_start_time
    ) VALUES (
        %(run_id)s, %(repository)s, %(organization)s, %(branch)s,
        %(runner_name)s, %(workflow_name)s, %(job_name)s, %(job_status)s, %(job_start_time)s
    )
    ON CONFLICT (run_id) DO UPDATE SET
        job_status = EXCLUDED.job_status,
        job_start_time = EXCLUDED.job_start_time
    """
    
    logger.info(f"Executing job_start SQL for run_id: {body.get('run_id')}")
    cur.execute(sql, body)
    conn.commit()
    logger.info(f"Successfully recorded job_start for run_id: {body.get('run_id')}")
    
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Job start recorded', 'run_id': body.get('run_id')})
    }

def handle_job_end(cur, conn, body):
    logger.info(f"Processing job_end for run_id: {body.get('run_id')}, status: {body.get('job_status')}")
    
    # UPDATE job_metrics set end/status/error/duration where run_id
    sql = """
    UPDATE job_metrics SET
        job_end_time = %(job_end_time)s,
        job_status = %(job_status)s,
        job_error_message = %(job_error_message)s,
        job_failure_category = %(job_failure_category)s,
        job_duration_seconds = %(job_duration_seconds)s
    WHERE run_id = %(run_id)s
    """
    
    logger.info(f"Executing job_end SQL for run_id: {body.get('run_id')}")
    cur.execute(sql, body)
    rows_affected = cur.rowcount
    conn.commit()
    logger.info(f"Successfully updated job_end for run_id: {body.get('run_id')}, rows affected: {rows_affected}")
    
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Job end recorded', 'run_id': body.get('run_id')})
    }

def handle_job_step(cur, conn, body):
    # UPSERT job_step_metrics by step_id
    sql = """
    INSERT INTO job_step_metrics (
        step_id, run_id, step_name, step_index, step_status,
        step_start_time, step_end_time, step_duration_seconds
    ) VALUES (
        %(step_id)s, %(run_id)s, %(step_name)s, %(step_index)s, %(step_status)s,
        %(step_start_time)s, %(step_end_time)s, %(step_duration_seconds)s
    )
    ON CONFLICT (step_id) DO UPDATE SET
        step_status = EXCLUDED.step_status,
        step_end_time = EXCLUDED.step_end_time,
        step_duration_seconds = EXCLUDED.step_duration_seconds
    """
    
    cur.execute(sql, body)
    conn.commit()
    
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Job step recorded', 'step_id': body.get('step_id')})
    }
