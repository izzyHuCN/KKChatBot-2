import httpx
import asyncio
import json
import sys

# 配置
API_BASE_URL = "http://localhost:8000"
USERNAME = "testuser_debug"
PASSWORD = "password123"
EMAIL = "test_debug@example.com"

async def main():
    async with httpx.AsyncClient(timeout=30.0) as client:
        print(f"Checking API health at {API_BASE_URL}/health ...")
        try:
            resp = await client.get(f"{API_BASE_URL}/health")
            print(f"Health check: {resp.status_code} {resp.json()}")
        except Exception as e:
            print(f"Failed to connect to backend: {e}")
            return

        # 1. Register (or ignore if exists)
        print("\nAttempting registration...")
        try:
            resp = await client.post(f"{API_BASE_URL}/auth/register", json={
                "username": USERNAME,
                "email": EMAIL,
                "password": PASSWORD
            })
            if resp.status_code == 200:
                print("Registration successful.")
            else:
                print(f"Registration info: {resp.status_code} (User might already exist)")
        except Exception as e:
            print(f"Registration error: {e}")

        # 2. Login
        print("\nLogging in...")
        resp = await client.post(f"{API_BASE_URL}/auth/login", data={
            "username": USERNAME,
            "password": PASSWORD
        })
        
        if resp.status_code != 200:
            print(f"Login failed: {resp.text}")
            return
            
        token = resp.json()["access_token"]
        print(f"Login successful. Token: {token[:10]}...")
        
        # 3. Chat Stream
        print("\nSending Chat Request...")
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "message": "Hello, this is a test message. Please verify connectivity.",
            "stream": True
        }
        
        try:
            async with client.stream("POST", f"{API_BASE_URL}/api/chat", json=payload, headers=headers, timeout=60.0) as response:
                print(f"Response Status: {response.status_code}")
                
                if response.status_code != 200:
                    print(f"Error Response: {await response.aread()}")
                    return

                print("--- Stream Started ---")
                async for line in response.aiter_lines():
                    if line.strip():
                        print(f"Received: {line}")
                print("--- Stream Ended ---")
                
        except Exception as e:
            print(f"Stream error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
