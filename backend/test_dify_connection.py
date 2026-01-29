#!/usr/bin/env python3
"""
测试Docker网络中的Dify连接
"""
import httpx
import json

def test_dify_connections():
    """测试不同的Dify连接方式"""
    
    # 测试配置
    api_key = "app-DJRsIxTBbLz5pkazjcjSkG20"
    test_endpoints = [
        "http://localhost/v1/chat-messages",
        "http://localhost:5001/v1/chat-messages",
        "http://172.18.0.7:5001/v1/chat-messages",
        "http://docker-api-1:5001/v1/chat-messages"
    ]
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "inputs": {},
        "query": "Hello, are you online?",
        "response_mode": "streaming",
        "conversation_id": "",
        "user": "test-user"
    }
    
    print("🧪 测试Dify连接...")
    print(f"API Key: {api_key[:20]}...")
    print()
    
    for endpoint in test_endpoints:
        print(f"测试端点: {endpoint}")
        try:
            response = httpx.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            print(f"状态码: {response.status_code}")
            if response.status_code == 200:
                print("✅ 连接成功！")
                # 尝试解析响应
                try:
                    lines = response.text.strip().split('\n')
                    for line in lines:
                        if line.startswith('data: '):
                            data = json.loads(line[6:])
                            if 'answer' in data:
                                print(f"响应: {data['answer']}")
                                break
                except:
                    print(f"原始响应: {response.text[:100]}...")
            else:
                print(f"❌ 连接失败: {response.text[:100]}...")
                
        except Exception as e:
            print(f"❌ 连接错误: {str(e)}")
        
        print("-" * 50)
        print()

if __name__ == "__main__":
    test_dify_connections()