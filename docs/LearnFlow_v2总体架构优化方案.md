# LearnFlow v2 总体架构优化方案

> 从「K12 游戏化刷题 Demo」重构为「可支撑计算机学科博士论文研究的实验平台」
> 版本：v2.0 ｜ 编制：论笃行（研究总编排）｜ 日期：2026-09-02

---

## 0. 一句话结论

当前架构的**算法层可用、数据层缺失、治理层为零**。v2 的全部工作量应集中在「补数据层、建治理层、不动算法层核心」。任何以重写算法为开端的改造都是错误方向。

---

## 1. 现状诊断

### 1.1 规模实测

| 层 | 文件数 | 行数 | 评价 |
|---|---:|---:|---|
| `app/services/` | 33 | 12,376 | 臃肿，9 个成瘾引擎零调用 |
| `app/api/` | 8 | 2,824 | 尚可，但 `gamification.py` 771 行过载 |
| `app/models/` | 7 | 524 | **严重不足**，16 表撑不起 33 个服务 |
| `app/core/` | 4 | 298 | 过薄，无缓存/消息/任务队列基础设施 |
| 前端 `src/` | 38 | 4,878 | 偏薄，17 个页面 |
| 后端合计 | 81 | 23,927 | — |

> 复算命令（后端规模）：`find app -name "*.py" | wc -l`（文件数）、`find app -name "*.py" -exec cat {} + | wc -l`（行数），HEAD=79d7f36 → 81 个文件 / 23,927 行。

**结构性失衡指标**：`services / models` 行数比 = **23.6 : 1**。
健康的教育平台该比值通常在 3:1 到 6:1。这个数字说明：**大量服务在内存里凭空造状态，没有落库**。

### 1.2 六项架构级缺陷

| ID | 缺陷 | 证据 | 后果等级 |
|---|---|---|---|
| **A1** | **状态无持久化** | 11 个类级可变字典驻留内存（`gamification_service.py:202/508/579`、`meta_learning_skilltree.py:163`、`ab_test_framework.py:104-105` 等）；`orchestrator.py:409` 每次请求 `XPState()` 重建 | 🔴 致命 |
| **A2** | **无统一机制注册表** | 全项目 `grep "registry\|MECHANISM_REGISTRY"` 零命中；`learning_orchestrator.py` 是硬编码 11 步流水线 | 🔴 致命 |
| **A3** | **无仲裁的并发干预** | 17 个独立 nudge 生成点；FOMO 催促与防沉迷限制语义直接对立 | 🔴 致命 |
| **A4** | **埋点严重不足** | `attempts` 表仅 4 个业务字段，无会话 ID、无展示/作答时间戳分离、无跳过标记 | 🔴 致命 |
| **A5** | **实验能力悬空** | A/B 框架无 `mechanism_id`，81 个引擎无一读取实验分组，实验数据在内存 | 🟠 高 |
| **A6** | **两层 API 语义混乱** | `k12.py`(88行) 与 `curriculum.py` 5 张表（`subjects`/`grade_levels`/`curriculum_nodes`/`classes`/`assignments`）**无任何 service 使用** | 🟠 高 |

### 1.3 已配置但未接线的基础设施

`app/core/config.py` 中已声明但代码中未发现使用：

- `REDIS_URL: str = "redis://localhost:6379/0"`（`:37`）
- `DATABASE_POOL_SIZE: int = 20` / `DATABASE_MAX_OVERFLOW: int = 10`（`:33-34`）
- `S3_*` 四个对象存储配置项（`:58-62`）

**判读**：作者有基础设施意识，但实现中途停在了配置层。v2 应**直接接上**这些，成本远低于新建。

---

## 2. v2 目标架构

### 2.1 分层原则

采用**五层单向依赖**，上层可依赖下层，下层严禁反向依赖：

```
┌─────────────────────────────────────────────────────────┐
│ L5  接入层  api/          FastAPI 路由、鉴权、DTO 校验      │
├─────────────────────────────────────────────────────────┤
│ L4  编排层  orchestration/ 会话编排、机制仲裁、实验注入      │
├─────────────────────────────────────────────────────────┤
│ L3  领域层  domain/       难度引擎、知识追踪、机制实现       │
├─────────────────────────────────────────────────────────┤
│ L2  支撑层  platform/     注册表、事件总线、实验框架、区块链  │
├─────────────────────────────────────────────────────────┤
│ L1  数据层  storage/      ORM、迁移、缓存、对象存储         │
└─────────────────────────────────────────────────────────┘
```

