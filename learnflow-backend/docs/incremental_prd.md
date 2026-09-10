# LearnFlow 增量 PRD（基于完整功能实现方案 v1.0.0）

> **版本**: 增量 1.0.0 | **日期**: 2026-06-20  
> **后端**: `H:\learnflow-backend` | **前端**: `H:\learnflow-frontend`

---

## 1. 项目目标与本次迭代范围

### 1.1 项目目标

LearnFlow 是一个 AI 驱动的游戏化学习成瘾实验平台，目标是通过 76 个游戏化成瘾引擎、28 种学习方法引擎、7 个核心算法引擎，为学生、教师、家长、管理员四端提供数据驱动的学习体验。

> 注：PRD 标题/概述声称 76 个游戏化引擎，但其 §2.3 表格逐项求和实为 69，二者自相矛盾；经三层复算（registry_fingerprint、scan_mechanism_landing、verify_counts），唯一登记机制数为 54（LF-M01…LF-M54），注册表指纹 `ee1a49be5732`，运行时落地 54/54（orphan=0）。论文主表述一律采用 54，76 仅作 PRD 历史声称保留；学习方法 28（LF-L01…LF-L28）、技能树节点 16 以代码为准。

**本次迭代目标**：
1. **补齐数据闭环**：确保新用户注册/演示账号初始化时自动生成宠物、技能画像、默认同意设置，避免空数据导致功能不可用。
2. **修复运行阻塞**：解决 `seed.py` 无法导入 `AsyncSessionLocal`、教师 AI 端点运行时错误、测试依赖版本冲突等问题。
3. **整合核心算法到业务流**：将 BKT、85% 规则、间隔复习、风险监控真正接入 `/student/next-task` 和 `/student/submit-answer`。
4. **扩展前端覆盖**：将后端已实现的连胜、排行榜、战队、学习技能树、宝箱等能力通过新增前端页面暴露给用户。

### 1.2 原始需求复述

> 基于《LearnFlow_完整功能实现方案.md》的 12 章内容，完成后端与前端的增量开发，使平台从“引擎/接口就绪”升级为“端到端可用”。

---

## 2. 已完整实现功能清单（按模块）

### 2.1 认证与社交登录（`app/api/auth.py`）

| 端点 | 状态 | 说明 |
|------|------|------|
| `POST /api/v1/auth/register` | 已实现 | 含密码强度校验（8 位+大小写+数字） |
| `POST /api/v1/auth/login` | 已实现 | form-urlencoded 标准登录 |
| `POST /api/v1/auth/login/json` | 已实现 | JSON 登录 |
| `POST /api/v1/auth/login/oauth` | 已实现 | QQ/微信 OAuth 自动注册/登录（模拟 UID） |
| `POST /api/v1/auth/refresh` | 已实现 | 刷新令牌 |
| `GET /api/v1/auth/me` | 已实现 | 当前用户信息 |
| `GET /api/v1/auth/role` | 已实现 | 当前角色 |
| `POST /api/v1/auth/change-role` | 已实现 | 返回 403 角色锁定 |

### 2.2 核心算法引擎（`app/services/`）

| 引擎 | 文件 | 状态 | 说明 |
|------|------|------|------|
| BKT 贝叶斯知识追踪 | `knowledge_tracing.py` | 已实现 | 四参数模型，含自适应调参 |
| DDA 动态难度调整 | `dda.py` | 已实现 | 窗口成功率 + 心流维持 |
| 85% 规则 / Elo / FSRS / 心流通道 | `optimal_difficulty.py` | 已实现 | 数学公式完整 |
| 风险监控 | `risk_monitor.py` | 已实现 | 绿/黄/红三级评估 |
| 反成瘾合规 | `anti_addiction_compliance.py` | 已实现 | 连续学习上限检查 |
| 间隔重复 | `spaced_repetition.py` | 已实现 | 标准间隔序列 |
| 宠物服务 | `pet_service.py` | 已实现 | 四维属性更新与进化 |

