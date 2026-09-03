"""CloudBase 云托管 - 最小化工作版本"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
import sys

# 配置日志（输出到 stdout，CloudBase 会收集）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("learnflow")

# 创建应用
app = FastAPI(title="LearnFlow API", version="1.0.0")

# CORS（允许所有来源，先让前端能访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 健康检查（CloudBase 用它检测应用是否启动成功）
@app.get("/health")
async def health():
    logger.info("✅ 健康检查被调用")
    return {"status": "healthy", "version": "1.0.0"}

# 根路径
@app.get("/")
async def root():
    logger.info("📍 根路径被访问")
    return {
        "app": "LearnFlow API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "message": "后端已启动！"
    }

# 模拟登录（用于测试前端能否连上后端）
@app.post("/api/v1/auth/login")
async def login():
    logger.info("🔐 登录请求（测试模式）")
    return {
        "access_token": "test-token-123",
        "token_type": "bearer"
    }

# 启动事件
@app.on_event("startup")
async def startup():
    port = os.getenv("PORT", "8000")
    logger.info(f"🚀 LearnFlow 后端启动成功！监听端口：{port}")
    logger.info(f"🌍 环境：{os.getenv('ENVIRONMENT', 'production')}")
    logger.info(f"📍 访问：http://0.0.0.0:{port}")
    logger.info(f"📖 API 文档：http://0.0.0.0:{port}/docs")

# 关闭事件
@app.on_event("shutdown")
async def shutdown():
    logger.info("🛑 LearnFlow 后端正在关闭...")