**关键约束**：L3 领域层**禁止直接读写数据库**，只能通过 L2 的仓储接口。这是当前代码最大的违规点——`learning_orchestrator.py:130` 直接执行 `SELECT Task WHERE difficulty == ...`。

### 2.2 目录结构重组

保留现有 `app/` 根布局以控制迁移成本，新增四个包：

```
learnflow-backend/app/
├── api/                    # L5 接入层（改造）
│   ├── v1/                 # 现有端点平移，保持向后兼容
│   │   ├── student.py      # 430 → 拆分
│   │   ├── teacher.py      # 713 → 拆分
│   │   ├── parent.py
│   │   ├── admin.py
│   │   ├── auth.py
│   │   └── gamification.py # 771 行 → 按机制类别拆 4 个
│   ├── v2/                 # 新增：实验平台 API
│   │   ├── experiments.py  # 实验注册、分组查询、指标上报
│   │   ├── telemetry.py    # 埋点批量上报（高吞吐，非阻塞）
│   │   ├── ledger.py       # 区块链凭证查询与验证
│   │   └── research.py     # 研究者数据导出（脱敏、IRB 合规）
│   └── deps.py             # 依赖注入集中化
│
├── orchestration/          # L4 编排层（新增，从 services 抽出）
│   ├── session_pipeline.py       # 替代硬编码 11 步
│   ├── mechanism_arbiter.py      # 干预仲裁（解决 A3）
│   ├── intervention_budget.py    # 干预预算
│   └── difficulty_fusion.py      # 难度融合（从 orchestrator:511 抽出）
│
├── domain/                 # L3 领域层（现有 services 迁入）
│   ├── difficulty/         # optimal_difficulty.py + dda.py 合并重构
│   ├── tracing/            # knowledge_tracing.py
│   ├── memory/             # spaced_repetition.py + memory_science_engine.py
│   ├── content/            # 题目、课程、知识点
│   └── gamification/       # 9 个成瘾引擎，按 taxonomy 重组
│
├── platform/               # L2 支撑层（新增）
│   ├── registry/           # 机制注册表（解决 A2）
│   │   ├── mechanism.py    # 抽象基类与声明式注册
│   │   ├── catalog.py      # LF-M01..LF-M54 目录
│   │   └── loader.py       # 自动发现与装配
│   ├── events/             # 事件总线 + schema（解决 A4）
│   │   ├── schema.py       # LearningEvent v1 定义
│   │   ├── bus.py          # 发布订阅
│   │   └── sink.py         # 落库 / 队列 / 链锚定
│   ├── experiment/         # 实验框架重构（解决 A5）
│   │   ├── assignment.py   # 确定性分桶 + 机制开关
│   │   ├── metrics.py      # 指标定义与护栏
│   │   └── stats.py        # 序贯检验、CUPED、多重比较校正
│   ├── ledger/             # 区块链模块（见专项设计文档）
│   └── llm/                # LLM 接入（离线标注，非在线决策）
│
├── storage/                # L1 数据层（新增，从 models 扩展）
│   ├── orm/                # 现有 7 个模型文件迁入 + 新增约 20 张表
│   ├── repositories/       # 仓储接口，供 L3 调用
│   ├── cache.py            # 接上 REDIS_URL（现有 services/cache.py 176 行升级）
│   └── migrations/         # Alembic 迁移（当前完全缺失）
│
└── core/                   # 配置、安全（保留，扩展）
```

### 2.3 为什么不做微服务

明确**保持单体**。理由：

1. 单体 + 模块化包结构已能解决全部六项缺陷，拆服务只增加运维成本
2. 博士论文的复现性要求「一条命令跑起来」，微服务是复现性的敌人
3. 项目规模（2.4 万行）远未触及单体瓶颈
4. 区块链模块以**进程内库 + 外部链节点**形式集成，不单独成服务

---

## 3. 数据层改造（对应 A1 / A4）

### 3.1 数据库选型

**建议：PostgreSQL 16+，放弃 MySQL 与 SQLite。**

