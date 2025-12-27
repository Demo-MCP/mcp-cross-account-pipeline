#!/usr/bin/env python3
import requests
import json
import time

def test_direct_alb_endpoints():
    base_url = 'http://internal-mcp-internal-alb-2059913293.us-east-1.elb.amazonaws.com'
    
    print('🔗 DIRECT ALB ENDPOINT TESTS')
    print('=' * 50)
    
    # Direct MCP server tests with proper metadata
    tests = [
        {
            'name': 'ECS Root Endpoint',
            'path': '/call-tool',
            'payload': {
                "server": "ecs",
                "tool": "ecs_resource_management",
                "params": {
                    "api_operation": "ListClusters",
                    "api_params": {},
                    "account_id": "500330120558",
                    "region": "us-east-1"
                }
            },
            'description': 'Direct ECS MCP server call via /call-tool'
        },
        {
            'name': 'ECS Services',
            'path': '/call-tool',
            'payload': {
                "server": "ecs",
                "tool": "ecs_resource_management",
                "params": {
                    "api_operation": "ListServices",
                    "api_params": {"cluster": "mcp-cluster"},
                    "account_id": "500330120558",
                    "region": "us-east-1"
                }
            },
            'description': 'Direct ECS services call via /call-tool'
        },
        {
            'name': 'CloudFormation IAC',
            'path': '/call-tool',
            'payload': {
                "server": "iac",
                "tool": "troubleshoot_cloudformation_deployment",
                "params": {
                    "stack_name": "sample-demo",
                    "account_id": "500330120558",
                    "region": "us-east-1"
                }
            },
            'description': 'Direct IAC troubleshooting call via /call-tool'
        },
        {
            'name': 'Deployment Metrics',
            'path': '/metrics',
            'payload': {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "deploy_get_run",
                    "arguments": {
                        "repo": "Demo-MCP/mcp-cross-account-pipeline",
                        "run_id": "20490873394"
                    }
                },
                "metadata": {
                    "actor": "github-user",
                    "repo": "Demo-MCP/mcp-cross-account-pipeline",
                    "pr_number": "9",
                    "run_id": "20490873394",
                    "stackName": "sample-demo"
                },
                "id": 4
            },
            'description': 'Direct deployment metrics call'
        },
        {
            'name': 'PR Analysis',
            'path': '/pr',
            'payload': {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "pr_get_diff",
                    "arguments": {
                        "repo": "Demo-MCP/mcp-cross-account-pipeline",
                        "pr_number": "9",
                        "actor": "github-user",
                        "run_id": "20490873394"
                    }
                },
                "metadata": {
                    "actor": "github-user",
                    "repo": "Demo-MCP/mcp-cross-account-pipeline",
                    "pr_number": "9",
                    "run_id": "20490873394",
                    "stackName": "sample-demo"
                },
                "id": 5
            },
            'description': 'Direct PR analysis call'
        },
        {
            'name': 'Pricing Calculator',
            'path': '/pricingcalc',
            'payload': {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "pricingcalc_estimate_from_cfn",
                    "arguments": {
                        "cfn_template": "t3.micro instance",
                        "region": "us-east-1"
                    }
                },
                "metadata": {
                    "actor": "github-user",
                    "repo": "Demo-MCP/mcp-cross-account-pipeline",
                    "pr_number": "9",
                    "run_id": "20490873394",
                    "stackName": "sample-demo"
                },
                "id": 6
            },
            'description': 'Direct pricing calculation call'
        }
    ]
    
    results = []
    
    for i, test in enumerate(tests, 1):
        print(f'\n{i}. {test["name"]}')
        print(f'   Path: {test["path"]}')
        print(f'   Tool: {test["payload"]["params"]["name"]}')
        print(f'   Description: {test["description"]}')
        
        try:
            url = f'{base_url}{test["path"]}'
            response = requests.post(
                url,
                json=test['payload'],
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            print(f'   Status: {response.status_code}')
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if 'result' in data:
                        result_content = str(data['result'])[:200]
                        print(f'   ✅ SUCCESS: {result_content}...')
                        results.append({
                            'test': test['name'],
                            'status': 'SUCCESS',
                            'response_length': len(str(data['result'])),
                            'has_error': 'error' in data
                        })
                    elif 'error' in data:
                        print(f'   ❌ JSON-RPC ERROR: {data["error"]}')
                        results.append({
                            'test': test['name'],
                            'status': f'JSON_RPC_ERROR: {data["error"].get("message", "Unknown")}',
                            'response_length': 0,
                            'has_error': True
                        })
                    else:
                        print(f'   ⚠️  UNEXPECTED RESPONSE: {str(data)[:100]}...')
                        results.append({
                            'test': test['name'],
                            'status': 'UNEXPECTED_RESPONSE',
                            'response_length': len(str(data)),
                            'has_error': False
                        })
                except json.JSONDecodeError:
                    print(f'   ❌ INVALID JSON: {response.text[:100]}...')
                    results.append({
                        'test': test['name'],
                        'status': 'INVALID_JSON',
                        'response_length': len(response.text),
                        'has_error': True
                    })
            else:
                print(f'   ❌ HTTP ERROR: {response.status_code} - {response.text[:100]}...')
                results.append({
                    'test': test['name'],
                    'status': f'HTTP_{response.status_code}',
                    'response_length': len(response.text),
                    'has_error': True
                })
                
        except Exception as e:
            print(f'   ❌ EXCEPTION: {str(e)}')
            results.append({
                'test': test['name'],
                'status': f'EXCEPTION: {str(e)}',
                'response_length': 0,
                'has_error': True
            })
        
        time.sleep(1)  # Rate limiting
    
    # Summary
    print('\n' + '=' * 50)
    print('📊 DIRECT ALB TEST SUMMARY')
    print('=' * 50)
    
    successful = len([r for r in results if r['status'] == 'SUCCESS'])
    total = len(results)
    
    print(f'Total Tests: {total}')
    print(f'Successful: {successful}')
    print(f'Failed: {total - successful}')
    print(f'Success Rate: {(successful/total)*100:.1f}%')
    
    print('\n📋 DETAILED RESULTS:')
    for result in results:
        status_emoji = '✅' if result['status'] == 'SUCCESS' else '❌'
        print(f'{status_emoji} {result["test"]}: {result["status"]}')
        if result['response_length'] > 0:
            print(f'   └─ Response: {result["response_length"]} chars, Error: {result["has_error"]}')
    
    print('\n🎯 DIRECT ALB TEST COMPLETE!')

if __name__ == '__main__':
    test_direct_alb_endpoints()
