#!/usr/bin/env python3
"""
创建测试用户的脚本
"""
import httpx
import sys

def create_test_user():
    """Create a test user for system testing"""
    print("Creating test user...")
    
    try:
        # 注册用户
        response = httpx.post(
            "http://localhost:8000/auth/register",
            json={
                "username": "admin",
                "email": "admin@example.com",
                "password": "123456"
            },
            timeout=10
        )
        
        print(f"Registration response: {response.status_code}")
        print(f"Registration response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Test user created successfully!")
            return True
        else:
            print(f"❌ Registration failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to create test user: {e}")
        return False

if __name__ == "__main__":
    success = create_test_user()
    sys.exit(0 if success else 1)