#!/usr/bin/env python3
import requests
import json
import time

def test_admin_tools():
    url = 'http://internal-broker-internal-alb-572182136.us-east-1.elb.amazonaws.com'
    
    print('🔧 COMPREHENSIVE ADMIN TOOLS TEST')
    print('=' * 50)
    
    # Test cases with specific metadata
    tests = [
        {
            'name': 'ECS Clusters',
            'query': 'List ECS clusters',
            'description': 'Test ECS resource management tool'
        },
        {
            'name': 'ECS Services', 
            'query': 'List ECS services in cluster mcp-cluster',
            'description': 'Test ECS service listing with cluster parameter'
        },
        {
            'name': 'CloudFormation Stack',
            'query': 'Troubleshoot CloudFormation stack sample-demo',
            'description': 'Test IAC troubleshooting tool'
        },
        {
            'name': 'Deployment Status',
            'query': 'deployment run_id status 20490873394',
            'description': 'Test deployment metrics with specific run ID'
        },
        {
            'name': 'Pull Request Analysis',
            'query': 'Analyze pull request 9 for repo Demo-MCP/mcp-cross-account-pipeline with run_id 20490873394 and stackName sample-demo',
            'description': 'Test PR analysis tool with metadata'
        },
        {
            'name': 'Pricing Calculator',
            'query': 'Calculate pricing for t3.micro instance',
            'description': 'Test pricing calculation tool'
        }
    ]
    
    results = []
    
    for i, test in enumerate(tests, 1):
        print(f'\n{i}. {test["name"]}')
        print(f'   Query: {test["query"]}')
        print(f'   Description: {test["description"]}')
        
        try:
            response = requests.post(
                f'{url}/admin',
                json={'ask_text': test['query']},
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data.get('answer', {}).get('message', {}).get('content', 'No content')
                debug_info = data.get('debug', {})
                
                print(f'   ✅ SUCCESS')
                print(f'   Tier: {debug_info.get("tier", "unknown")}')
                print(f'   Tools Available: {debug_info.get("tools_advertised_count", "unknown")}')
                print(f'   Response: {content[:150]}...')
                
                results.append({
                    'test': test['name'],
                    'status': 'SUCCESS',
                    'tier': debug_info.get('tier'),
                    'tools_count': debug_info.get('tools_advertised_count'),
                    'response_length': len(content)
                })
            else:
                print(f'   ❌ HTTP ERROR: {response.status_code}')
                results.append({
                    'test': test['name'],
                    'status': f'HTTP_ERROR_{response.status_code}',
                    'tier': None,
                    'tools_count': None,
                    'response_length': 0
                })
                
        except Exception as e:
            print(f'   ❌ EXCEPTION: {str(e)}')
            results.append({
                'test': test['name'],
                'status': f'EXCEPTION: {str(e)}',
                'tier': None,
                'tools_count': None,
                'response_length': 0
            })
        
        time.sleep(2)  # Rate limiting
    
    # Summary
    print('\n' + '=' * 50)
    print('📊 TEST SUMMARY')
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
        if result['tier']:
            print(f'   └─ Tier: {result["tier"]}, Tools: {result["tools_count"]}, Response: {result["response_length"]} chars')
    
    print('\n🎯 ADMIN TOOLS TEST COMPLETE!')

if __name__ == '__main__':
    test_admin_tools()
