# LearnFlow

> **为「适应性学习中难度的可测量化与可治理化」提供可测量、可审计、可复现的系统与测量底座。**
> 平台以游戏化自适应学习为载体，同时作为**实证研究可复现性 artifact** 发布。

> **身份说明（2026-09-22）**：本仓库的研究主线**唯一**是**难度**（测量 → 目标 → 决策 → 治理，
> 见 §难度研究主线）。历史版本曾把「学习成瘾化」写为主线，现已降级为
> **附属且未经心理测量学验证的模块**（见 §附属模块：学习成瘾指数）。同一产物不得同时
> 声明两个研究主线。

[![tests](https://img.shields.io/badge/tests-1017%20passed-brightgreen)](#测试)
[![mechanisms](https://img.shields.io/badge/mechanisms-54%20registered%20%C2%B7%202%20effect--producers%20%C2%B7%209%2F37%2F8-blue)](#可复现性)
[![instruments](https://img.shields.io/badge/self--report%20instruments-4-orange)](learnflow-backend/app/services/instrument_catalog.py)
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

> **当前投稿路线（2026-10-07 作者确认）**：M1/M3 优先采用公开日志与离线评价，不开展新真人实验。现成 K12 题库优先复用 XES3G5M，已整理 7,652 题，当前数值界面经格式初筛兼容 3,209 题；其余图题/选择/多空题需独立适配。详见 `docs/当前投稿路线_公开数据与离线评价.md` 和 `results/k12/xes_bank_inventory.json`。研究会话仅为后续技术储备，测试通过不等于人类学习效果。

## English Overview

**LearnFlow** is a K12 gamified adaptive-learning platform, released primarily as a
**reproducible research artifact for the study of _difficulty_ in adaptive learning (AI-assisted)**.

Its research contribution supports four connected lines of work:

| Line | Question |
|---|---|
| **Measurement** | Are difficulty sources defined on different scales commensurable? |
| **Target** | What can observed success-rate distributions tell us, and what requires a learning-gain experiment? |
| **Decision** | How does difficulty enter ordered sequencing under a cold start, and where does an LLM difficulty prior stop being reliable? |
| **Governance** | Which intervention schema fields and effect producers exist in the sealed internal implementation? |

Three properties are load-bearing for reviewers:

- **Mechanism accounting is a triple, never a single number.** The registered mechanism count
  (54) is always reported together with the **runtime effect-producer count (2)** and the
  **maturity breakdown (complete 9 / partial 37 / placeholder 8)**. A registered count alone
  would be read as "54 mechanisms are running", which is not what the code does.
- **Recomputed counts with explicit limits.** Count scripts inspect code and selected document
  fields. Missing document matches are not verification, and counts do not establish runtime
  user outcomes or scientific validity. See [Reproducibility](#可复现性).
- **Failed implementations are not results.** Annotation runs that failed for engineering
  reasons (truncated thinking blocks, unparseable output formats) are reported separately
  from valid protocol comparisons, and never enter a capability claim.

> **Auxiliary, unvalidated module.** The repository also contains a behavioural-log plus
> self-report measurement layer (a five-dimension learning-addiction index, LAI). It has no
> user data, its self-report items are purpose-built and **not yet psychometrically validated**,
> and it is **not used or validated in any of the four lines of work above**. It is retained
> for engineering completeness only; see [§附属模块](#附属模块学习成瘾指数lai未经验证).

## 这是什么

LearnFlow 是一个 **K12 游戏化自适应学习平台**，包含学生 / 教师 / 家长 / 管理员四端，
以及一套面向实证研究的可复现性基础设施。

它同时承担三个角色：

| 角色 | 说明 |
|---|---|
| **研究 artifact** | 为难度研究（测量 / 目标 / 决策 / 治理四条链）提供**可引用、可复现**的系统底座与统计脚本；所有头部数字均可由代码复算 |
| **软件系统** | 可运行的自适应学习平台：动态难度调节（DDA）、记忆科学复习调度（FSRS）、游戏化干预引擎、教育与未成年保护护栏、家长门户 |
| **附属模块** | 学习成瘾指数（LAI）行为日志 + 自陈量表测量层：**未经心理测量学验证，非研究主线**，仅为工程完整性保留 |

---

## 难度研究主线

本项目的核心研究问题是：**适应性学习系统每天都要回答「下一题给什么难度」，而支撑这一
决策的核心量「难度」从未被当作可测量、可校准、可决策、可治理的形式对象来处理。**
四条链彼此递进，构成学位论文的整合结构：

| 链 | 问题 | 状态 |
|---|---|---|
| **1 测量** | 难度各源是否可公度？线性归一化加权的有效权重是否随单调重参数化漂移？ | 已执行（合成 + assist09 真实数据） |
| **2 目标** | 最优错误率 15.87%（85% 规则）在外部分布上是否成立？ | 描述性证据；因果侧识别**尚未执行**（见 `docs/LearnFlow_研究总档.md（第七部·研究设计与审阅档案）（§2 因果侧识别策略）`） |
| **3 决策** | 难度如何进入带记忆的序贯决策？LLM 难度先验可信到哪里？ | 已执行（Junyi 真实臂 + LLM 标注协议审计） |
| **4 治理** | 数十个干预机制并存时，冲突是否真的发生？ | **内部静态审计**（无真实用户日志，运行时冲突频率未测） |

> 计划书与进展报告的唯一源是 `docs/研究计划与报告/` 的中韩四份 Markdown。现行稿与历史材料的区别见 `docs/README.md`；Word 工作稿由 `tools/docx_build/_md_to_docx.py` 生成到仓库外修订包。M1、M3 仍暂缓投稿；M2 为路线 B 内部章节，M4 不在提交包中。

---

## 附属模块：学习成瘾指数（LAI，未经验证）

> ⚠️ **本节描述的不是本研究主线，且该模块未经验证、无用户数据、未在任何一篇支撑稿中使用。**
> 保留它是为了工程完整性（四端界面与 API 仍在运行），**不得**把它写成本 artifact 的测量贡献。

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
综合指数下结论，本身就是本研究的方法论主张。原始测量层设计文档见
`learnflow_archive_20260913/docs/LearnFlow_成瘾化研究_测量框架.md`。

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

# 全量测试（历史审阅基线 972 passed；当前结果见修订包验证记录）
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
# 静默模式同时输出机制头条三元组：登记 54 / 效果生产 2 / 成熟度 9·37·8
.venv/Scripts/python scripts/verify_counts.py

# 代码资产数字（Python 行数、服务模块数、源文件数、API 端点、测试数）
# --doc-check 在「文档数字 ≠ 代码事实」时以退出码 1 报错
.venv/Scripts/python scripts/verify_asset_numbers.py --doc-check --with-pytest

# 滑窗错误率的离散支撑点口径（M1 8.1 / 报告 3.7 / 计划书 RQ2 依赖的数字）
python ../results/code/verify_window_support.py
```

> ⚠️ **机制数字必须三个并列**：`登记 54 / 运行时效果生产者 2 / 成熟度 complete 9 · partial 37 · placeholder 8`。
> 只写「54 机制」会被读成「54 个都在运行」——运行时真正构造干预效果的只有 2 处
> （`deep_addiction_engine.py:296` LF-M44、`learning_orchestrator.py:986` LF-M52），
> 其余机制只写评估记录或不构造效果。三元组由 `verify_counts.py` 复算，`tests/test_count_verification.py` 钉死。
> 效果生产者采用封存审计时点 2（tag `audit-m2-20260911`）。Route A 固定候选代码已移至非运行实验档案，应用不再注入。

主要统计脚本：

| 脚本 | 产出 |
|---|---|
| `scripts/verify_counts.py` | 机制唯一数（54）、学习方法数（28）、技能树节点数（16）、**成熟度三元组（9/37/8）**、**效果生产者数（2）**、注册表指纹 |
| `scripts/verify_asset_numbers.py` | 代码资产数字 + 文档一致性门禁（`--doc-check`） |
| `scripts/scan_mechanism_landing.py` | 机制运行时可达性扫描（落地 / 孤儿 / 编排器接线） |
| `scripts/power_table.py` | 实验功效与样本量测算表（离线分析工具） |
| `../results/code/verify_window_support.py` | assist09 滑窗错误率的 21 个离散支撑点口径（反分箱伪影） |
| `../results/code/record_llm_model.py` | LLM 标注模型的 manifest / digest / 量化 / 基座元数据 |

机读产物落在 `learnflow-backend/artifacts/`：

- `count_verification.json` —— 计数核验（含 `cross_validation_passed`、`maturity_*`、`effect_producers`）
- `mechanism_landing_status.json` —— 逐机制落地状态（`total` / `landed` / `orphan` / `orchestrator_wired`）
- `asset_numbers.json` —— 代码资产数字快照
- `impl_ref_integrity.json` —— 实现引用完整性

### 封存审计与历史资产口径（非本轮完整资产快照）

| 指标 | 值 | 复算来源 |
|---|---|---|
| 游戏化机制（登记） | **54**（`LF-M01`…`LF-M54`） | `verify_counts.py` |
| 运行时干预效果生产者 | **2** | `verify_counts.py` / `effect_producers` |
| 机制成熟度 | **complete 9 / partial 37 / placeholder 8** | `verify_counts.py` / `maturity_*` |
| 占位机制 ID | `LF-M19, M28, M29, M32, M45, M49, M50, M53` | `verify_counts.py` / `maturity_placeholder.ids` |
| 学习方法 | **28**（`LF-L01`…`LF-L28`） | `verify_counts.py` |
| 元学习技能树节点 | **16** | `verify_counts.py` |
| 机制引用覆盖（不表示运行时效果） | **54 / 54**，孤儿 0（历史扫描） | `scan_mechanism_landing.py` |
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
├── docs/                       # 当前工作稿索引、冻结原件与明确标识的历史稿
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

当前源与历史稿的身份以 [docs/README.md](docs/README.md) 为准。本轮工作稿未冻结；其余完整稿不是最终版本。

| 文档 | 用途 |
|---|---|
| `docs/研究计划与报告/` | 四份中韩计划/报告唯一 Markdown 源 |
| `docs/M1_submission_EN_compressed.md` | M1 唯一拟投稿主稿 |
| `docs/M3_submission_EN_compressed.md` | M3 指标修正工作稿 |
| `docs/M2_路线B_内部静态审计章.md` | 内部静态审计章节 |
| `docs/机制治理_审计基线.md` | 旧审计口径，不能视为当前运行结果 |
| `docs/因果侧识别策略.md` | f43e2a7 冻结原件 |
| `docs/因果侧识别策略_v2_未冻结草案.md` | 执行前讨论草案 |

修订 Word、答复与日志位于仓库外 `/Volumes/Untitled/learnflow_revision_20261007/`；旧材料备份位于 `/Volumes/Untitled/learnflow_revision_archive_20261007/`。当前移出文件不清除 Git 历史。最近本地后端全量测试991项通过，随后相关回归85项通过；这不表示人类实验已经实施。

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

> ⚠️ **已知的不一致（正在修复）**：Zenodo 现存 `10.5281/zenodo.22719229` 为 **v0.1.0（2026-09-11）**，
> 其记录标题写的是「学习成瘾测量工具」，与本仓库当前统一的难度研究主线不一致。
> v0.2.0 的元数据（标题 / 描述 / 关键词以难度为中心，LAI 明确标注为附属未验证模块）
> 已准备在 [`.zenodo.json`](.zenodo.json)，上传新版本后该记录即与稿件正文统一。
> 在此之前引用时请以本仓库 README 与 `CITATION.cff` 的主题为准。

## 贡献与支持

见 [`CONTRIBUTING.md`](CONTRIBUTING.md)。

## 许可证

[MIT](LICENSE)。
