# 🎓 LearnFlow — AI 驱动的游戏化学习平台

> **让学习本身成为内在奖励** — 通过心流与放松引导提升长期投入

基于简·麦格尼格尔《游戏改变世界》理论、Csikszentmihalyi 心流理论、Deci & Ryan 自我决定理论、多巴胺期待机制、α波脑态优化和中国班级宠物实践经验。

---

## 🎯 核心设计原理

| 理论 | 系统实现 |
|------|---------|
| **心流理论** (Csikszentmihalyi) | DDA 动态难度调节，维持成功率 75-85% |
| **自我决定理论** (SDT) | 自主选择路径、清晰掌握度、班级归属 |
| **多巴胺期待机制** | ≤3秒即时微反馈 + "下一步预告" |
| **失败安全化** | 错题诊断 + 可重复练习 + 宠物"恢复体力" |
| **α波与放松** | 柔和UI/音乐、呼吸引导、放松型提示语 |
| **神经可塑性** | 间隔复习 + 身份强化（长期进步档案） |

## 🏗️ 项目结构

```
learnflow/
├── backend/                     # Python FastAPI 后端
│   ├── app/
│   │   ├── api/                 # API 路由
│   │   │   ├── auth.py          # 认证（JWT登录/注册/刷新）
│   │   │   ├── student.py       # 学生端（仪表盘/DDA/反馈/宠物）
│   │   │   ├── teacher.py       # 教师端（班级/AI建议/任务）
│   │   │   ├── parent.py        # 家长端（摘要/同意/导出）
│   │   │   └── admin.py         # 管理端（审核/文案/规则）
│   │   ├── core/                # 核心配置
│   │   │   ├── config.py        # 全局配置
│   │   │   ├── database.py      # 数据库 + 异步会话
│   │   │   └── security.py      # JWT + 密码哈希
│   │   ├── models/              # SQLAlchemy 模型
│   │   │   ├── user.py          # 用户（学生/教师/家长/管理员）
│   │   │   ├── pet.py           # 宠物四维模型
│   │   │   ├── task.py          # 任务/答题/技能画像
│   │   │   └── consent.py       # 同意/告警/文案库
│   │   ├── services/            # 核心业务逻辑
│   │   │   ├── dda.py           # DDA动态难度调节引擎
│   │   │   ├── pet_service.py   # 宠物四维属性更新
│   │   │   ├── feedback_service.py  # 微反馈生成 + 文案库
│   │   │   ├── spaced_repetition.py # 间隔复习（艾宾浩斯）
│   │   │   └── risk_monitor.py  # 风险监控（成瘾检测）
│   │   └── main.py              # FastAPI 应用入口
│   ├── seed.py                  # 种子数据
│   └── requirements.txt
│
├── frontend/                    # React + TypeScript 前端
│   ├── src/
│   │   ├── pages/
│   │   │   ├── LoginPage.tsx         # 登录页
│   │   │   ├── StudentDashboard.tsx  # 学生仪表盘
│   │   │   ├── LearningSession.tsx   # 学习任务流
│   │   │   ├── TeacherDashboard.tsx  # 教师仪表盘
│   │   │   ├── ParentSummary.tsx     # 家长摘要
│   │   │   └── AdminPanel.tsx        # 管理面板
│   │   ├── components/
│   │   │   ├── pet/PetCard.tsx       # 宠物四维卡片
│   │   │   └── common/Layout.tsx     # 导航布局
│   │   ├── services/api.ts          # API 客户端
│   │   ├── styles/index.css         # 全局样式
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── index.html
│   ├── package.json
│   └── vite.config.ts
│
└── README.md
```

## 🚀 快速启动

### 后端

```bash
cd backend
pip install -r requirements.txt
python seed.py              # 初始化数据库和种子数据
uvicorn app.main:app --reload
```

API 文档：http://localhost:8000/docs

### 前端

```bash
cd frontend
npm install
npm run dev
```

前端：http://localhost:5173

### 演示账号

运行 `python seed.py` 初始化数据库和种子数据。账号密码通过环境变量注入：

```bash
# 可选：设置种子密码（不设置将自动生成随机密码）
export SEED_ADMIN_PASSWORD="your_admin_password"
export SEED_TEACHER_PASSWORD="your_teacher_password"
export SEED_STUDENT_PASSWORD="your_student_password"
export SEED_PARENT_PASSWORD="your_parent_password"
```

默认演示邮箱：
- 🧑‍🎓 学生: student@learnflow.com
- 👩‍🏫 教师: teacher@learnflow.com
- 👨‍👧 家长: parent@learnflow.com
- 🛡️ 管理员: admin@learnflow.com

## 🔑 核心功能

### 1. DDA 动态难度调节
基于最近 10 题表现自动调整难度，维持成功率 75-85%（心流通道）。

### 2. 宠物四维模型
不是积分容器，而是学习维度的可视化镜像：
- 🧠 理解力 — 正确率↑、少用提示
- ❤️ 坚持力 — 做困难题、重试错题
- 💡 创造力 — 独特解法
- 🤝 协作力 — 帮助同学

### 3. 即时微反馈
提交后 2-3 秒内返回诊断/引导/确认，所有文案可管理、可审计。

### 4. 放松引导模式
可选的 α 波友好界面：呼吸动画、柔和音乐、正向引导语（透明、需同意）。

### 5. 风险监控
日均使用超时、夜间使用、表现下降、挑战回避等自动告警。

## 🛡️ 伦理设计

- ✅ 所有放松引导功能需显式同意，可随时关闭
- ✅ 提示语标注来源，版本可追溯
- ✅ 积分仅用于虚拟进度，不兑换实物
- ✅ 失败不扣分，触发"恢复体力"而非惩罚
- ✅ 连续学习 90 分钟强制休息提醒

## 📋 技术栈

| 层 | 技术 |
|----|------|
| 后端框架 | FastAPI (Python 3.12+) |
| 数据库 | PostgreSQL + SQLAlchemy 2.0 (async) |
| 缓存 | Redis |
| 前端 | React 18 + TypeScript + Vite |
| 图表 | Recharts |
| 动画 | Framer Motion |
| 认证 | JWT (python-jose) |

---

> 本系统基于项目内部的 MVP 功能规格书构建。教育的真正竞争对手不是游戏，而是教育对人性的误解。
