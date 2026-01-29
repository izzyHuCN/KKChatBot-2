import time
from collections import defaultdict
from fastapi import Request, HTTPException
from ..config import settings

# 简单的内存限流器
class SimpleRateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)
        self.rate_limit = settings.RATE_LIMIT_PER_MINUTE
        self.time_window = 60  # 60 seconds
    
    def is_allowed(self, key: str) -> bool:
        now = time.time()
        # 清理过期的请求记录
        self.requests[key] = [req_time for req_time in self.requests[key] if now - req_time < self.time_window]
        
        # 检查是否超过限流
        if len(self.requests[key]) >= self.rate_limit:
            return False
        
        # 记录当前请求
        self.requests[key].append(now)
        return True

rate_limiter = SimpleRateLimiter()

def check_rate_limit(request: Request):
    """检查限流 - 使用客户端IP作为限流键"""
    client_ip = request.client.host if request.client else "unknown"
    
    if not rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later."
        )
    
    return True