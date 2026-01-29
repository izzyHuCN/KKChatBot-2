import httpx
import asyncio
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

url = "http://127.0.0.1/v1/chat-messages"
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

async def test_httpx_streaming():
    print(f"Sending POST to {url} using httpx with streaming...")
    try:
        async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
            async with client.stream('POST', url, headers=headers, json=data) as response:
                print(f"Status Code: {response.status_code}")
                print("Response Headers:")
                print(response.headers)
                
                if response.status_code != 200:
                    print("Error response body:")
                    print(await response.read())
                    return

                print("Starting stream processing...")
                async for line in response.aiter_lines():
                    if line:
                        print(f"Received line: {line}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_httpx_streaming())
