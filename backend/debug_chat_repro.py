import requests
import json

url = "http://127.0.0.1:8000/api/chat"
headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNzY5NzMyOTgxfQ.lpdYYQODZsQY8MXWw2NH8kVHqiMbElbJnM_Ydm5iSpo",
    "Content-Type": "application/json"
}

data = {
    "message": "The weather today is nice",
    "stream": False
}

print("Sending request 1...")
response = requests.post(url, json=data, headers=headers, stream=True)
print("Response 1:")
for line in response.iter_lines():
    if line:
        print(line.decode('utf-8'))

print("\n" + "="*20 + "\n")

data2 = {
    "message": "What is 1+1?",
    "stream": False
}
print("Sending request 2...")
response = requests.post(url, json=data2, headers=headers, stream=True)
print("Response 2:")
for line in response.iter_lines():
    if line:
        print(line.decode('utf-8'))
