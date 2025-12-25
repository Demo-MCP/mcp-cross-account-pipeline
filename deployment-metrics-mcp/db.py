import os
import psycopg2
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

# Database configuration from environment variables
DB_HOST = os.environ.get('DB_HOST', 'mcp-metrics-db.c8n6ce6mmzmc.us-east-1.rds.amazonaws.com')
DB_PORT = int(os.environ.get('DB_PORT', '5432'))
DB_NAME = os.environ.get('DB_NAME', 'mcp_metrics')
DB_USER = os.environ.get('DB_USER', 'metrics_user')
DB_PASSWORD = os.environ.get('DB_PASSWORD')  # Required from Secrets Manager

if not DB_PASSWORD:
    raise ValueError("DB_PASSWORD environment variable is required")

@contextmanager
def get_db_connection():
    """Get database connection with context manager"""
    conn = None
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            connect_timeout=10
        )
        yield conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise
    finally:
        if conn:
            conn.close()