| 维度 | SQLite（现状兜底） | MySQL（现状默认） | PostgreSQL（推荐） |
|---|---|---|---|
| JSONB 支持 | ✗ | 有限 | ✓ 原生，事件 schema 演进必需 |
| 窗口函数 | 部分 | 8.0+ | ✓ 完整，学习分析查询必需 |
| 数组/范围类型 | ✗ | ✗ | ✓ 难度区间、技能向量 |
| 物化视图 | ✗ | ✗ | ✓ 离线分析加速 |
| 时序扩展 | ✗ | ✗ | TimescaleDB 可选 |
| 全文检索 | 弱 | 中 | ✓ 中文需额外配置 |

**决定性理由**：事件 schema 会频繁演进（`LearningEvent` 会加字段），JSONB 是唯一现实选择。且窗口函数是学习分析（如「最近 20 次作答滚动成功率」）的刚需。

迁移路径：`SQLite → PostgreSQL`，用 Alembic 管理。当前**完全缺失迁移工具**，这是必须先补的基础设施。

### 3.2 事件表设计（解决 A4）

现有 `attempts` 表 4 个业务字段远远不够。新设计拆分**两张表**：

**`learning_events`（只增不改的事件流，高写入）**

```sql
CREATE TABLE learning_events (
    event_id        BIGSERIAL PRIMARY KEY,
    event_type      VARCHAR(48)  NOT NULL,  -- TASK_PRESENTED/ANSWERED/SKIPPED/HINT_REQUESTED/...
    user_id         UUID         NOT NULL,
    session_id      UUID         NOT NULL,  -- 新增：会话聚合键
    task_id         BIGINT,
    knowledge_point VARCHAR(64),
    -- 时间三元组（当前完全缺失）
    presented_at    TIMESTAMPTZ,            -- 展示时刻
    answered_at     TIMESTAMPTZ,            -- 作答时刻
    thinking_ms     INTEGER,                -- 冗余但高频使用，避免每次算差值
    -- 作答结果
    is_correct      BOOLEAN,
    answer_payload  JSONB,
    -- 难度决策快照（可复现性的关键）
    decision_snapshot JSONB  NOT NULL,      -- {theta, sigma, optimal_d, fused_d, zone, mechanism_toggles, experiment_arm}
    -- 上下文
    client_ctx      JSONB,                  -- 设备、时区、网络
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_events_user_time ON learning_events (user_id, created_at DESC);
CREATE INDEX idx_events_session   ON learning_events (session_id);
CREATE INDEX idx_events_kp        ON learning_events (knowledge_point, created_at);
```

**`decision_snapshot` 是本设计的重点**：把每次难度决策的完整输入与开关状态冻结下来。没有它，任何离线回放与因果归因都不可能——**这是论文可复现性的地基**。

**`attempts`（保留为面向业务的窄表，由事件流投影而来）**

