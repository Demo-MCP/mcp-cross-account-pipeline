"""
Correlation ID generation and propagation for end-to-end request tracing
"""
import uuid
import hashlib
from typing import Dict, Any, Optional


def get_or_create_correlation_id(
    headers: Dict[str, str], 
    metadata: Dict[str, Any], 
    prompt: str
) -> str:
    """
    Get existing correlation ID or create new one with GitHub workflow context
    
    Priority:
    1. Existing x-correlation-id header
    2. GitHub workflow format: org/repo__pr-N__run-ID__job-NAME
    3. Fallback: UUID with prompt hash
    """
    # Check if client provided correlation ID
    correlation_id = headers.get('x-correlation-id')
    if correlation_id:
        return correlation_id
    
    # Build from GitHub workflow metadata
    repo = metadata.get('repository', 'unknown')
    run_id = metadata.get('run_id', 'unknown')
    pr_number = metadata.get('pr_number')
    actor = metadata.get('actor', 'unknown')
    
    # GitHub workflow format
    if pr_number:
        correlation_id = f"{repo}__pr-{pr_number}__run-{run_id}__actor-{actor}"
    else:
        correlation_id = f"{repo}__run-{run_id}__actor-{actor}"
    
    # Add prompt fingerprint for duplicate detection
    prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]
    correlation_id += f"__hash-{prompt_hash}"
    
    # Fallback to UUID if metadata missing
    if 'unknown' in correlation_id:
        correlation_id = f"broker__{uuid.uuid4().hex[:12]}"
    
    return correlation_id


def add_correlation_headers(headers: Dict[str, str], correlation_id: str) -> Dict[str, str]:
    """Add correlation ID to outbound request headers"""
    headers = headers.copy()
    headers['x-correlation-id'] = correlation_id
    return headers


def extract_correlation_from_request(request) -> Optional[str]:
    """Extract correlation ID from FastAPI request"""
    return request.headers.get('x-correlation-id')
