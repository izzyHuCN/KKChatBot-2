import httpx
import asyncio
import json

url = "http://localhost/v1/chat-messages"
headers = {
    "Authorization": "Bearer app-eruXC70ovNO9aRhbbrNUiGYm",
    "Content-Type": "application/json"
}
data = {
    "inputs": {},
    "query": "Hello",
    "response_mode": "streaming",
    "conversation_id": "",
    "user": "test-user"
}

async def test_httpx():
    print(f"Sending POST to {url} using httpx...")
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=data)
            print(f"Status Code: {response.status_code}")
            print("Response Headers:")
            print(response.headers)
            print("Response Text (first 500 chars):")
            print(response.text[:500])
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_httpx())
