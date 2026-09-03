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
ENV JWT_SECRET_KEY=learnflow-production-jwt-secret-key-2026-06
ENV REDIS_URL=redis://localhost:6379/0
ENV SEED_ADMIN_PASSWORD=Admin123!
ENV SEED_TEACHER_PASSWORD=Teacher123!
ENV SEED_STUDENT_PASSWORD=Student123!
ENV SEED_PARENT_PASSWORD=Parent123!

EXPOSE 80

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80", "--loop", "asyncio"]
