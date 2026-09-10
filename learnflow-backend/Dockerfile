# 使用完整 Python 镜像以避免 greenlet / 编译依赖问题
FROM python:3.12

WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖（腾讯云镜像加速）
RUN pip install --no-cache-dir \
    -i http://mirrors.cloud.tencent.com/pypi/simple \
    --trusted-host mirrors.cloud.tencent.com \
    --upgrade pip && \
    pip install --no-cache-dir \
    -i http://mirrors.cloud.tencent.com/pypi/simple \
    --trusted-host mirrors.cloud.tencent.com \
    -r requirements.txt && \
    python -c "import greenlet; print('greenlet', greenlet.__version__)" && \
    python -c "import sqlalchemy; print('sqlalchemy', sqlalchemy.__version__)"

# 复制应用代码与数据库
COPY app/ ./app/
COPY learnflow.db ./

ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production
ENV PORT=80
ENV DATABASE_URL=sqlite+aiosqlite:///./learnflow.db
ENV REDIS_URL=redis://localhost:6379/0

# JWT_SECRET_KEY、数据库凭据和生产 CORS 来源必须在部署平台以密钥/环境变量注入。
# 应用会拒绝缺少 JWT_SECRET_KEY 的 production 配置，也不会自动创建演示账号。

EXPOSE 80

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80", "--loop", "asyncio"]
