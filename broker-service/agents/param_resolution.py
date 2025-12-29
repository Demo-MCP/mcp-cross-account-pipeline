"""
Context-aware parameter resolution with alias handling
"""
import json
from typing import Dict, Any, Optional, List

def build_request_context(request_data: dict, tier: str) -> dict:
    """Build request context from inbound request"""
    return {
        "tier": tier,
        "prompt": request_data.get("ask_text", ""),
        "metadata": request_data.get("metadata", {}),
        "aws": {
            "account_id": request_data.get("account_id", "500330120558"),
            "region": request_data.get("region", "us-east-1"),
            "shim_url": request_data.get("shim_url", "http://internal-mcp-internal-alb-2059913293.us-east-1.elb.amazonaws.com")
        }
    }

# Parameter aliases for common field name mismatches
PARAM_ALIASES = {
    "repo": ["repository", "repo_name", "github_repo"],
    "account_id": ["aws_account", "account"],
    "stack_name": ["stack", "cfn_stack"],
    "cluster": ["cluster_name", "ecs_cluster"],
    "service": ["service_name", "ecs_service"]
}

def resolve_with_aliases(target_key: str, metadata: dict, user_params: dict = None) -> Any:
    """Check target key and all known aliases in metadata and user params"""
    # Ensure metadata is a dict
    if not isinstance(metadata, dict):
        metadata = {}
    
    # Ensure user_params is a dict
    if not isinstance(user_params, dict):
        user_params = {}
    
    # Check user params first (prioritize user input)
    if user_params:
        if target_key in user_params:
            return user_params[target_key]
        for alias in PARAM_ALIASES.get(target_key, []):
            if alias in user_params:
                return user_params[alias]
    
    # Fallback to metadata
    if target_key in metadata:
        return metadata[target_key]
    
    for alias in PARAM_ALIASES.get(target_key, []):
        if alias in metadata:
            return metadata[alias]
    return None

def extract_parameters_with_bedrock(prompt: str, required_params: Dict[str, str], metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """Extract parameters from user prompt using Nova AI - lightweight approach with timeout protection"""
    try:
        import boto3
        
        if not required_params or not prompt.strip():
            return {}
        
        # Quick check - if all required params are already in metadata, skip Nova call
        if metadata and isinstance(metadata, dict) and isinstance(required_params, dict):
            metadata_has_all = all(
                resolve_with_aliases(param, metadata) is not None 
                for param in required_params.keys()
            )
            if metadata_has_all:
                print(f"[DEBUG] Skipping Nova - all params available in metadata")
                return {}
        
        # Simple extraction prompt focused on user intent
        extraction_prompt = f"""Extract parameters from this user request:

"{prompt}"

Required parameters: {list(required_params.keys()) if isinstance(required_params, dict) else []}

Extract ONLY the values explicitly mentioned. For stack names, look for words after "stack", "for", or similar indicators.

Return JSON format: {{"parameter_name": "value"}}

Examples:
- "cost for stack my-app" → {{"stack_name": "my-app"}}
- "pricing for sample-demo stack" → {{"stack_name": "sample-demo"}}
- "list services in my-cluster" → {{"cluster": "my-cluster"}}"""

        bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        
        response = bedrock.invoke_model(
            modelId='amazon.nova-micro-v1:0',
            body=json.dumps({
                "messages": [{"role": "user", "content": [{"text": extraction_prompt}]}],
                "inferenceConfig": {"maxTokens": 100, "temperature": 0}
            })
        )
        
        result = json.loads(response['body'].read())
        content = result['output']['message']['content'][0]['text'].strip()
        
        print(f"[DEBUG] Nova extraction - Input: {prompt[:50]}...")
        print(f"[DEBUG] Nova extraction - Output: {content}")
        
        try:
            # Remove markdown code blocks if present
            content_clean = content.strip()
            if content_clean.startswith('```json'):
                content_clean = content_clean[7:]
            if content_clean.startswith('```'):
                content_clean = content_clean[3:]
            if content_clean.endswith('```'):
                content_clean = content_clean[:-3]
            content_clean = content_clean.strip()
            
            extracted = json.loads(content_clean)
            if isinstance(extracted, dict):
                return {k: v for k, v in extracted.items() if k in required_params and v is not None}
            return {}
        except json.JSONDecodeError:
            print(f"[DEBUG] JSON parsing failed: {content}")
            return {}
            
    except Exception as e:
        print(f"[DEBUG] Parameter extraction failed: {e}")
        return {}

def resolve_required_params(tool_name: str, model_args: dict, ctx: dict) -> dict:
    """
    Context-aware parameter resolution with alias handling and performance optimization
    """
    resolved = {}
    missing = []
    
    metadata = ctx.get("metadata", {})
    aws_ctx = ctx.get("aws", {})
    
    # Common AWS parameters (always from context)
    resolved.update({
        "account_id": aws_ctx.get("account_id"),
        "region": aws_ctx.get("region"),
        "shim_url": aws_ctx.get("shim_url")
    })
    
    # Get parameter requirements from model_args
    required_params = {}
    required_list = []
    if "arguments" in model_args and "properties" in model_args["arguments"]:
        for param_name, param_def in model_args["arguments"]["properties"].items():
            if param_name not in ["account_id", "region", "shim_url"]:  # Skip AWS context params
                description = param_def.get("description", f"{param_name} parameter")
                param_type = param_def.get("type", "string")
                required_params[param_name] = f"{param_type} - {description}"
        
        required_list = model_args["arguments"].get("required", [])
    
    # Fast path: try to resolve all parameters from metadata first
    all_resolved_from_metadata = True
    for param_name in required_params:
        value = resolve_with_aliases(param_name, metadata)
        if value is not None:
            resolved[param_name] = value
        elif param_name in required_list:
            all_resolved_from_metadata = False
            break
    
    # Only call Nova if we couldn't resolve required params from metadata
    user_params = {}
    if not all_resolved_from_metadata and required_params:
        user_params = extract_parameters_with_bedrock(
            ctx.get("prompt", ""), 
            required_params,
            metadata
        )
    
    print(f"[DEBUG] Tool: {tool_name}, Required: {required_list}")
    print(f"[DEBUG] User params extracted: {user_params}")
    print(f"[DEBUG] Metadata keys: {list(metadata.keys()) if isinstance(metadata, dict) else 'not-dict'}")
    
    # Final resolution with user params as override
    for param_name in required_params:
        if param_name not in resolved:  # Not already resolved from metadata
            value = resolve_with_aliases(param_name, metadata, user_params)
            print(f"[DEBUG] Resolving {param_name}: {value}")
            if value is not None:
                resolved[param_name] = value
            elif param_name in required_list:
                missing.append(param_name)
    
    # Check for missing required parameters
    if missing:
        raise MissingParamsError(missing, tool_name)
    
    return {k: v for k, v in resolved.items() if v is not None}

class MissingParamsError(Exception):
    """Raised when required parameters are missing"""
    def __init__(self, missing_params: List[str], tool_name: str):
        self.missing_params = missing_params
        self.tool_name = tool_name
        super().__init__(f"Missing required parameters for {tool_name}: {missing_params}")

def get_missing_params_response(missing_params: List[str], tool_name: str, correlation_id: str = None) -> dict:
    """Standard response for missing parameters"""
    response = {
        "error_type": "MISSING_PARAMS",
        "tool": tool_name,
        "missing": missing_params,
        "message": f"Missing required parameters for {tool_name}: {', '.join(missing_params)}. Provide them in metadata or request."
    }
    if correlation_id:
        response["correlation_id"] = correlation_id
    return response