```sql
CREATE TABLE attempts (
    attempt_id   BIGSERIAL PRIMARY KEY,
    user_id      UUID NOT NULL,
    task_id      BIGINT NOT NULL,
    session_id   UUID NOT NULL,
    is_correct   BOOLEAN,
    time_spent   INTEGER,
    hints_used   INTEGER DEFAULT 0,
    difficulty   NUMERIC(3,2),   -- 由 INT 改为 NUMERIC，支持 v2 的连续难度
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 3.3 需补的表清单

由「有引擎逻辑但无表」的 13 个模块反推，至少新增：

| 表名 | 对应模块 | 优先级 |
|---|---|---|
| `user_progression` | XP / 等级 / 连胜（`orchestrator.py:409` 当前丢失） | P0 |
| `skill_tree_state` | 16 技能树（`meta_learning_skilltree.py:163`） | P0 |
| `experiments` / `experiment_assignments` / `experiment_metrics` | `ab_test_framework.py:104-105` | P0 |
| `mechanism_state` | 机制通用状态 KV（替代 11 个内存字典） | P0 |
| `mechanism_catalog` | LF-M01..LF-M54 元数据（类别、理论来源、开关） | P0 |
| `intervention_log` | 每次干预的记录（谁、何时、哪个机制、是否被仲裁拦截） | P1 |
| `placement_sessions` | `placement_test_engine.py`（当前全流程不可恢复） | P1 |
| `onboarding_progress` | `onboarding_engine.py` | P1 |
| `usage_quota` | `anti_addiction_compliance.py` 时长配额 | P1 |
| `teams` / `team_members` / `team_matches` / `seasons` | `team_competition_engine.py` 4 个内存字典 | P2 |
| `quests` | `duolingo_addiction_engine.py:469 ACTIVE_QUESTS` | P2 |
| `memory_palaces` | `learning_methods_engine.py:329` | P2 |
| `self_regulation_goals` | `habit_addiction_engine.py:216` | P2 |
| `task_difficulty_priors` | LLM 离线标注的题目难度先验 | P1 |
| `ledger_anchors` | 区块链锚定记录（见专项文档） | P1 |

完整 DDL 见 `LearnFlow_机制治理与落实方案.md`（严复核负责）。

### 3.4 缓存与多 worker 一致性

`config.py:37` 已备好 `REDIS_URL`，直接接上：

- **会话级热状态**（宝箱进度、峰终会话记忆、未完成任务）→ Redis，TTL 24h，异步落库
- **持久状态**（XP、技能树、实验分组）→ PostgreSQL 为唯一真源，Redis 只做读缓存
- **实验分组** → 必须落库 + Redis 缓存，进程重启后分组不可变（否则实验失效）

现有 `services/cache.py`（176 行）需要评估后升级或替换。

---

## 4. 编排层重构（对应 A2 / A3）

### 4.1 从硬编码流水线到可装配编排

现状 `learning_orchestrator.py:46-233` 是一条写死的 11 步流程，新增机制必须改源码。v2 改为：

```python
# orchestration/session_pipeline.py
class SessionPipeline:
    """声明式编排：阶段 → 候选机制 → 仲裁 → 执行"""

    STAGES = ["pre_session", "task_selection", "during_task",
              "post_answer", "session_end", "async_nudge"]

    def run(self, stage: str, ctx: SessionContext) -> list[Effect]:
        candidates = self.registry.query(stage=stage, ctx=ctx)
        enabled = [m for m in candidates
                   if m.is_enabled(ctx.user_id, ctx.experiment_assignment)]
        scored = [(m, self.arbiter.score(m, ctx)) for m in enabled]
        return self.arbiter.select(scored, ctx.budget)
```

### 4.2 干预仲裁器（解决 A3）

17 个 nudge 生成点的冲突，用**三层过滤**解决：

```
第 1 层｜合规否决（绝对优先）
  防沉迷时长限制、强制休息、监护人撤回同意
  → 命中即清空所有"延长使用"类干预

第 2 层｜预算约束
  每会话最多 N 次干预；每 24h 最多 M 次推送；同类机制最小间隔 T
  → 超出预算按 score 降序截断

第 3 层｜语义互斥图
  静态声明机制对的互斥关系（如 FOMO ↔ 休息提醒）
  → 同批次内互斥对只保留 score 高者
