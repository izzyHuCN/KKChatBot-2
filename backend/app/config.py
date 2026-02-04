from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # --- 应用基础配置 ---
    APP_NAME: str = "AI Chat Demo"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True # 开发模式下开启，生产环境请设为 False

    # --- 数据库配置 ---
    # 默认使用 SQLite 文件数据库，无需安装额外服务
    # 生产环境建议切换到 PostgreSQL: "postgresql://user:password@localhost/dbname"
    # 注意：如果使用 MySQL，需要安装 pymysql 并在 URL 中指定 mysql+pymysql://
    DATABASE_URL: str = "sqlite:///./ai_chat.db"

    # --- Redis 配置 ---
    # 用于 API 限流和 Session 缓存 (当前代码主要用于限流)
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- JWT 认证配置 ---
    # SECRET_KEY 必须在生产环境中修改为随机强密码！
    # 可以使用 `openssl rand -hex 32` 生成
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30 # Token 过期时间

    # --- Dify 配置 (已弃用) ---
    # 早期版本使用 Dify 作为 Agent 编排，现已迁移到直连 LLM 模式
    DIFY_API_KEY: str = ""
    DIFY_BASE_URL: str = ""

    # --- LLM 配置 (OpenAI 兼容协议) ---
    # 目前对接的是阿里云通义千问 (Qwen-VL-Max)，支持多模态
    # 如果要切换其他模型（如 DeepSeek, GPT-4），只需修改 BASE_URL 和 API_KEY
    LLM_API_KEY: str = "" 
    LLM_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1" 
    LLM_MODEL_NAME: str = "qwen-vl-max"

    # --- 阿里云智能语音交互 (NLS) 配置 ---
    # 用于 TTS (Text-to-Speech) 服务
    # 需在阿里云控制台开通 NLS 服务并获取 AppKey
    ALIYUN_NLS_APP_KEY: str = ""
    ALIYUN_ACCESS_KEY_ID: str = ""
    ALIYUN_ACCESS_KEY_SECRET: str = ""

    # --- 限流配置 ---
    # 每个用户每分钟允许的最大请求数
    RATE_LIMIT_PER_MINUTE: int = 30

    class Config:
        # 优先读取 .env 文件中的环境变量
        # 环境变量名不区分大小写
        env_file = ".env"


settings = Settings()