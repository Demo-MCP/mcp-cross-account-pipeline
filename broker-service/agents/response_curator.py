import json
import re
from typing import Dict, Any

def curate_response(full_response: Dict[str, Any]) -> str:
    """Extract and format the final response for PR comments."""
    
    # Get the main message content
    message = full_response.get("message", {})
    content = message.get("content", [])
    
    # Extract text content, filtering thinking blocks
    response_text = ""
    for item in content:
        text = item.get("text", "")
        # Remove thinking blocks (including multiline)
        text = re.sub(r'<thinking>.*?</thinking>\s*', '', text, flags=re.DOTALL)
        response_text += text
    
    # Get metrics summary
    metrics = full_response.get("metrics", {})
    cycle_count = metrics.get("cycle_count", 0)
    tool_metrics = metrics.get("tool_metrics", {})
    
    # Build summary
    summary_parts = []
    if cycle_count > 0:
        summary_parts.append(f"Completed in {cycle_count} cycles")
    
    if tool_metrics:
        tool_calls = sum(m.get("call_count", 0) for m in tool_metrics.values())
        if tool_calls > 0:
            summary_parts.append(f"{tool_calls} tool calls")
    
    # Format final response
    result = response_text.strip()
    if summary_parts:
        result += f"\n\n*{', '.join(summary_parts)}*"
    
    return result

def curate_response_from_file(file_path: str) -> str:
    """Load and curate response from file."""
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    # Handle wrapped response format
    if "answer" in data:
        data = data["answer"]
    
    return curate_response(data)
