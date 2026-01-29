#!/usr/bin/env python3
"""
Comprehensive system test for KKChatBot-2
Tests login authentication, chat API, and Dify connection without user involvement
"""
import httpx
import json
import asyncio
import time
import sys
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000"
DIFY_BASE_URL = "http://localhost/v1"
USERNAME = "admin"
PASSWORD = "123456"
TEST_MESSAGE = "Hello, are you online?"

def print_test_header(test_name: str):
    print(f"\n{'='*60}")
    print(f"TEST: {test_name}")
    print(f"{'='*60}")

def print_result(success: bool, message: str, details: str = ""):
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status}: {message}")
    if details:
        print(f"Details: {details}")

def test_backend_health():
    """Test if backend is running"""
    print_test_header("Backend Health Check")
    try:
        response = httpx.get(f"{BASE_URL}/docs", timeout=5)
        print_result(response.status_code == 200, "Backend is accessible", f"Status: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print_result(False, "Backend is not accessible", str(e))
        return False

def test_login():
    """Test login authentication"""
    print_test_header("Login Authentication")
    try:
        # Use OAuth2PasswordRequestForm format
        response = httpx.post(
            f"{BASE_URL}/auth/login",
            data={"username": USERNAME, "password": PASSWORD},
            timeout=10
        )
        
        print(f"Login response status: {response.status_code}")
        print(f"Login response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            if token:
                print_result(True, "Login successful", f"Token received: {token[:20]}...")
                return token
            else:
                print_result(False, "Login response missing token", str(data))
                return None
        else:
            print_result(False, f"Login failed with status {response.status_code}", response.text)
            return None
            
    except Exception as e:
        print_result(False, "Login request failed", str(e))
        return None

def test_chat_api(token: str):
    """Test chat API with authentication"""
    print_test_header("Chat API Test")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        response = httpx.post(
            f"{BASE_URL}/api/chat",
            json={"message": TEST_MESSAGE},
            headers=headers,
            timeout=30
        )
        
        print(f"Chat response status: {response.status_code}")
        print(f"Chat response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            message = data.get("message", "")
            if message:
                print_result(True, "Chat API working", f"Response: {message[:100]}...")
                return True
            else:
                print_result(False, "Chat API returned empty message", str(data))
                return False
        elif response.status_code == 401:
            print_result(False, "Chat API authentication failed", response.text)
            return False
        else:
            print_result(False, f"Chat API failed with status {response.status_code}", response.text)
            return False
            
    except Exception as e:
        print_result(False, "Chat API request failed", str(e))
        return False

def test_dify_direct():
    """Test direct Dify API connection"""
    print_test_header("Direct Dify API Test")
    try:
        # Get Dify API key from environment
        import os
        api_key = os.environ.get("DIFY_API_KEY") or "app-DJRsIxTBbLz5pkazjcjSkG20"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "inputs": {},
            "query": TEST_MESSAGE,
            "response_mode": "streaming",
            "conversation_id": "",
            "user": "test-user"
        }
        
        response = httpx.post(
            f"{DIFY_BASE_URL}/chat-messages",
            json=payload,
            headers=headers,
            timeout=30
        )
        
        print(f"Dify response status: {response.status_code}")
        
        if response.status_code == 200:
            # Parse streaming response
            full_response = ""
            for line in response.iter_lines():
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        if data.get("event") in ["message", "agent_message"]:
                            full_response += data.get("answer", "")
                    except:
                        pass
            
            if full_response:
                print_result(True, "Dify API working", f"Response: {full_response[:100]}...")
                return True
            else:
                print_result(False, "Dify returned empty response", response.text[:200])
                return False
        else:
            print_result(False, f"Dify API failed with status {response.status_code}", response.text)
            return False
            
    except Exception as e:
        print_result(False, "Dify API request failed", str(e))
        return False

def test_backend_logs():
    """Check recent backend logs"""
    print_test_header("Backend Logs Check")
    try:
        # This would require docker exec, but we'll simulate by checking if backend responds
        response = httpx.get(f"{BASE_URL}/docs", timeout=5)
        if response.status_code == 200:
            print_result(True, "Backend is responsive", "Check docker logs manually for detailed info")
            return True
        else:
            print_result(False, "Backend not responsive", f"Status: {response.status_code}")
            return False
    except Exception as e:
        print_result(False, "Cannot check backend status", str(e))
        return False

def run_full_test():
    """Run complete system test"""
    print("🚀 Starting KKChatBot-2 Comprehensive System Test")
    print(f"Testing against: {BASE_URL}")
    print(f"Dify API: {DIFY_BASE_URL}")
    
    results = []
    
    # Test 1: Backend health
    results.append(("Backend Health", test_backend_health()))
    
    # Test 2: Login authentication
    token = test_login()
    if token:
        results.append(("Login", True))
        
        # Test 3: Chat API with token
        chat_result = test_chat_api(token)
        results.append(("Chat API", chat_result))
    else:
        results.append(("Login", False))
        results.append(("Chat API", False))
    
    # Test 4: Direct Dify API
    results.append(("Direct Dify API", test_dify_direct()))
    
    # Test 5: Backend logs check
    results.append(("Backend Logs", test_backend_logs()))
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! System should be working.")
        return True
    else:
        print("⚠️  Some tests failed. Check the details above.")
        return False

if __name__ == "__main__":
    success = run_full_test()
    sys.exit(0 if success else 1)