```

**语义互斥图必须静态声明并可测试**，运行时检测会漏掉未触发的路径。这是仲裁器能被论文引用的前提——可验证的约束，而非黑箱打分。

### 4.3 难度融合抽离

`orchestrator.py:511-516` 的 `round(0.45×BKT + 0.35×DDA + 0.20×Optimal)` 三量纲直接加权，抽到独立模块 `orchestration/difficulty_fusion.py`，由 `causal-analyst` 的 v2 设计重写（见 `LearnFlow_难度适配引擎v2设计.md`）。

**迁移期双写策略**：v1 融合与 v2 融合并行计算，v1 结果用于线上，v2 结果只记录到 `decision_snapshot`，待离线验证后再切换。这样可以在不中断服务的前提下积累 v2 的反事实数据。

---

## 5. API 层改造（对应 A6）

### 5.1 现有问题

- `gamification.py` 771 行承载过多职责
- `k12.py`（88 行）是领域硬编码的遗留，`curriculum.py` 的 5 张表**无任何 service 使用**——即 API 存在但业务从未走通
- 无 `/v2` 命名空间，无法做破坏性升级

### 5.2 处置建议

| 文件 | 现状 | 处置 |
|---|---|---|
| `gamification.py` (771) | 过载 | 按机制类别拆为 `rewards.py` / `social.py` / `progress.py` / `experiments.py` |
| `k12.py` (88) + `curriculum.py` 5 表 | 死代码 | **删除**。K12 课程体系与 CS 研究方向无关，保留只会制造"未完成功能"的负面信号 |
| `student.py` (430) | 尚可 | 保留，接入 v2 难度决策后返回完整 `decision_snapshot` |
| `teacher.py` (713) | 偏大 | 拆出 AI 助教与班级分析 |

### 5.3 新增 `/api/v2` 研究面 API

这是**论文的基础设施**，必须优先：

- `POST /api/v2/telemetry/batch` — 高吞吐埋点上报，异步非阻塞，写 `learning_events`
- `GET  /api/v2/experiments/{id}/assignment` — 查询（并惰性创建）用户分组
- `POST /api/v2/experiments/{id}/metrics` — 指标上报
- `GET  /api/v2/research/export` — 研究者数据导出，强制脱敏 + IRB 审计日志
- `GET  /api/v2/ledger/verify/{event_id}` — 链上凭证验证

**研究者导出端点必须内置审计**：谁在什么时候导出了什么范围的数据，全部记 `audit_logs`。这既是伦理合规要求，也是论文方法章节可写的点。

---

## 6. 前端架构调整

### 6.1 现状

38 个文件 / 4,878 行 / 17 个页面。相对后端偏薄，且 `CurriculumPage.tsx` 等页面绑定了 K12 课程体系（后端表已判定删除，前端需同步）。

### 6.2 改造要点

1. **删除 K12 绑定页面**：`CurriculumPage.tsx` 随后端 `curriculum` 表一并处置
2. **新增研究透明度面板**（论文加分项）：
   - 难度决策可视化：展示 `decision_snapshot` 中的 θ、σ、optimal_d、所属 zone
   - 可解释性面板：把 `optimal_difficulty.py` 已有的 `explanation` 字段（当前被 `orchestrator:119` 丢弃）真正暴露给用户
   - 实验知情同意与分组公示
3. **埋点 SDK 化**：把散落的埋点调用收敛为统一 hook（`useTelemetry`），事件 schema 与后端 `LearningEvent` 严格对齐，用 TypeScript 类型保证
4. **性能**：后端融合难度计算涉及多次 DB 往返，前端应做乐观更新避免卡顿——心流体验对延迟极敏感，>200ms 的等待会直接破坏"心流"这一核心主张

---

## 7. 可观测性与研究基础设施

### 7.1 当前缺口

`services/audit.py` 仅 37 行，只有 `audit_logs` 表。缺乏：
- 结构化日志
- 指标采集（Prometheus 或等价物）
- 分布式追踪
- 数据质量监控（空值率、事件乱序、埋点丢失）

### 7.2 最小可行方案

| 需求 | 方案 | 成本 |
|---|---|---|
| 结构化日志 | `structlog` + JSON 输出，强制带 `trace_id` / `user_id` / `session_id` | 低 |
| 埋点丢失检测 | 定时任务比对 `learning_events` 与前端上报计数 | 低 |
| 数据质量看板 | 每日跑一次Schema 校验 + 空值率 + 乱序率，异常告警 | 中 |
| 指标采集 | 先不做 Prometheus，用 `experiment_metrics` 表 + 简单聚合脚本 | 低 |

**研究平台的特殊性**：对生产系统而言可观测性是运维需求，对本项目而言它是**数据质量证据**。论文方法章节需要回答"你怎么知道埋点没丢"，上述检测就是答案。因此这一块**不可省略**，即便它对产品功能无贡献。

---

## 8. 安全与合规

### 8.1 现有基础

`core/security.py`（47 行）+ `models/consent.py`（84 行，含 `consent_records`）。GDPR/个人信息保护法的同意撤回机制已有雏形，这是**加分项**，应保留并强化。

### 8.2 必须补强

1. **JWT 密钥**：`config.py:41` 用 `secrets.token_hex(32)` 每次启动生成新密钥 → **重启即所有 token 失效**。生产必须改为从环境变量读取，缺失时启动失败（fail-fast）
2. **研究数据脱敏**：导出接口必须剥离可识别信息，或提供 k-匿名化
3. **未成年数据**：`anti_addiction_compliance.py` 与 `consent.py` 的监护人同意流程需打通（当前孤立）
4. **IRB/伦理审查**：涉及真人实验必须走伦理审批，且论文方法章节需声明审批号

---

## 9. 迁移路线图

### 阶段划分（与论文进度对齐）

| 阶段 | 工期 | 内容 | 对应论文需求 |
|---|---:|---|---|
| **S0 地基** | 4 周 | Alembic 引入、PostgreSQL 迁移、`learning_events` 表 + 埋点 SDK、结构化日志 | 全部论文的数据基础 |
| **S1 治理** | 6 周 | 机制注册表、仲裁器、干预预算、11 个内存态落库、实验框架改造 | 机制审计论文、消融实验前提 |
| **S2 算法** | 8 周 | 难度引擎 v2（统一量纲 + 心流形式化 + bandit）、双写与离线验证 | 难度适配论文（核心） |
| **S3 可信** | 8 周 | 区块链锚定模块、可验证凭证、跨机构场景 | 区块链论文 |
| **S4 实验** | 12–24 周 | 真实用户 A/B（依赖 IRB 审批与招募） | 全部实证章节 |
| **S5 收口** | 4 周 | 数据导出、复现包、开源发布 | 论文复现材料 |

**总计约 10–14 个月**（不含 S4 的真实实验周期）。

### 关键依赖与顺序约束

```
S0 ─→ S1 ─→ S2 ─→ S4
 ↓      ↓      ↓
 └──────┴→ S3 ─┘
              ↓
             S5
