import requests
import json

url = "http://localhost/v1/chat-messages"
headers = {
    "Authorization": "Bearer app-eruXC70ovNO9aRhbbrNUiGYm",
    "Content-Type": "application/json"
}
data = {
    "inputs": {},
    "query": "Hello",
    "response_mode": "blocking",
    "conversation_id": "",
    "user": "test-user"
}

try:
    print(f"Sending POST to {url}...")
    response = requests.post(url, headers=headers, json=data)
    print(f"Status Code: {response.status_code}")
    print("Response Headers:")
    print(response.headers)
    print("Response Body:")
    print(response.text)
except Exception as e:
    print(f"Error: {e}")