### 2.3 游戏化成瘾引擎（76 个）

| 分类 | 文件 | 引擎数量 | 状态 |
|------|------|----------|------|
| 正向成瘾引擎 | `positive_addiction_engine.py` | 7 | 已实现 |
| 深度成瘾引擎 | `deep_addiction_engine.py` | 10 | 已实现 |
| UI 成瘾引擎 | `ux_addiction_engine.py` | 12 | 已实现 |
| 社交成瘾引擎 | `social_addiction_engine.py` | 8 | 已实现 |
| 多邻国式成瘾 | `duolingo_addiction_engine.py` | 8 | 已实现 |
| 竞技排位引擎 | `team_competition_engine.py` | 7 | 已实现 |
| 新增成瘾引擎 v3 | `addiction_engine_v3.py` | 5 | 已实现 |
| 游戏化激励服务 | `gamification_service.py` | 12+ | 已实现 |

> 注：服务层代码完整，但**大部分尚未暴露为 API 或接入前端**。
> 口径说明：本节表格逐项求和为 69（7+10+12+8+8+7+5+12），与标题声称的 76 自相矛盾；登记注册表唯一机制数为 54（LF-M01…LF-M54），详见 §1.1 注。

### 2.4 学习方法引擎（28 种）

| 文件 | 方法数 | 状态 |
|------|--------|------|
| `learning_methods_engine.py` | 18 | 已实现（含记忆宫殿、费曼、元认知等） |
| `advanced_methods_engine.py` | 5 | 已实现 |
| `learning_methods_engine_v3.py` | 5 | 已实现 |
| `meta_learning_skilltree.py` | 16 技能树 | 已实现 |

### 2.5 后端 API 端点（45+）

| 模块 | 已实现端点 | 备注 |
|------|------------|------|
| 学生端 `/student` | dashboard、next-task、submit-answer、recovery-choice、pet、relaxation-guide、consent、health-check | 核心流完整 |
| 教师端 `/teacher` | classroom、student/{id}、suggestions、tasks、alerts、alerts/{id}/resolve、AI 分析端点 | AI 端点有运行时 bug |
| 家长端 `/parent` | child/{id}/summary、consent-settings/{id}、consent、child/{id}/export | 完整 |
| 管理端 `/admin` | pending-tasks、review-task、feedback-scripts、alert-rules、stats | 完整 |

### 2.6 数据库模型（`app/models/`）

| 模型 | 状态 | 说明 |
|------|------|------|
| `User` | 已实现 | 四角色、家长绑定、同意 JSON |
| `PetProfile` | 已实现 | 四维属性、视觉状态 |
| `Task / Attempt / SpacedReview / StudentSkillProfile` | 已实现 | 题目、答题、复习、技能画像 |
| `ConsentRecord / Alert / FeedbackScript` | 已实现 | 同意记录、风险告警、文案库 |

### 2.7 前端界面（`H:\learnflow-frontend\src`）

| 页面 | 状态 | 说明 |
|------|------|------|
| `LoginPage.tsx` | 已实现 | 4 角色选择、登录/注册、OAuth 模拟、演示账号 |
| `StudentDashboard.tsx` | 已实现 | 宠物、今日统计、技能画像、今日目标、放松模式 |
| `LearningSession.tsx` | 已实现 | 答题流、提交、反馈、恢复选项、进度 |
| `TeacherDashboard.tsx` | 已实现 | 班级概览、学生列表、AI 建议 |
| `ParentSummary.tsx` | 已实现 | 静态演示数据 |
| `AdminPanel.tsx` | 已实现 | 系统概览、文案管理、规则展示（内容审核为静态） |
| `api.ts` | 已实现 | 所有 API 方法封装、token 自动刷新 |

### 2.8 测试