```

- **S0 必须先于一切**：没有 `learning_events`，后续所有实验都是空中楼阁
- **S1 与 S2 可部分并行**：注册表改造不动难度引擎内部
- **S3 相对独立**，但依赖 S0 的事件流（链上锚定的就是事件哈希）
- **S4 是瓶颈**：真实用户实验周期不可压缩，需最早启动 IRB 审批

---

## 10. 风险登记

| ID | 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|---|
| R1 | 数据库迁移引发数据丢失 | 中 | 高 | 当前无真实用户数据，风险窗口仅存在于开发期；迁移前全量备份 + 双写验证 |
| R2 | 注册表改造引发大面积回归 | 高 | 中 | 868 个现有测试是安全网；新增改造必须同步补测试，覆盖率不得下降 |
| R3 | 过度工程，工期失控 | 高 | 高 | 严守"不动算法核心"原则；每阶段设可演示里程碑 |
| R4 | 区块链模块沦为摆设 | 中 | 高 | 见区块链专项文档的降级方案；先做 Merkle 锚定最小版 |
| R5 | 真实用户招募失败 | 中 | **致命** | 尽早启动 IRB；准备公开数据集离线验证作为后备主证据 |
| R6 | 论文数字与代码不符被审稿人发现 | 中 | 高 | 机制编号体系 LF-M01..LF-M54 建立后，文档与代码双向可查 |

> 复算命令（测试数）：`python -m pytest tests/ -q` → 868 passed（49 测试文件，0 error、0 failure、16 warning），HEAD=79d7f36 / count_verification.json 复算于 7ce9ffb。

---

## 11. 与其他设计文档的分工

| 文档 | 负责人 | 覆盖范围 |
|---|---|---|
| 本文档 | 论笃行 | 分层架构、目录重组、数据层、API 层、前端、部署、路线图 |
| `LearnFlow_区块链大数据模块设计.md` | 洗澄明 | 区块链模块的技术选型、架构、合约设计、论文创新点 |
| `LearnFlow_难度适配引擎v2设计.md` | 顾因果 | 难度引擎的算法内核、统一量纲、心流形式化、bandit、实验设计 |
| `LearnFlow_机制治理与落实方案.md` | 严复核 | 机制编号体系、注册表、冲突仲裁、补表 DDL、消融实验统计设计 |
| `LearnFlow_文献测绘与研究缺口.md` | 搜文献 | 五个方向的文献格局、最近邻工作、研究缺口、BibTeX |
| `LearnFlow_期刊论文拆分方案.md` | 选题锐 | 4–6 篇论文拆分、新颖性审计、期刊路由 |
| `LearnFlow_博士毕业论文总纲.md` | 文锦成 | 博士论文完整章节结构与内容映射 |
