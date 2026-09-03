"""LearnFlow 后端 - 最小化版本（用于验证部署管道）"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title="LearnFlow API",
    version="1.0.0",
    description="AI驱动的游戏化学习平台"
)

# CORS 配置
allowed_origins = os.getenv("ALLOWED_ORIGINS", "[\"*\"]")
try:
    import json
    allowed_origins_list = json.loads(allowed_origins)
except:
    allowed_origins_list = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 健康检查（最重要！CloudBase 用它检测应用是否启动成功）
@app.get("/health")
async def health():
    logger.info("✅ 健康检查被调用")
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "production")
    }

# 根路径
@app.get("/")
async def root():
    logger.info("📍 根路径被访问")
    return {
        "app": "LearnFlow API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "message": "🎓 让学习成为享受"
    }

# 测试登录端点（模拟）
@app.post("/api/v1/auth/login")
async def login():
    logger.info("🔐 登录请求（测试模式）")
    return {
        "access_token": "test-token-12345",
        "token_type": "bearer",
        "user": {
            "username": "testuser",
            "email": "<EMAIL_REMOVED>",
            "role": "student"
        }
    }

# 启动事件
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 LearnFlow 后端启动成功！")
    logger.info(f"🌍 环境: {os.getenv('ENVIRONMENT', 'production')}")
    logger.info(f"📍 端口: {os.getenv('PORT', '8000')}")

# 关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 LearnFlow 后端正在关闭...")