| 文件数 | 收集测试数 | 状态 |
|--------|------------|------|
| 49 个测试文件 | 868 个（0 error、0 failure、16 warning） | 全部通过（HEAD=79d7f36，count_verification.json 复算于 7ce9ffb）；`pydantic_settings` 版本冲突已修复 |

> 当前实测 868 passed（49 测试文件，0 error、0 failure、16 warning）；历史文档曾称 420，现以复算值为准。复算命令：`python -m pytest tests/ -q` → `artifacts/count_verification.json`。

---

## 3. 缺失/需完善功能清单（按优先级）

### P0 — 必须完成（阻塞或影响核心可用性）

| # | 问题 | 影响 | 建议方案 |
|---|------|------|----------|
| 3.1 | **新注册用户/演示账号没有自动创建 PetProfile** | `/student/pet`、`/student/dashboard` 返回 `has_pet: False`；`submit-answer` 中 `pet` 为 `None`，宠物成长逻辑不生效 | 在注册流程和 `_ensure_demo_users()` 中统一创建宠物，并设置默认四维 50 |
| 3.2 | **seed.py 导入 `AsyncSessionLocal` 失败** | 无法通过 `seed.py` 初始化数据库，演示环境依赖 `main.py` 启动时的种子任务 | 修正为使用 `app.core.database._get_sessionmaker()` 或导出 `AsyncSessionLocal` |
| 3.3 | **`/teacher/ai/student-analysis/{id}` 存在运行时错误** | 独立函数内使用 `cls._count_consecutive_fails`，调用即 500 | 改为顶层函数 `_count_consecutive_fails` 或移除 `cls` 前缀 |
| 3.4 | **`submit-answer` 未创建 `SpacedReview` 记录** | 间隔重复引擎仅存在于代码中，无法触发复习提醒 | 答对后按 `SpacedRepetitionService` 创建复习计划，答错加入错题再练 |
| 3.5 | **`next-task` 未使用 BKT / 85% 规则 / Elo-FSRS 模型** | 难度推荐仅靠 DDA 成功率，知识掌握度未真正驱动题目选择 | 用 `StudentSkillProfile` 或 BKT 状态计算最优难度，再与 DDA 结果融合 |
| 3.6 | **测试环境 `pydantic_settings` 版本冲突导致无法收集测试** | CI/回归受阻 | 锁定 `pydantic-settings>=2.3,<2.8` 或升级/降级到兼容 `pydantic` 版本 |
| 3.7 | **家长端 `ParentSummary.tsx` 使用硬编码演示数据** | 无法查看真实孩子数据，家长功能不可用 | 调用 `parentApi.childSummary` 并处理亲子关系绑定 |
| 3.8 | **学生注册时未绑定默认家长（演示账号亦无）** | 家长端无法验证亲子关系 | 注册时可选填写家长邮箱，或系统生成默认家长账号并绑定 |

### P1 — 应该完成（显著提升体验与功能完整性）

