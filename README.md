# LearnFlow

> **把「难度」从工程参数提升为可测量、可校准、可决策、可治理的一等公民。**
> 一个面向 K12 的游戏化自适应学习平台，同时作为**实证研究可复现性 artifact** 发布。

[![tests](https://img.shields.io/badge/tests-898%20passed-brightgreen)](#测试)
[![mechanisms](https://img.shields.io/badge/mechanisms-54%20(LF--M01%E2%80%A6LF--M54)-blue)](#可复现性)
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## English Overview

**LearnFlow** is a K12 gamified adaptive-learning platform, released primarily as a
**reproducible research artifact**. Its research contribution is methodological: it treats
*learning difficulty* as a measurable, calibratable, decision-theoretic and governable
first-class quantity rather than as a fixed engineering constant.

The artifact accompanies a portfolio of empirical papers on (i) commensurability of
difficulty scales, (ii) external-validity testing of the 85% success-rate rule,
(iii) ordered-action bandits with a formalised flow channel, (iv) formalisation and
conflict arbitration of gamification interventions, and (v) reliability boundaries of
LLM-based difficulty annotation.

Two properties make the artifact useful to reviewers:

- **Machine-verifiable numbers.** Every headline count in the documentation is recomputed
  from source by scripts in `learnflow-backend/scripts/`, and the check fails loudly when a
  document number diverges from the code. See [Reproducibility](#可复现性).
- **No proprietary data.** All empirical inputs are public datasets or a locally-run
  simulator; per-participant runtime state is deliberately excluded from version control.

---

## 这是什么

LearnFlow 是一个 **K12 游戏化自适应学习平台**，包含学生 / 教师 / 家长 / 管理员四端，
以及一套面向实证研究的可复现性基础设施。

它同时承担两个角色：

| 角色 | 说明 |
|---|---|
| **软件系统** | 可运行的自适应学习平台：动态难度调节（DDA）、记忆科学复习调度（FSRS）、游戏化干预引擎、防沉迷与未成年保护护栏、家长门户 |
| **研究 artifact** | 为一系列实证论文提供**可引用、可复现**的系统底座与统计脚本；所有头部数字均可由代码复算 |

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

---

## 测试

```bash
cd learnflow-backend

# 全量测试（当前 898 passed）
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
│   │   ├── api/                # 路由层（含机制独立 API 模块）
│   │   ├── core/               # 配置 / 数据库 / 安全
│   │   ├── models/             # SQLAlchemy 模型
│   │   └── services/           # 领域服务（DDA、记忆科学、游戏化引擎…）
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
| `docs/LearnFlow_期刊论文拆分方案.md` | 论文组合规划、五维新颖性审计、数字诚信红线 |
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
- 涉及人类被试的研究须先取得伦理审查批准

### 数据边界

以下内容**刻意排除**在版本控制之外，因为它们属于研究原始数据或敏感配置：

| 路径 | 内容 | 排除原因 |
|---|---|---|
| `learnflow-backend/.env` | 密钥与种子口令 | 凭据 |
| `learnflow-backend/artifacts/state/` | 被试实时游戏化状态 | 研究原始数据，受数据最小化约束 |
| `learnflow-backend/artifacts/experiments.json` | 被试分组信息 | 研究原始数据（含处理/对照分配） |
| `*.db` / `*.sqlite*` | 本地数据库 | 运行时产物 |

`artifacts/` 中**除上述两类外**的复算产物**刻意纳入版本控制**——它们是论文可复现性印章的一部分。

---

## 引用

见 [`CITATION.cff`](CITATION.cff)。归档后的版本将获得 Zenodo DOI，届时请引用带 DOI 的具体版本。

## 贡献与支持

见 [`CONTRIBUTING.md`](CONTRIBUTING.md)。

## 许可证

[MIT](LICENSE)。
