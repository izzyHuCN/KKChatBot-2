from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from .config import settings
from .database import engine, Base
# from .middleware.rate_limit import rate_limit_middleware
from .api import chat, auth

# --- 生命周期管理器 ---
# 用于在应用启动和关闭时执行特定逻辑
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时：自动创建数据库表结构
    # 如果使用 Alembic 进行迁移，这里可以移除
    Base.metadata.create_all(bind=engine)
    print("Database tables created")
    yield
    # 关闭时：可以在这里释放资源（如数据库连接池、Redis 连接等）
    print("Shutting down")

# --- 初始化 FastAPI 应用 ---
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# --- CORS 配置 (跨域资源共享) ---
# 允许前端 (通常是 5173 端口) 访问后端 API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 警告：生产环境应限制为具体的前端域名，如 ["https://your-domain.com"]
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有 HTTP 方法 (GET, POST, etc.)
    allow_headers=["*"],  # 允许所有 Header (Authorization, Content-Type, etc.)
)

# --- 静态文件挂载 ---
# 挂载 uploads 目录，使用户上传的图片/文件可以通过 URL 访问
# 例如: http://localhost:8000/uploads/example.jpg
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# 限流中间件已在各个路由中单独应用，这里注释掉全局应用
# app = rate_limit_middleware(app)

# --- 注册路由模块 ---
# auth.router: 处理登录、注册、Token 刷新
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
# chat.router: 处理对话、语音、WebSocket
app.include_router(chat.router, prefix="/api", tags=["chat"])

@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION
    }

@app.get("/health")
async def health_check():
    """健康检查接口，用于负载均衡或监控"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    # 启动开发服务器
    # reload=True 表示代码变动时自动重启
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
