#!/usr/bin/env python3

import requests
import json
import time
import boto3

# Download script from S3 using boto3
try:
    s3 = boto3.client('s3')
    print('Downloading test script from S3...')
    # This is just a placeholder - we'll run the test directly
except Exception as e:
    print(f'S3 setup: {e}')

# Wait for service to be ready
time.sleep(60)

broker_url = 'http://internal-broker-internal-alb-572182136.us-east-1.elb.amazonaws.com'

print('TESTING DEPLOY-FIX2 DEPLOYMENT TOOLS')
print('='*50)

# Test deployment tool with proper metadata
payload = {
    'ask_text': 'Get deployment run details for run_id 20490873394 in repo Demo-MCP/mcp-cross-account-pipeline',
    'metadata': {
        'repo': 'Demo-MCP/mcp-cross-account-pipeline',
        'run_id': '20490873394'
    }
}

try:
    response = requests.post(f'{broker_url}/admin', json=payload, timeout=90)
    print(f'Status: {response.status_code}')
    
    if response.status_code == 200:
        data = response.json()
        print('Response structure:')
        print(json.dumps(data, indent=2)[:2000])
        
        # Try to extract the actual content
        if isinstance(data, dict):
            answer = data.get('answer', {})
            if isinstance(answer, dict):
                message = answer.get('message', {})
                if isinstance(message, dict):
                    content = message.get('content', [])
                    if content and len(content) > 0:
                        text = content[0].get('text', 'No text found')
                        print('\nExtracted text:')
                        print(text[:1000])
                    else:
                        print('\nNo content array found')
                else:
                    print(f'\nMessage is not dict: {type(message)}')
            else:
                print(f'\nAnswer is not dict: {type(answer)}')
        else:
            print(f'\nData is not dict: {type(data)}')
    else:
        print(f'Error response: {response.text}')
        
except Exception as e:
    print(f'Exception: {e}')

print('\nDEPLOY-FIX2 TEST COMPLETE!')
