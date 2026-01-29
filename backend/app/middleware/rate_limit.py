import redis
from fastapi import Request, HTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from ..config import settings
import logging

logger = logging.getLogger(__name__)

# 尝试连接Redis，如果失败则使用内存存储
try:
    redis_client = redis.from_url(settings.REDIS_URL)
    # 测试Redis连接
    redis_client.ping()
    storage_uri = settings.REDIS_URL
    logger.info("Redis connection successful")
except Exception as e:
    logger.warning(f"Redis connection failed: {e}, using memory storage")
    storage_uri = "memory://"

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=storage_uri,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"]
)

def rate_limit_middleware(app):
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    return app