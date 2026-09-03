# CloudBase 云托管部署指南

## 问题：SERVICE_VERSION_NOT_FOUND

### 原因
服务已创建，但没有成功部署的版本。

### 解决方案

#### 方案 A：使用源码部署（推荐，不需要本地 Docker）

1. **准备代码包**
   - 打包以下文件：
     - `app/` 目录（全部）
     - `requirements.txt`
     - `Dockerfile`
     - `.dockerignore`
   
2. **上传到 CloudBase 控制台**
   - 打开 [CloudBase 控制台](https://console.cloud.tencent.com/tcb)
   - 进入 **云托管** → `learnflow-api`
   - 点击 **新建版本**
   - 选择 **源码部署**
   - 上传 ZIP 包
   - 配置环境变量（见下方）
   - 点击 **部署**

#### 方案 B：使用我的最小化版本（先验证管道）

1. **使用最小化应用**
   - 将 `app/main_cloudbase.py` 重命名为 `app/main.py`
   - 使用 `Dockerfile.minimal`
   
2. **部署**
   - 这个版本不依赖数据库，99% 能启动成功
   - 用于验证部署管道是否正常

---

## 环境变量配置

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `ENVIRONMENT` | `production` | 生产环境 |
| `DEBUG` | `false` | 关闭调试 |
| `DATABASE_URL` | `<DB_CONNECTION_REMOVED> | MySQL 连接 |
| `REDIS_URL` | `<DB_CONNECTION_REMOVED> | Redis 连接 |
| `JWT_SECRET` | `09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7` | JWT 密钥 |
| `ALLOWED_ORIGINS` | `["https://learnflow-frontend-9gawx5qy1c958c1f-1256129125.tcloudbaseapp.com"]` | 允许的前端域名 |

---

## 部署后验证

1. **测试健康检查**
   ```bash
   curl https://<your-cloud-run-url>/health
   ```
   
   期望响应：
   ```json
   {"status":"healthy"}
   ```

2. **测试登录**
   ```bash
   curl -X POST https://<your-cloud-run-url>/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username":"test","password":"test"}'
   ```

3. **查看 API 文档**
   访问：https://<your-cloud-run-url>/docs

---

## 常见问题

### Q1：部署失败，如何查看日志？
A：CloudBase 控制台 → 云托管 → 服务名 → 版本列表 → 点击失败版本 → 查看日志

### Q2：应用启动后立即退出？
A：检查：
- Dockerfile 的 CMD 命令是否正确
- 应用是否监听 `$PORT` 或 `0.0.0.0:8000`
- 依赖是否全部安装

### Q3：健康检查失败？
A：确保 `/health` 端点返回 200 状态码

---

## 快速联系

如果部署遇到问题，请：
1. 截取 CloudBase 控制台错误截图
2. 复制错误日志文本
3. 发给我，我会帮您分析
