"""
Observability hooks for Strands broker
"""
import time
import logging
from typing import Dict, Any, Optional
from opentelemetry import trace as trace_api

logger = logging.getLogger(__name__)
tracer = trace_api.get_tracer(__name__)

def log_tool_execution(tool_name: str, outcome: str, latency_ms: int, tier: str, metadata: Optional[Dict] = None):
    """Log tool execution with redacted args"""
    
    # Redact sensitive metadata
    safe_metadata = {}
    if metadata:
        safe_metadata = {
            "pr_number": metadata.get("pr_number"),
            "repository": metadata.get("repository", "").split("/")[-1] if metadata.get("repository") else None,
            "tier": tier
        }
    
    logger.info(
        f"TOOL_EXEC tool={tool_name} outcome={outcome} latency_ms={latency_ms} tier={tier} metadata={safe_metadata}"
    )
    
    # OpenTelemetry span
    with tracer.start_as_current_span(f"tool.{tool_name}") as span:
        span.set_attribute("tool.name", tool_name)
        span.set_attribute("tool.outcome", outcome)
        span.set_attribute("tool.latency_ms", latency_ms)
        span.set_attribute("tool.tier", tier)
        if safe_metadata.get("pr_number"):
            span.set_attribute("pr.number", safe_metadata["pr_number"])

def measure_execution(tool_name: str, tier: str, metadata: Dict):
    """Context manager to measure and log tool execution"""
    class ExecutionTimer:
        def __init__(self):
            self.start_time = None
            
        def __enter__(self):
            self.start_time = time.time()
            return self
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            latency_ms = int((time.time() - self.start_time) * 1000)
            
            if exc_type:
                outcome = "ERROR"
            else:
                outcome = "SUCCESS"
                
            log_tool_execution(tool_name, outcome, latency_ms, tier, metadata)
    
    return ExecutionTimer()
