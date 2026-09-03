# CloudBase 云托管部署 - 完整指南

## 问题：SERVICE_VERSION_NOT_FOUND

### 含义
服务已创建，但没有成功部署的版本。

---

## 解决方案 A：部署最小化版本（推荐，99% 能成功）

### 目的
先部署一个**不依赖数据库**的最小化版本，验证部署管道是否能工作。

### A1. 准备最小化应用

1. 打开 `H:\learnflow-backend\app\main.py`
2. **临时替换**为以下内容（先备份原文件）：

```python
"""LearnFlow 后端 - 最小化版本（用于验证部署）"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import logging

# 配置日志（输出到 stdout，CloudBase 会收集）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(title="LearnFlow API", version="1.0.0")

# CORS 配置（允许所有来源，先让前端能访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 健康检查（最重要！CloudBase 用它检测应用是否启动成功）
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
        "message": "🎓 后端已启动！"
    }

# 模拟登录（用于测试前端能否连上后端）
@app.post("/api/v1/auth/login")
async def login():
    logger.info("🔐 登录请求（测试模式）")
    return {
        "access_token": "test-token-12345",
        "token_type": "bearer"
    }

# 启动事件
@app.on_event("startup")
async def startup_event():
    port = os.getenv("PORT", "8000")
    logger.info(f"🚀 LearnFlow 后端启动成功！监听端口：{port}")
    logger.info(f"🌍 环境：{os.getenv('ENVIRONMENT', 'production')}")
    logger.info(f"📖 API 文档：http://0.0.0.0:{port}/docs")

# 关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 LearnFlow 后端正在关闭...")
```

### A2. 准备最小化 Dockerfile

1. 打开 `H:\learnflow-backend\Dockerfile`
2. **替换为**以下内容：

```dockerfile
FROM python:3.12-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 只安装最小依赖（FastAPI + Uvicorn）
RUN pip install --no-cache-dir fastapi uvicorn

# 复制应用代码
COPY app/ ./app/

# 确保 app 是一个 Python 包
RUN mkdir -p /app/app && touch /app/app/__init__.py

# 环境变量
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

# 暴露端口（CloudBase 会使用 PORT 环境变量）
EXPOSE 8000

# 健康检查（CloudBase 用这个检测应用是否健康）
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# 启动命令（使用 $PORT 环境变量，CloudBase 会设置这个变量）
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

### A3. 打包代码

1. 打开 PowerShell，执行：
   ```powershell
   cd H:\learnflow-backend
   Compress-Archive -Path * -DestinationPath learnflow-minimal.zip -Force
   ```

2. 等待打包完成（会生成 `learnflow-minimal.zip` 文件）

### A4. 通过 CloudBase 控制台部署

1. 打开浏览器，访问：https://console.cloud.tencent.com/tcb
2. 选择环境：`learnflow-d5gapot1tc7d4debd`
3. 点击左侧 **云托管**
4. 找到 `learnflow-api` 服务，点击 **"新建版本"**
5. 配置：
   - **版本名称**：`minimal-v1`
   - **部署方式**：选择 **"源码部署"**
   - **代码包**：上传 `learnflow-minimal.zip`
   - **端口**：`8000`
   - **环境变量**：暂时不填（最小化版本不需要数据库）
6. 点击 **"部署"**
7. 等待部署完成（约 3-5 分钟）

### A5. 验证部署成功

部署完成后：

1. 在 CloudBase 控制台，找到新版本的 **访问地址**（类似 `https://learnflow-api-xxx.sh.run.tcloudbase.com`）
2. 打开浏览器，访问：`https://<访问地址>/health`
3. **期望响应**：
   ```json
   {"status":"healthy","version":"1.0.0"}
   ```
4. 如果看到这个响应，说明**部署管道正常工作**！

---

## 解决方案 B：查看部署日志（精准修复）

### 目的
查看失败原因，精准修复问题。

### B1. 查看日志步骤

1. 打开 CloudBase 控制台
2. 进入 **云托管** → `learnflow-api`
3. 点击 **版本列表**
4. 找到失败版本，点击 **"查看日志"**
5. **复制所有红色错误信息**

### B2. 常见错误及修复

| 错误 | 原因 | 修复 |
|------|------|------|
| `port 8000 is already in use` | 端口冲突 | 确保 `CMD` 中使用 `$PORT` 变量 |
| `ModuleNotFoundError: No module named 'fastapi'` | 依赖未安装 | 检查 `Dockerfile` 中的 `pip install` 命令 |
| `database connection failed` | 数据库不可用 | 使用我的修复代码（数据库不可用时应用仍能启动）|
| `health check failed` | 健康检查失败 | 确保 `/health` 端点返回 200 |

---

## 解决方案 C：配置环境变量（完整版部署）

### 目的
部署完整版本（带数据库）时，需要配置环境变量。

### C1. 必需的环境变量

在 CloudBase 控制台创建版本时，配置以下环境变量：

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `ENVIRONMENT` | `production` | 生产环境 |
| `DEBUG` | `false` | 关闭调试 |
| `DATABASE_URL` | `<DB_CONNECTION_REMOVED> | MySQL 连接 |
| `REDIS_URL` | `<DB_CONNECTION_REMOVED> | Redis 连接 |
| `JWT_SECRET` | `09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7` | JWT 密钥 |
| `ALLOWED_ORIGINS` | `["https://learnflow-frontend-9gawx5qy1c958c1f-1256129125.tcloudbaseapp.com"]` | 允许的前端域名 |

### C2. 注意事项

1. **数据库连接**：确保 MySQL 和 Redis 已创建并可访问
2. **JWT 密钥**：生产环境务必使用强密钥（我已经生成了一个）
3. **CORS**：`ALLOWED_ORIGINS` 必须包含前端域名，否则前端无法调用 API

---

## 部署后验证

### 1. 测试健康检查

```bash
curl https://<your-cloud-run-url>/health
```

**期望响应**：
```json
{"status":"healthy"}
```

### 2. 测试登录

```bash
curl -X POST https://<your-cloud-run-url>/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test"}'
```

**期望响应**：
```json
{"access_token":"...","token_type":"bearer"}
```

### 3. 查看 API 文档

访问：`https://<your-cloud-run-url>/docs`

---

## 故障排查

### 问题 1：部署失败，如何查看日志？

**解决**：
1. CloudBase 控制台 → 云托管 → `learnflow-api`
2. 版本列表 → 点击失败版本
3. 点击 **"查看日志"** 按钮

### 问题 2：应用启动后立即崩溃？

**可能原因**：
- `main.py` 中有语法错误
- 依赖未安装或版本不兼容
- 端口绑定错误（没有监听 `$PORT`）

**解决**：
1. 使用最小化版本（不依赖数据库）先验证管道
2. 查看 CloudBase 日志

### 问题 3：前端无法调用后端 API？

**可能原因**：
- CORS 配置错误
- 后端未启动成功
- 前端配置的 API 地址错误

**解决**：
1. 检查后端 `/health` 是否返回 200
2. 检查 CORS 配置（`ALLOWED_ORIGINS`）
3. 检查前端 `.env.production` 中的 `VITE_API_URL`

---

## 快速联系

如果部署遇到问题，请：
1. **截取 CloudBase 控制台错误截图**
2. **复制错误日志文本**
3. **发给我**，我会帮您分析

---

## 下一步

1. **先部署最小化版本**（验证部署管道）
2. **查看部署日志**（如果失败）
3. **部署完整版本**（配置环境变量）
4. **测试登录功能**
5. **如果还有问题，把错误信息发给我**

---

**祝您部署顺利！🎉**
