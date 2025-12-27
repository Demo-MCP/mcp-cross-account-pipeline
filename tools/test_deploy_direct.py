#!/usr/bin/env python3
import requests
import json

def test_deployment_direct():
    base_url = 'http://internal-mcp-internal-alb-2059913293.us-east-1.elb.amazonaws.com'
    
    print('🔗 DIRECT DEPLOYMENT MCP TEST (with repository)')
    print('=' * 50)
    
    # Test deploy_find_latest directly with "repository" parameter
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "deploy_find_latest",
            "arguments": {
                "repository": "Demo-MCP/mcp-cross-account-pipeline"
            }
        },
        "metadata": {
            "actor": "github-user",
            "repository": "Demo-MCP/mcp-cross-account-pipeline"
        },
        "id": 1
    }
    
    try:
        url = f'{base_url}/metrics'
        print(f'URL: {url}')
        print(f'Payload: {json.dumps(payload, indent=2)}')
        
        response = requests.post(
            url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f'\nStatus: {response.status_code}')
        
        if response.status_code == 200:
            data = response.json()
            print('Response:')
            print(json.dumps(data, indent=2))
        else:
            print(f'Error: {response.text}')
            
    except Exception as e:
        print(f'Exception: {e}')

if __name__ == '__main__':
    test_deployment_direct()
