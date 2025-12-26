#!/usr/bin/env python3
"""
Broker Tier Test Suite
Tests tool accessibility across /ask and /admin endpoints
"""

import requests
import json
import time

BROKER_URL = "http://internal-broker-internal-alb-572182136.us-east-1.elb.amazonaws.com"

# Test cases: (tool_name, expected_on_ask, expected_on_admin, test_query)
TEST_CASES = [
    # User-allowed tools (should work on both)
    ("ecs_call_tool", True, True, "List ECS clusters"),
    ("iac_call_tool", True, True, "Check CloudFormation stacks"),
    ("deploy_find_latest", True, True, "Find latest deployment for mcp-cross-account-pipeline"),
    ("pricingcalc_estimate_from_cfn", True, True, "Estimate costs for a CloudFormation template"),
    
    # Admin-only tools (should only work on /admin)
    ("pr_get_diff", False, True, "Get PR diff for Demo-MCP/mcp-cross-account-pipeline PR 9"),
    ("pr_summarize", False, True, "Analyze PR changes with security scanning"),
    
    # Test cases that should trigger denials
    ("pr_get_diff", False, False, "Get PR diff for Demo-MCP/mcp-cross-account-pipeline PR 9 on /ask"),
    ("fake_admin_tool", False, False, "Use fake_admin_tool to do something"),
]

def test_endpoint(endpoint, query, tool_name=None):
    """Test an endpoint and return tools called/denied"""
    url = f"{BROKER_URL}/{endpoint}"
    payload = {"ask_text": query}
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        debug = data.get("debug", {})
        answer = data.get("answer", "")
        
        # Check for error indicators in response
        has_error = "error" in answer.lower() or "not allowed" in answer.lower() or "denied" in answer.lower()
        
        return {
            "success": True,
            "tools_advertised": debug.get("tools_advertised_count", 0),
            "tools_called": debug.get("tools_called", []),
            "denied_tools": debug.get("denied_tool_calls", []),
            "tier": debug.get("tier", "unknown"),
            "total_ms": debug.get("total_ms", 0),
            "answer_preview": answer[:150] + "..." if len(answer) > 150 else answer,
            "has_error": has_error,
            "response_size": len(json.dumps(data))
        }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Request timeout (60s)"
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Request failed: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }

def run_test_suite():
    """Run complete test suite"""
    print("🧪 Broker Tier Test Suite")
    print("=" * 60)
    
    results = {
        "ask": {},
        "admin": {},
        "summary": {}
    }
    
    # Test each endpoint
    for endpoint in ["ask", "admin"]:
        print(f"\n📋 Testing /{endpoint} endpoint:")
        print("-" * 40)
        
        # Test with a general query to see tool counts
        general_result = test_endpoint(endpoint, "What tools are available?")
        if general_result["success"]:
            print(f"✅ Tier: {general_result['tier']}")
            print(f"✅ Tools advertised: {general_result['tools_advertised']}")
            print(f"✅ Response time: {general_result['total_ms']}ms")
        else:
            print(f"❌ Endpoint failed: {general_result['error']}")
            continue
        
        results[endpoint]["general"] = general_result
        
        # Test specific tool access patterns
        for tool_name, expected_on_ask, expected_on_admin, query in TEST_CASES:
            expected = expected_on_admin if endpoint == "admin" else expected_on_ask
            
            print(f"\n🔧 Testing {tool_name} access:")
            result = test_endpoint(endpoint, query, tool_name)
            
            if result["success"]:
                tool_called = tool_name in result["tools_called"]
                tool_denied = tool_name in result["denied_tools"]
                has_error = result["has_error"]
                
                # Determine test outcome
                if expected and tool_called and not has_error:
                    status = "✅ PASS: Tool executed successfully"
                elif not expected and tool_denied:
                    status = "✅ PASS: Tool properly denied"
                elif not expected and has_error and not tool_called:
                    status = "✅ PASS: Tool blocked with error"
                elif not expected and not tool_called and not tool_denied and not has_error:
                    status = "✅ PASS: Tool not attempted by model"
                else:
                    status = f"❌ FAIL: Expected={expected}, Called={tool_called}, Denied={tool_denied}, Error={has_error}"
                
                print(f"   {status}")
                print(f"   Tools called: {result['tools_called']}")
                print(f"   Tools denied: {result['denied_tools']}")
                print(f"   Response time: {result['total_ms']}ms")
                
                if has_error:
                    print(f"   Error in response: {result['answer_preview']}")
                    
            else:
                print(f"❌ FAIL: Request error - {result['error']}")
            
            results[endpoint][tool_name] = result
            time.sleep(2)  # Rate limiting between tests
    
    # Generate summary
    ask_success = results["ask"]["general"]["success"] if "general" in results["ask"] else False
    admin_success = results["admin"]["general"]["success"] if "general" in results["admin"] else False
    
    if ask_success and admin_success:
        ask_tools = results["ask"]["general"]["tools_advertised"]
        admin_tools = results["admin"]["general"]["tools_advertised"]
        
        results["summary"] = {
            "ask_tools_count": ask_tools,
            "admin_tools_count": admin_tools,
            "additional_admin_tools": admin_tools - ask_tools,
            "tier_separation_working": admin_tools > ask_tools,
            "both_endpoints_responsive": True
        }
    else:
        results["summary"] = {
            "both_endpoints_responsive": False,
            "ask_working": ask_success,
            "admin_working": admin_success
        }
    
    # Print summary
    print("\n📊 Test Summary:")
    print("=" * 60)
    
    if results["summary"]["both_endpoints_responsive"]:
        print(f"✅ /ask endpoint: {results['summary']['ask_tools_count']} tools")
        print(f"✅ /admin endpoint: {results['summary']['admin_tools_count']} tools")
        print(f"✅ Admin additional tools: {results['summary']['additional_admin_tools']}")
        print(f"✅ Tier separation: {'Working' if results['summary']['tier_separation_working'] else 'BROKEN'}")
    else:
        print(f"❌ /ask working: {results['summary']['ask_working']}")
        print(f"❌ /admin working: {results['summary']['admin_working']}")
    
    return results

def save_results(results):
    """Save test results to file"""
    timestamp = int(time.time())
    filename = f"/tmp/broker_test_results_{timestamp}.json"
    
    with open(filename, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to {filename}")
    return filename

if __name__ == "__main__":
    print("Starting broker tier test suite...")
    results = run_test_suite()
    save_results(results)
    
    # Exit with appropriate code
    if results["summary"].get("both_endpoints_responsive", False):
        print("\n🎉 Test suite completed successfully!")
        exit(0)
    else:
        print("\n💥 Test suite found issues!")
        exit(1)
