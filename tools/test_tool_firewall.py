#!/usr/bin/env python3
"""
Test tool firewall enforcement
"""
import requests
import json

def test_tool_firewall():
    """Test that user endpoint blocks admin-only tools"""
    
    broker_url = "http://internal-broker-internal-alb-572182136.us-east-1.elb.amazonaws.com"
    
    # Test 1: User tries to access admin-only PR tool
    print("🧪 Test 1: User endpoint blocks PR tools")
    
    user_request = {
        "ask_text": "Get the diff for PR #123",
        "account_id": "500330120558",
        "region": "us-east-1",
        "metadata": {
            "actor": "test-user",
            "repository": "Demo-MCP/test-repo",
            "pr_number": 123,
            "run_id": "test-run"
        }
    }
    
    try:
        response = requests.post(
            f"{broker_url}/ask",
            json=user_request,
            headers={"x-correlation-id": "test__firewall-test__user-blocked"},
            timeout=30
        )
        
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        
        # Check if PR tools were denied
        denied_tools = result.get("debug", {}).get("denied_tool_calls", [])
        if any("pr_" in tool for tool in denied_tools):
            print("✅ PASS: User endpoint correctly blocked PR tools")
        else:
            print("❌ FAIL: User endpoint should have blocked PR tools")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Test 2: Admin endpoint allows PR tools
    print("\n🧪 Test 2: Admin endpoint allows PR tools")
    
    try:
        response = requests.post(
            f"{broker_url}/admin", 
            json=user_request,
            headers={"x-correlation-id": "test__firewall-test__admin-allowed"},
            timeout=30
        )
        
        result = response.json()
        tools_called = result.get("debug", {}).get("tools_called", [])
        denied_tools = result.get("debug", {}).get("denied_tool_calls", [])
        
        print(f"Tools called: {tools_called}")
        print(f"Tools denied: {denied_tools}")
        
        if not any("pr_" in tool for tool in denied_tools):
            print("✅ PASS: Admin endpoint allows PR tools")
        else:
            print("❌ FAIL: Admin endpoint should allow PR tools")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    test_tool_firewall()
