#!/usr/bin/env python3
"""
Comprehensive Broker Tier Security Test Suite
Tests all tools on /admin vs /ask endpoints to validate tier-based access control
"""
import requests
import json
import time
from typing import Dict, List, Any

BROKER_URL = "http://internal-broker-internal-alb-572182136.us-east-1.elb.amazonaws.com"
TIMEOUT = 60

# Test metadata for PR tools
TEST_METADATA = {
    'repository': 'Demo-MCP/mcp-cross-account-pipeline',
    'pr_number': 9,
    'actor': 'admin',
    'run_id': '20490873394'
}

# Tool test cases with expected behavior
TOOL_TESTS = {
    # PR Tools (Admin only)
    'pr_get_diff': {
        'admin_allowed': True,
        'user_allowed': False,
        'test_payload': {
            'ask_text': 'Get diff for pull request #9',
            'metadata': TEST_METADATA
        }
    },
    'pr_summarize': {
        'admin_allowed': True,
        'user_allowed': False,
        'test_payload': {
            'ask_text': 'Summarize pull request #9',
            'metadata': TEST_METADATA
        }
    },
    
    # Deploy Tools (Both tiers)
    'deploy_find_latest': {
        'admin_allowed': True,
        'user_allowed': True,
        'test_payload': {
            'ask_text': 'Find latest deployment for Demo-MCP/mcp-cross-account-pipeline',
            'metadata': {'repository': 'Demo-MCP/mcp-cross-account-pipeline'}
        }
    },
    'deploy_get_summary': {
        'admin_allowed': True,
        'user_allowed': True,
        'test_payload': {
            'ask_text': 'Get deployment summary for run 20490873394',
            'metadata': {'repository': 'Demo-MCP/mcp-cross-account-pipeline', 'run_id': '20490873394'}
        }
    },
    
    # Pricing Tools (Both tiers)
    'pricingcalc_estimate_from_stack': {
        'admin_allowed': True,
        'user_allowed': True,
        'test_payload': {
            'ask_text': 'Get pricing estimate for pr-context-mcp CloudFormation stack'
        }
    },
    
    # IAC Tools (Both tiers)
    'iac_call_tool': {
        'admin_allowed': True,
        'user_allowed': True,
        'test_payload': {
            'ask_text': 'Check status of pr-context-mcp CloudFormation stack'
        }
    },
    
    # ECS Tools (Both tiers)
    'ecs_call_tool': {
        'admin_allowed': True,
        'user_allowed': True,
        'test_payload': {
            'ask_text': 'List ECS clusters'
        }
    }
}

def test_endpoint(endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Test a single endpoint with payload"""
    try:
        response = requests.post(f"{BROKER_URL}/{endpoint}", json=payload, timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            return {
                'success': True,
                'tools_called': data.get('debug', {}).get('tools_called', []),
                'tools_denied': data.get('debug', {}).get('denied_tool_calls', []),
                'tools_advertised': data.get('debug', {}).get('tools_advertised_count', 0),
                'response_length': len(data.get('answer', '')),
                'time_ms': data.get('debug', {}).get('total_ms', 0)
            }
        else:
            return {
                'success': False,
                'error': f"HTTP {response.status_code}: {response.text[:200]}"
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def run_comprehensive_test():
    """Run comprehensive test suite"""
    print("🧪 COMPREHENSIVE BROKER TIER SECURITY TEST")
    print("=" * 60)
    
    results = {
        'admin': {},
        'ask': {},
        'summary': {
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'admin_tools': 0,
            'user_tools': 0,
            'security_violations': []
        }
    }
    
    # Test each tool on both endpoints
    for tool_name, test_config in TOOL_TESTS.items():
        print(f"\n🔧 Testing {tool_name}")
        print("-" * 40)
        
        # Test admin endpoint
        print("  Admin endpoint:", end=" ")
        admin_result = test_endpoint('admin', test_config['test_payload'])
        results['admin'][tool_name] = admin_result
        
        if admin_result['success']:
            called_expected_tool = any(tool_name in str(tool) for tool in admin_result['tools_called'])
            print(f"✅ SUCCESS - Tools: {admin_result['tools_called']}")
        else:
            print(f"❌ FAILED - {admin_result['error']}")
        
        # Test ask endpoint
        print("  User endpoint: ", end=" ")
        ask_result = test_endpoint('ask', test_config['test_payload'])
        results['ask'][tool_name] = ask_result
        
        if ask_result['success']:
            called_restricted_tool = any(tool_name in str(tool) for tool in ask_result['tools_called']) and not test_config['user_allowed']
            if called_restricted_tool:
                results['summary']['security_violations'].append(f"User tier called restricted tool: {tool_name}")
                print(f"🚨 SECURITY VIOLATION - Called: {ask_result['tools_called']}")
            else:
                print(f"✅ SUCCESS - Tools: {ask_result['tools_called']}")
        else:
            print(f"❌ FAILED - {ask_result['error']}")
        
        results['summary']['total_tests'] += 2
    
    # Get tool counts
    admin_sample = next(iter(results['admin'].values()))
    ask_sample = next(iter(results['ask'].values()))
    
    if admin_sample['success']:
        results['summary']['admin_tools'] = admin_sample['tools_advertised']
    if ask_sample['success']:
        results['summary']['user_tools'] = ask_sample['tools_advertised']
    
    # Calculate pass/fail
    for endpoint_results in [results['admin'], results['ask']]:
        for result in endpoint_results.values():
            if result['success']:
                results['summary']['passed'] += 1
            else:
                results['summary']['failed'] += 1
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {results['summary']['total_tests']}")
    print(f"Passed: {results['summary']['passed']}")
    print(f"Failed: {results['summary']['failed']}")
    print(f"Admin Tools Available: {results['summary']['admin_tools']}")
    print(f"User Tools Available: {results['summary']['user_tools']}")
    print(f"Tool Difference: {results['summary']['admin_tools'] - results['summary']['user_tools']} (admin-only tools)")
    
    if results['summary']['security_violations']:
        print(f"\n🚨 SECURITY VIOLATIONS: {len(results['summary']['security_violations'])}")
        for violation in results['summary']['security_violations']:
            print(f"  - {violation}")
    else:
        print("\n✅ NO SECURITY VIOLATIONS DETECTED")
    
    # Tier security validation
    print(f"\n🔒 TIER SECURITY VALIDATION:")
    if results['summary']['admin_tools'] > results['summary']['user_tools']:
        print("✅ Admin tier has more tools than user tier (expected)")
    else:
        print("❌ Admin and user tiers have same tool count (unexpected)")
    
    success_rate = (results['summary']['passed'] / results['summary']['total_tests']) * 100
    print(f"\n📈 SUCCESS RATE: {success_rate:.1f}%")
    
    return results

if __name__ == "__main__":
    run_comprehensive_test()
