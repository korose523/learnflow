# LearnFlow

> **为一个面向 K12 的学习成瘾化研究，提供可测量、可审计、可复现的系统与测量底座。**
> 平台以游戏化自适应学习为载体，同时作为**实证研究可复现性 artifact** 发布。

[![tests](https://img.shields.io/badge/tests-920%20passed-brightgreen)](#测试)
[![mechanisms](https://img.shields.io/badge/mechanisms-54%20(LF--M01%E2%80%A6LF--M54)-blue)](#可复现性)
[![instruments](https://img.shields.io/badge/self--report%20instruments-4-orange)](docs/LearnFlow_成瘾化研究_测量框架.md)
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## English Overview

**LearnFlow** is a K12 gamified adaptive-learning platform, released primarily as a
**reproducible research artifact for the study of learning addiction (AI-assisted)**.

Its measurement contribution is a **dual-source, five-dimension framework**: a behavioural
log (durations, night-time ratio, hint dependence) is combined with a **self-report
instrument layer** to cover the dimensions that behavioural logs structurally cannot
observe — behavioural control, sleep/social impairment, and time-perception bias.

Two properties are load-bearing for reviewers:

- **Measurement honesty.** 45% of the index weight depends on self-report. When a dimension
  is unmeasured, it is **excluded from the weighting and reported via a coverage object** —
  never silently scored as healthy. The API returns the score *together with* its coverage.
  The self-report items are **purpose-built and not yet psychometrically validated**; the
  documentation states this unconditionally.
- **Machine-verifiable numbers.** Every headline count in the documentation is recomputed
  from source by scripts in `learnflow-backend/scripts/`, and the check fails loudly when a
  document number diverges from the code. See [Reproducibility](#可复现性).

## 这是什么

LearnFlow 是一个 **K12 游戏化自适应学习平台**，包含学生 / 教师 / 家长 / 管理员四端，
以及一套面向实证研究的可复现性基础设施。

它同时承担三个角色：

| 角色 | 说明 |
|---|---|
| **测量系统** | 学习成瘾化的**双源五维**测量层：行为日志 + 自陈量表，含覆盖度报告与「未测不得谎报为健康」的强制约束 |
| **软件系统** | 可运行的自适应学习平台：动态难度调节（DDA）、记忆科学复习调度（FSRS）、游戏化干预引擎、防沉迷与未成年保护护栏、家长门户 |
| **研究 artifact** | 为一系列实证论文提供**可引用、可复现**的系统底座与统计脚本；所有头部数字均可由代码复算 |

> 🔬 **成瘾化研究主线的权威测量定义**见
> [`docs/LearnFlow_成瘾化研究_测量框架.md`](docs/LearnFlow_成瘾化研究_测量框架.md)
> —— 五维如何测量、哪些维度其实测不到、以及必须声明的信效度局限。

---

## 成瘾化研究主线

本项目的核心研究问题是：**如何在 K12 学习场景中，把「成瘾化」从主观判断变成可测量、
可审计、且诚实披露其边界的量。** 技术实现围绕这一个问题组织。

### 双源五维测量

| 维度 | 权重 | 测量源 | 可观测内容 |
|---|---|---|---|
| `time` 时间投入 | 0.30 | 行为日志 | 时长 / 单次会话长度 / 夜间比例 |
| `motivation` 动机结构 | 0.25 | 行为日志（**代理**） | 提示依赖 → 内在动机 / 外在奖励依赖 |
| `control` 行为控制 | 0.25 | **自陈量表** | 能否按计划停止 |
| `cognition` 认知 | 0.10 | 行为日志 + **自陈** | 专注度代理 + 时间感知偏差 |
| `function` 功能影响 | 0.10 | **自陈量表** | 对睡眠与社交的损害 |

行为日志覆盖 55% 权重，自陈量表补上其余 45%——这两部分**互补而非互验**：
行为测「做了什么」，自陈测「体验如何」。

### 测量诚实性约束（工程强制，非文档自律）

1. **未测维度不得计分。** `LearningAddictionIndex.assess(measured_dimensions=…)` 要求调用方
   显式声明哪些维度有真实数据；未测维度从加权中剔除，权重在已测维度上重新归一化。
2. **分数必须随覆盖度一起返回。** `GET /api/v1/gamification/lai/dashboard` 的响应同时包含
   分数与其 `measurement` 覆盖度对象，使下游无法在不看到覆盖度的情况下引用分数。
3. **不给默认值。** 无自陈数据时，未覆盖的输入**不出现在**聚合结果里，绝不填一个
   「看起来健康」的常量。零自陈数据时权重基础为 **0.55**，如实报告。
4. **作答有效期 28 天。** 过期作答不再支撑当前评分，防止用数月前的一次填写维持结论。

### ⚠️ 必须声明的局限

- 四份自陈量表的题项为**本项目自行编写**，**尚未经过独立信效度检验**
  （无重测信度 / 结构效度 / 与 BSMAS、IGD-9 的聚合效度证据）。
  **不得**宣称其「已验证」「已标定」，**不得**据此做临床判断。
- 自陈存在社会赞许性偏差，方向性后果是**低估**成瘾风险。
- `motivation` / `time` 的构造是**代理指标**，不等于直接观测。
- 当前 **`connection_quality` 未被测量**（固定默认 0.7）。

这些局限在论文中必须逐条声明。把测量效度问题显式暴露出来，而非用一个未验证的
综合指数下结论，本身就是本研究的方法论主张。详见
[`docs/LearnFlow_成瘾化研究_测量框架.md`](docs/LearnFlow_成瘾化研究_测量框架.md)。

### 自陈测量 API

前缀 `/api/v1/instruments`：

| 方法 | 路径 | 用途 |
|---|---|---|
| `GET` | `/instruments` | 量表列表（含题项），可按维度过滤 |
| `GET` | `/instruments/catalog` | 目录元信息 + 指纹 `3531e875d286` |
| `POST` | `/instruments/{code}/responses` | 提交作答（服务端计分并落库） |
| `GET` | `/instruments/me/coverage` | 本人测量覆盖度（哪些维度已实测） |

---

## 环境要求

| 组件 | 版本 | 说明 |
|---|---|---|
| Python | **3.11+** | 后端。仓库锁定于 3.11 开发与测试 |
| Node.js | **18+** | 前端构建 |
| SQLite | 内置 | 本地开发默认；无需额外安装 |
| Redis | 可选 | 不可用时自动退化为内存缓存 |

---

## 快速开始

### 后端

```bash
cd learnflow-backend

# 1. 创建虚拟环境并安装依赖
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt   # macOS / Linux

# 2. 准备配置（务必先复制模板，不要提交 .env）
cp .env.example .env

# 3. 初始化演示数据（可选）
.venv/Scripts/python seed.py

# 4. 启动
.venv/Scripts/python -m uvicorn app.main:app --reload
```

- API 文档：<http://localhost:8000/docs>
- 健康检查：<http://localhost:8000/health>

### 前端

```bash
cd learnflow-frontend
npm install
npm run dev
```

前端：<http://localhost:5173>（开发模式下通过 Vite 代理访问后端 `/api/v1`）

### 演示账号

演示账号**仅在**显式执行 `seed.py` 或设置 `DEMO_DATA_ENABLED=true` 时创建。
密码通过未提交的 `.env` 或环境变量注入（`SEED_STUDENT_PASSWORD` 等）：

| 角色 | 邮箱 |
|---|---|
| 学生 | `student@learnflow.com` |
| 教师 | `teacher@learnflow.com` |
| 家长 | `parent_student@learnflow.com` |
| 管理员 | `admin@learnflow.com` |

> ⚠️ 演示账号面向本地评估。**生产环境与正式研究采集环境必须保持 `DEMO_DATA_ENABLED=false`，且不得设置演示账号。**

**口令轮换**：应用启动时会校验演示账号的 hash 是否与 `SEED_*_PASSWORD` 一致，
不一致则自动更新——因此轮换只需改 `.env`，无需删库重建。

**源码中不含任何口令。** 开发期快捷登录（点击角色卡片自动填充）：
口令只从**未提交**的 `learnflow-frontend/.env.local` 读取，且仅在 Vite 开发模式下生效：

```bash
cd learnflow-frontend && cp .env.example .env.local
# 把 VITE_DEMO_*_PASSWORD 填成与 learnflow-backend/.env 的 SEED_*_PASSWORD 相同的值
```

生产构建（`vite build`）下快捷登录整体不生效。

---

## 测试

```bash
cd learnflow-backend

# 全量测试（当前 920 passed）
PYTEST_DEBUG_TEMPROOT=<绝对路径>/pytest_tmp .venv/Scripts/python -m pytest tests/ -q
```

> **注意**：`PYTEST_DEBUG_TEMPROOT` 必须指向一个**已存在的**目录，且必须是绝对路径。
> 否则依赖 `tmp_path` 夹具的用例会抛出 `FileNotFoundError`，表现为大批量失败，实为环境问题而非代码回归。

前端质量门：

```bash
cd learnflow-frontend
npm run lint      # eslint
npx tsc --noEmit  # 类型检查
npm run build     # 构建
```

---

## 可复现性

本仓库的**核心工程约定**是：文档中出现的每一个头部数字，都必须能被机器复算，否则视为缺陷。

```bash
cd learnflow-backend

# 机制数 / 学习方法数 / 技能树节点数 —— 权威计数与交叉校验
.venv/Scripts/python scripts/verify_counts.py

# 代码资产数字（Python 行数、服务模块数、源文件数、API 端点、测试数）
# --doc-check 在「文档数字 ≠ 代码事实」时以退出码 1 报错
.venv/Scripts/python scripts/verify_asset_numbers.py --doc-check --with-pytest
```

主要统计脚本：

| 脚本 | 产出 |
|---|---|
| `scripts/verify_counts.py` | 机制唯一数（54）、学习方法数（28）、技能树节点数（16）、注册表指纹 |
| `scripts/verify_asset_numbers.py` | 代码资产数字 + 文档一致性门禁（`--doc-check`） |
| `scripts/scan_mechanism_landing.py` | 机制运行时可达性扫描（落地 / 孤儿 / 编排器接线） |
| `scripts/power_table.py` | 实验功效与样本量测算表（离线分析工具） |

机读产物落在 `learnflow-backend/artifacts/`：

- `count_verification.json` —— 计数核验（含 `cross_validation_passed`）
- `mechanism_landing_status.json` —— 逐机制落地状态（`total` / `landed` / `orphan` / `orchestrator_wired`）
- `asset_numbers.json` —— 代码资产数字快照
- `impl_ref_integrity.json` —— 实现引用完整性

### 当前基线

| 指标 | 值 | 复算来源 |
|---|---|---|
| 游戏化机制（唯一） | **54**（`LF-M01`…`LF-M54`） | `verify_counts.py` |
| 学习方法 | **28**（`LF-L01`…`LF-L28`） | `verify_counts.py` |
| 元学习技能树节点 | **16** | `verify_counts.py` |
| 机制运行时落地 | **54 / 54**，孤儿 0 | `scan_mechanism_landing.py` |
| 注册表指纹 | `ee1a49be5732` | `registry_fingerprint()` |

> **数字纪律**：本项目历史上曾出现「76 个机制」的表述膨胀。四层复核链为
> **76**（早期标题声称）→ **69**（表格逐项求和）→ **60**（实现单元）→ **54**（语义去重后的唯一机制数）。
> 对外一律使用 **54**。该自我披露本身是本 artifact 的方法论主张之一。

---

## 项目结构

```
learnflow/
├── LICENSE                     # MIT
├── README.md                   # 本文件
├── CONTRIBUTING.md             # 贡献与支持指南
├── CITATION.cff                # 引用元数据
├── docs/                       # 研究文档（论文拆分、机制治理、文献测绘等）
├── artifacts/                  # E2E 验证截图等证据
├── learnflow-backend/          # FastAPI 后端
│   ├── app/
│   │   ├── api/                # 路由层（含机制独立 API 模块、自陈测量 instrument.py）
│   │   ├── core/               # 配置 / 数据库 / 安全
│   │   ├── models/             # SQLAlchemy 模型（含 instrument.py 自陈作答）
│   │   └── services/           # 领域服务
│   │       ├── (DDA / 记忆科学 / 游戏化引擎 …)
│   │       ├── instrument_catalog.py    # ⭐ 自陈量表目录与计分（测量层）
│   │       ├── self_report_service.py   # ⭐ 自陈聚合与覆盖度推导
│   │       └── learning_addiction_index.py  # ⭐ LAI 五维评分（受覆盖度约束）
│   ├── artifacts/              # 机器复算产物（可复现性印章）
│   ├── docs/                   # 架构图、增量 PRD、研究工具登记
│   ├── scripts/                # 复算与校验脚本
│   └── tests/                  # pytest 测试套件
└── learnflow-frontend/         # React 18 + TypeScript + Vite 前端
    └── src/
        ├── pages/              # 学生 / 教师 / 家长 / 管理员页面
        ├── components/         # 通用组件与布局
        └── services/           # API 客户端
```

---

## 文档索引

| 文档 | 内容 |
|---|---|
| `docs/LearnFlow_成瘾化研究_测量框架.md` | ⭐ **成瘾化研究主线的测量层权威定义**：五维如何测量、双源设计、覆盖度契约、信效度局限 |
| `docs/LearnFlow_抗成瘾层_论文表图.md` | 抗成瘾层结果表图（LAI 场景对比、仲裁器降权） |
| `docs/LearnFlow_学习成瘾化研究_补充文献测绘.md` | 成瘾化理论文献支撑（A 心理学 / B 游戏设计 / C 实证） |
| `docs/LearnFlow_期刊论文拆分方案.md` | 论文组合规划、五维新颖性审计、数字诚信红线 |
| `docs/LearnFlow_投稿材料模板.md` | 各目标期刊的强制前置材料模板（声明 / Highlights / Index Terms / 投稿检查清单） |
| `docs/LearnFlow_机制治理与落实方案.md` | 54 个机制的去重口径与落地状态 |
| `docs/LearnFlow_文献测绘与研究缺口.md` | 文献综述与研究缺口定位 |
| `docs/LearnFlow_v2总体架构优化方案.md` | 架构设计 |
| `docs/references.bib` | 参考文献库（BibTeX） |
| `learnflow-backend/docs/research_tooling.md` | 离线分析工具与死代码可达性登记 |
| `learnflow-backend/docs/incremental_prd.md` | 增量产品需求 |

---

## 研究与伦理说明

本项目面向**未成年人**，因此在设计上把安全与同意作为一等约束：

- 放松引导、氛围类功能**需显式同意**，可随时关闭
- 提示语标注来源，版本可追溯
- 积分仅用于虚拟进度，**不兑换实物**
- 失败不扣分，触发「恢复体力」而非惩罚
- 连续学习 90 分钟强制休息提醒
- **自陈量表数据仅本人可读写**，`user_id` 强制取自登录态，不提供无条件全表导出
- **未成年被试的研究同意必须由家长角色授权**，学生自授无效（`research_consent` 模块判定）
- 涉及人类被试的研究须先取得伦理审查批准；本仓库提供**采集能力**，不构成伦理批准

### 数据边界

以下内容**刻意排除**在版本控制之外，因为它们属于研究原始数据或敏感配置：

| 路径 | 内容 | 排除原因 |
|---|---|---|
| `learnflow-backend/.env` | 密钥与种子口令 | 凭据 |
| `learnflow-backend/artifacts/state/` | 被试实时游戏化状态 | 研究原始数据，受数据最小化约束 |
| `learnflow-backend/artifacts/experiments.json` | 被试分组信息 | 研究原始数据（含处理/对照分配） |
| `self_report_responses`（数据库表） | **未成年人自陈的心理/行为数据**（睡眠、社交、自控感受） | 研究原始数据，敏感度最高；不提供全表导出端点 |
| `*.db` / `*.sqlite*` | 本地数据库 | 运行时产物 |

`artifacts/` 中**除上述两类外**的复算产物**刻意纳入版本控制**——它们是论文可复现性印章的一部分。

---

## 引用

见 [`CITATION.cff`](CITATION.cff)。归档后的版本将获得 Zenodo DOI，届时请引用带 DOI 的具体版本。

## 贡献与支持

见 [`CONTRIBUTING.md`](CONTRIBUTING.md)。

## 许可证

[MIT](LICENSE)。