| # | 问题 | 影响 | 建议方案 |
|---|------|------|----------|
| 3.9 | **游戏化引擎未接入 API/前端** | 76 个成瘾引擎和连胜/宝箱/排行榜等仅存在于后端服务，用户无感知 | 新增 `/student/gamification`、`/student/streak`、`/student/leaderboard`、`/student/team` 等端点，并在前端展示 |
| 3.10 | **学习方法与技能树未接入学习流程** | 28 种方法和 16 技能树未使用，元学习体验缺失 | 在 `next-task` 返回学习方法提示，`submit-answer` 后根据题目推荐方法并加技能 XP |
| 3.11 | **风险监控未接入学生健康检查** | `/student/health-check` 返回静态 green，无法真实预警 | 基于答题时长、夜间答题、连续失败等指标调用 `RiskMonitor.assess` |
| 3.12 | **教师端无法真正创建题目并进入审核队列** | 管理端 `content` Tab 为静态 | 补全教师创建题目表单，管理员可审核/拒绝 |
| 3.13 | **前端缺少宠物自定义、连胜、排行榜、战队页面** | 大量后端能力无 UI 入口 | 新增 `PetCustomizePage`、`StreakPage`、`LeaderboardPage`、`TeamPage`、`SkillTreePage` |
| 3.14 | **OAuth 登录为前端模拟 UID，非真实 QQ/微信 OAuth** | 无法真实接入第三方登录 | 增加 OAuth 回调页 `/oauth/callback`，后端支持 `code` 换 `access_token`（可选） |
| 3.15 | **学习会话缺少结束总结与峰终定律** | 退出学习流时无高光时刻总结 | 在 `LearningSession` 退出或完成时调用 `PeakEndEngine.end_session` 并展示 |
| 3.16 | **错题再练入口为静态** | 学生仪表盘“错题再练”卡片未调用真实数据 | 接入 `/student/next-task?review=true` 或新增 `/student/due-reviews` |
| 3.17 | **教师端缺少学生详情页与难度调整 UI** | 后端 `/teacher/student/{id}`、调整难度端点已存在，但前端未展示 | 在教师仪表盘点开学生行跳转详情页，支持调整难度 |

### P2 — 锦上添花（增强与优化）

| # | 问题 | 影响 | 建议方案 |
|---|------|------|----------|
| 3.18 | **前端未使用 Tailwind 响应式类，且大量内联样式** | 移动端体验差，维护困难 | 逐步迁移到 Tailwind 类，增加移动端布局 |
| 3.19 | **缺少 WebSocket / 推送通知** | 连胜提醒、好友任务、联赛倒计时无法实时触达 | 增加 SSE 或 WebSocket 用于关键事件推送 |
| 3.20 | **测试数量已对齐为 868 passed（49 测试文件，0 error、0 failure、16 warning）** | 回归覆盖充足 | 以复算值为准，重点覆盖 P0 新增逻辑 |
| 3.21 | **Dockerfile 体积与 CloudBase 部署文档碎片化** | 部署可维护性低 | 统一 Dockerfile，移除 `Dockerfile.hello`/`minimal` 等调试文件 |
| 3.22 | **缺少学生-家长关系批量导入与班级管理** | 教师无法批量管理学生与家长 | 增加教师端班级导入、家长绑定功能 |
| 3.23 | **没有成就/徽章系统数据库模型** | 社交成瘾、多邻国式引擎中大量徽章概念无法持久化 | 新增 `Badge`、`Achievement`、`UserBadge` 模型 |

---

## 4. 接口/UI 差距清单

### 4.1 后端 API 已暴露但前端未使用

| 后端端点 | 前端当前状态 | 建议前端动作 |
|----------|--------------|--------------|
| `GET /student/pet` | 未显示宠物详情页 | 增加宠物详情/装扮页 |
| `GET /student/relaxation-guide` | 未在放松模式时调用 | 开启放松模式时获取引导文案 |
| `POST /student/consent` | 仅用于 relaxation_guide | 增加设置页管理 EEG/数据研究等同意项 |
| `GET /teacher/student/{id}` | 未实现学生详情页 | 增加学生详情页 |
| `POST /teacher/ai/adjust-difficulty` | 未使用 | 学生详情页增加难度调整 |
| `GET /parent/consent-settings/{id}` | 家长页按钮未绑定 | 增加同意设置弹窗 |
| `GET /parent/child/{id}/export` | 家长页按钮未绑定 | 点击导出时调用并下载 JSON |
| `GET /admin/pending-tasks` | Admin content Tab 静态 | 接入真实待审核列表 |
| `POST /admin/review-task` | 无审核按钮 | 增加通过/拒绝按钮 |
| `POST /admin/feedback-scripts` | 无新增文案入口 | 增加文案创建表单 |

### 4.2 后端能力未暴露为 API

