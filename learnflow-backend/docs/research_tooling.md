# 研究工具与死代码可达性登记（Research Tooling & Dead-Code Register）

> 本论文项目有一条硬性规则：**未实现 / 运行时不可达的东西，要么接线暴露，要么显式登记为「有意非运行时」**。沉默的死代码被视为缺陷。
> 本文件集中登记四个被本任务处理的 `app/services` 模块的可达性状态。

---

## 1. 现已运行时可达（已接线为 HTTP 端点）

### `app/services/onboarding_engine.py`
新手上路 / 情境帮助 / 功能发现引擎，已实现但原本无运行时入口。现已由
`app/api/onboarding.py` 暴露（前缀 `/api/v1/onboarding`）：

| 端点 | 方法 | 包装的引擎方法 |
|------|------|----------------|
| `/api/v1/onboarding/steps` | GET | `OnboardingEngine.get_onboarding(role)` |
| `/api/v1/onboarding/current` | GET | `OnboardingEngine.get_current_step(role, completed_steps)` |
| `/api/v1/onboarding/complete` | POST | `OnboardingEngine.complete_step(role, step_id)` |
| `/api/v1/onboarding/skip` | POST | `OnboardingEngine.skip_onboarding(role)` |
| `/api/v1/onboarding/help` | GET | `ContextualHelpEngine.get_help_for_trigger(trigger, context)` |
| `/api/v1/onboarding/features` | GET | `FeatureDiscoveryEngine.check_new_features(role, sessions_completed)` |

### `app/services/placement_test_engine.py`
自适应入学水平测试引擎（类 CAT / IRT 原理），已实现但原本无运行时入口。现已由
`app/api/placement.py` 暴露（前缀 `/api/v1/placement`）：

| 端点 | 方法 | 包装的引擎方法 |
|------|------|----------------|
| `/api/v1/placement/start` | POST | `AdaptivePlacementEngine.start_test(user_id)` + `get_next_question(state)` |
| `/api/v1/placement/answer` | POST | `submit_answer(state, is_correct)` + `_check_convergence(state)` + `generate_result(state)` |

> ⚠️ 会话存储为 **进程内单 worker** 实现（字典 + `threading.Lock` + 30 分钟 TTL），
> 多 worker / 重启会丢失会话。生产部署需替换为 Redis 或数据库表。详见 `app/api/placement.py` 模块 docstring。

---

## 2. 有意非运行时（离线分析工具，按设计不暴露 HTTP）

这两个模块是论文的**离线统计工具**，用于计算效应量与功效分析，由研究者本地 /
脚本调用，刻意不接线为任何端点：

### `app/services/causal_effects.py`
- `dml_ate(treatment, outcome, covariates, l2)` —— 双机器学习（DML）残差回归，
  估计「某机制是否下发 → LAI 等学习指标变化量」的 **平均因果效应 ATE**（含标准误 `se` 与样本量 `n`）。
- `estimate_mechanism_effect(rows)` —— 把 `[{treatment, outcome, covariates}]` 行批量喂给 `dml_ate`，
  产出某机制的平均因果效应。
- **产出的研究工件**：论文最强的可复现卖点 —— 对照 CHI/UIST 因果评估范式的机制级 ATE 估计，
  用于支撑「机制有效」的因果声明（而非仅相关性）。

### `app/services/experiment_power.py`
- `design_effect(cluster_size, icc)` —— 整群随机设计效应 `DEFF = 1 + (m-1)·ρ`；`m=30, ρ=0.05 → 2.45`。
- `required_n_per_group(d, ...)` —— 连续结局（Cohen's d）每组样本量（two-sided, 含 DEFF 修正）。
- `required_n_two_proportion(p1, p2, ...)` —— 二分类结局（两组率差）每组样本量（Fleiss 法近似，含 DEFF 修正）。
- `plan_experiment(...)` —— 一键生成 `PowerPlan`（预注册用），含 `required_n_per_group` / `total_n` / `required_clusters`。
- **产出的研究工件**：论文 §3.4.2 样本量预注册方案。其 `DEFF = 2.45` 的整群随机修正直接决定了
  论文宣称的每组样本量要求（硬编码的 `min_sample_per_group=100` 已被本模块可复算的功效分析取代）。

两者均为纯计算函数（不依赖数据库 / 框架实例），由 `tests/test_experiment_power.py` 等单测覆盖，
**不通过 HTTP 暴露**——它们是论文方法学工件，不是产品运行时功能。
