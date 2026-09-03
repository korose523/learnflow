# API 路由 与 Frontend Wrapper 对照表

本文件列出后端公开路由（`learnflow-backend/app/api/*.py`）与前端封装（`learnflow-frontend/src/services/api.ts`）的一一对应关系，便于快速核对与回归测试。

> 说明：所有后端路由均以 `/api/v1/...` 前缀注册。前端通过 `API_BASE`（默认 `/api/v1`）进行调用。

## 全量对照

- **认证（auth）**
  - 后端：`/api/v1/auth/register` → 前端：`authApi.register`
  - 后端：`/api/v1/auth/login/json` → 前端：`authApi.login`
  - 后端：`/api/v1/auth/login/oauth` → 前端：`authApi.oauthLogin`
  - 后端：`/api/v1/auth/refresh` → 前端：`authApi.refresh`
  - 后端：`/api/v1/auth/me` → 前端：`authApi.me`

- **学生端（student）**
  - 后端：`/api/v1/student/dashboard` → 前端：`studentApi.dashboard`
  - 后端：`/api/v1/student/next-task` → 前端：`studentApi.nextTask`
  - 后端：`/api/v1/student/submit-answer` → 前端：`studentApi.submitAnswer`
  - 后端：`/api/v1/student/recovery-choice` → 前端：`studentApi.recoveryChoice`
  - 后端：`/api/v1/student/pet` → 前端：`studentApi.pet`
  - 后端：`/api/v1/student/relaxation-guide` → 前端：`studentApi.relaxationGuide`
  - 后端：`/api/v1/student/consent` → 前端：`studentApi.updateConsent`
  - 后端：`/api/v1/student/due-reviews` → 前端：`studentApi.dueReviews`
  - 后端：`/api/v1/student/health-check` → 前端：`studentApi.healthCheck`

- **游戏化（student/gamification）**
  - 后端：`/api/v1/student/gamification/streak` → 前端：`gamificationApi.streak`
  - 后端：`/api/v1/student/gamification/xp` → 前端：`gamificationApi.xp`
  - 后端：`/api/v1/student/gamification/leaderboard` → 前端：`gamificationApi.leaderboard`
  - 后端：`/api/v1/student/gamification/team` → 前端：`gamificationApi.team`
  - 后端：`/api/v1/student/gamification/team/join` → 前端：`gamificationApi.joinTeam`
  - 后端：`/api/v1/student/gamification/team/leave` → 前端：`gamificationApi.leaveTeam`
  - 后端：`/api/v1/student/gamification/team/leaderboard` → 前端:（前端直接使用 `gamificationApi.team`/`teamLeaderboard`）
  - 后端：`/api/v1/student/gamification/skill-tree` → 前端：`gamificationApi.skillTree`
  - 后端：`/api/v1/student/gamification/daily-quests` → 前端：`gamificationApi.dailyQuests`
  - 后端：`/api/v1/student/gamification/complete-quest` → 前端：`gamificationApi.completeQuest`
  - 后端：`/api/v1/student/gamification/open-box` → 前端：`gamificationApi.openBox`
  - 后端：`/api/v1/student/gamification/memory-palace` → 前端：`gamificationApi.memoryPalace`
  - 后端：`/api/v1/student/gamification/pet` → 前端：`gamificationApi.updatePet`

- **教师端（teacher）**
  - 后端：`/api/v1/teacher/classroom` → 前端：`teacherApi.classroom`
  - 后端：`/api/v1/teacher/student/{id}` → 前端：`teacherApi.studentDetail(id)`
  - 后端：`/api/v1/teacher/tasks` → 前端：`teacherApi.createTask` / `teacherApi.listTasks`
  - 后端：`/api/v1/teacher/suggestions` → 前端：`teacherApi.suggestions`
  - 后端：`/api/v1/teacher/alerts` → 前端：`teacherApi.alerts`
  - 后端：`/api/v1/teacher/alerts/{id}/resolve` → 前端：`teacherApi.resolveAlert(id)`
  - 后端（AI）：`/api/v1/teacher/ai/classroom-analysis` → 前端：`teacherApi.aiClassroomAnalysis`
  - 后端（AI）：`/api/v1/teacher/ai/student-analysis/{id}` → 前端：`teacherApi.aiStudentAnalysis(id)`
  - 后端（AI）：`/api/v1/teacher/ai/difficulty-suggestions` → 前端：`teacherApi.aiDifficultySuggestions`
  - 后端（AI）：`/api/v1/teacher/ai/intervention-plan` → 前端：`teacherApi.aiInterventionPlan`
  - 后端（AI）：`/api/v1/teacher/ai/adjust-difficulty` → 前端：`teacherApi.adjustDifficulty`

- **家长端（parent）**
  - 后端：`/api/v1/parent/child/{id}/summary` → 前端：`parentApi.childSummary(id)`
  - 后端：`/api/v1/parent/consent-settings/{id}` → 前端：`parentApi.consentSettings(id)`
  - 后端：`/api/v1/parent/consent` → 前端：`parentApi.updateConsent`
  - 后端：`/api/v1/parent/child/{id}/export` → 前端：`parentApi.exportData(id)`（返回 `blob`）

- **管理端（admin）**
  - 后端：`/api/v1/admin/pending-tasks` → 前端：`adminApi.pendingTasks`
  - 后端：`/api/v1/admin/review-task` → 前端：`adminApi.reviewTask`
  - 后端：`/api/v1/admin/feedback-scripts` → 前端：`adminApi.feedbackScripts`
  - 后端：`/api/v1/admin/feedback-scripts` (POST) → 前端：`adminApi.createFeedbackScript`
  - 后端：`/api/v1/admin/alert-rules` → 前端：`adminApi.alertRules`
  - 后端：`/api/v1/admin/stats` → 前端：`adminApi.stats`

## 状态摘要

- 已在本地进行快速联通测试（后端运行于 `127.0.0.1:8000`，前端 dev 服务器 `127.0.0.1:5173`）。
- 游戏化模块关键接口（连胜、XP、排行榜、战队、每日任务、宝箱）已返回有效 JSON。
- 家长导出、AI 建议、DDA 流（next-task / submit-answer）已通过示例演示账号验证。

若需将此文档导出为 CSV/表格或集成到自动化测试报告中，可告知我进一步格式要求。

---
文档生成于项目工作区，文件路径：`docs/api_route_frontend_mapping.md`。
