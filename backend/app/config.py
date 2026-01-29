from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "AI Chat Demo"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # 数据库配置 - 默认使用SQLite简化测试
    DATABASE_URL: str = "sqlite:///./ai_chat.db"

    # Redis配置（用于限流和会话）
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT配置
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Dify配置 (已弃用，保留作为参考)
    DIFY_API_KEY: str = ""
    DIFY_BASE_URL: str = "http://127.0.0.1/v1"  # Dify本地地址

    # Direct LLM 配置 (OpenAI Compatible)
    # 默认值留空或填入占位符，等待用户配置
    LLM_API_KEY: str = "" 
    LLM_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1" 
    LLM_MODEL_NAME: str = "qwen-vl-max"

    # 阿里云智能语音交互 (NLS) 配置
    ALIYUN_NLS_APP_KEY: str = ""
    ALIYUN_ACCESS_KEY_ID: str = ""
    ALIYUN_ACCESS_KEY_SECRET: str = ""

    # 限流配置
    RATE_LIMIT_PER_MINUTE: int = 30

    class Config:
        env_file = ".env"


settings = Settings()