| 后端服务 | 建议新增端点 | 前端需求 |
|----------|--------------|----------|
| `DuolingoStreakEngine` | `GET /student/streak` | 连胜火焰、冻结卡、提醒 |
| `XPEngine / LeagueEngine` | `GET /student/xp`, `GET /student/league` | 经验条、联赛排名 |
| `TeamManagementEngine` | `GET /student/team`, `POST /student/team` | 战队创建/加入/对抗 |
| `SocialAddictionEngine / BusinessCardEngine` | `GET /student/social/profile`, `POST /student/social/cheer` | 名片、鼓励好友 |
| `SkillTreeEngine` | `GET /student/skill-tree` | 学习技能树可视化 |
| `GamificationService` | `POST /student/open-box` | 宝箱动画 |
| `MemoryPalaceEngine` | `GET /student/memory-palace` | 记忆宫殿 UI |
| `TeacherAIAssistant` | `/teacher/ai/*` 已存在 | 前端展示班级/学生 AI 分析 |

### 4.3 前端界面与文档差距

| 文档要求 | 前端现状 | 差距 |
|----------|----------|------|
| 4 端角色分离 | 4 端页面均有 | 基本满足，但家长/管理员为演示/静态 |
| 学生仪表盘含宠物/统计/技能画像/每日目标/任务流 | 已实现 | 缺少连胜、排行榜、战队、技能树入口 |
| 教师面板：题目管理、风险告警处理、学生难度调整 | 部分实现 | 缺少题目创建、告警处理、学生详情 |
| 家长门户：学习时间趋势、同意管理、数据导出 | 未实现 | 趋势图、同意管理、导出均未接入 |
| 管理控制台：题目审核队列、用户管理 | 部分实现 | 题目审核静态、无用户管理 |
| QQ/微信 OAuth 快捷登录 | 模拟按钮 | 无真实 OAuth 流程 |

---

## 5. 待确认问题

1. **家长绑定策略**：新注册学生是否必须绑定家长？是否允许系统生成默认家长账号？还是教师/管理员批量导入家长关系？
2. **宠物默认值**：是否所有新用户默认获得一只名为“小豆”的猫，还是允许注册时选择宠物品种/名称？
3. **OAuth 范围**：本次迭代是否必须接入真实 QQ/微信 OAuth 回调，还是继续模拟 UID 即可？
4. **BKT 持久化**：BKT 状态是否持久化到数据库（新增 `bkt_state` 表），还是每次根据答题记录在线计算？
5. **测试目标**：当前实测 868 passed（49 测试文件），`pydantic_settings` 依赖冲突已修复；是否进一步扩充用例覆盖 P0 新增逻辑？
6. **部署目标**：本次增量是否包含重新部署 CloudBase，还是仅完成代码与测试？
7. **移动端优先级**：是否需要将前端响应式优化列为 P1，还是保持 P2？

---

## 6. 关键差距摘要（5 条）

1. **数据初始化缺口**：新用户/演示账号没有自动创建宠物，且 `seed.py` 无法导入 `AsyncSessionLocal`，导致核心宠物成长与间隔重复功能无法闭环。
2. **核心算法未接入业务流**：BKT、85% 规则、间隔复习、风险监控已作为独立服务实现，但尚未接入 `/student/next-task` 和 `/student/submit-answer` 的真实路径。
3. **后端引擎与前端脱节**：76 个成瘾引擎、28 个学习方法引擎、16 技能树、战队/联赛等能力大量未暴露为 API，前端缺少对应页面。
4. **运行时缺陷**：教师 AI 端点 `/teacher/ai/student-analysis/{id}` 存在 `cls._count_consecutive_fails` 运行时错误；测试环境因 `pydantic_settings` 版本冲突无法完整收集。
5. **家长与管理员功能演示化**：`ParentSummary.tsx` 使用硬编码数据，管理端内容审核为静态占位，真实业务流程未打通。
