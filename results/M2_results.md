# M2《游戏化干预冲突检测与仲裁》实证结果

- **数据工程师**：洗澄明（data-engineer）
- **仓库**：`E:\learnflow`（**只读运行**，未修改任何文件）
- **代码基线 commit**：`8a328430d36860043f3bf80e8e0bf2a82edd2ecd`（2026-09-11）
- **Python**：`E:\learnflow\learnflow-backend\.venv\Scripts\python.exe`（3.11.9，含 sqlalchemy / pytest）
- **所有产物目录**：`E:/learnflow/results/m2/`

> **复算环境约定**（每条命令均在此前缀下执行）：
> ```bash
> export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*'
> export PATH="/c/Users/mac/.workbuddy/binaries/PortableGit/versions/1.2.0/usr/bin:/c/Windows/System32:/c/Windows:$PATH"
> cd "E:/learnflow/learnflow-backend"
> PY="E:/learnflow/learnflow-backend/.venv/Scripts/python.exe"
> R="E:/learnflow/results/m2"
> ```
>
> **为什么用 harness**：`learnflow-backend/artifacts/` 是 **git 跟踪目录**（`.gitignore` 第 74 行明确「刻意不忽略」）。直接运行仓库脚本会覆写被跟踪的 JSON = 修改仓库。因此本报告全部通过 `$R/harness.py` 以 importlib 加载脚本模块、把模块级输出路径常量重定向到 `results/m2/` 后调用其 `main()` —— **跑的是脚本本体逻辑，但不写仓库**。
>
> **仓库未修改的证据**：运行前后 `git status --short` 输出**逐行一致**（同为 13 项预存在改动，无新增）。
> ```bash
> cd "E:/learnflow" && git status --short
> ```

---

## 摘要（关键数字）

| 项 | 本文实测 | 说明 |
|---|---:|---|
| 机制总数 | **54**（LF-M01…LF-M54，连续无缺口） | 与预期一致 |
| 注册表指纹 | **`ee1a49be5732`** | 与预期一致 |
| 治理文档 8 类别分布 | A 8 / B 8 / C 6 / D 10 / E 10 / F 4 / G 4 / H 4 | 合计 54 |
| 注册表 `category` 5 类别 | retention 19 / motivation 18 / selfreg 9 / cognition 4 / health 4 | **≠ 8 类** |
| 编排器步骤映射（门控映射） | **34** | 与文档一致 |
| 仅源码文本引用（未进步骤映射） | **20**（=54−34）；其中 LF-M01–M53 内为 **19** | 两种口径都成立 |
| 独立 `is_enabled` 门控并真实调用 | **31** | =34−3 健康护栏 |
| 落地扫描 landed / orphan | **54 / 0** | |
| 类型 I 效果方向冲突（运行时实际可检出） | **1**（LF-M44 vs LF-M52） | 由健康否决层消解 |
| 类型 I（静态潜在对，上界） | 27（9 approach × 3 withdraw） | |
| 类型 II 预算竞争（运行时） | **0** | 仅 1 个可见非健康候选 |
| 不可归类比例（无 direction 标注） | **42/54 = 77.8%** | 这是本系统 schema 覆盖率的真实缺口 |
| E2 外部系统 | **2 个**（Ludilearn 6 机制 / Level Up XP 11 机制） | 均 clone 成功 |

---

## E1 静态审计

### E1-1 机制总数与注册表指纹

```bash
PY="E:/learnflow/learnflow-backend/.venv/Scripts/python.exe"
R="E:/learnflow/results/m2"
cd "E:/learnflow/learnflow-backend" && "$PY" "$R/harness.py" fingerprint
```

**实测输出**（`results/m2/fingerprint.json`）：

```json
{
  "count": 54,
  "fingerprint": "ee1a49be5732",
  "id_first": "LF-M01",
  "id_last": "LF-M54",
  "id_contiguous": true,
  "registry_CATEGORIES": ["retention", "motivation", "selfreg", "cognition", "health"],
  "registry_STAGES": ["pre", "during", "post", "ambient"],
  "registry_category_counts": {"retention": 19, "motivation": 18, "selfreg": 9, "cognition": 4, "health": 4}
}
```

- **机制总数 = 54，指纹 = `ee1a49be5732`**，与任务预期完全一致。
- 指纹算法：`md5(f"{count()}|" + "|".join(sorted(ids())))[:12]`（`mechanism_registry.py:145-154`）。
- ID 连续无缺口由注册表构造期不变量强制（`mechanism_registry.py:510-519`）。

交叉校验（AST 静态复算，零依赖路径）：
```bash
cd "E:/learnflow/learnflow-backend" && "$PY" "$R/harness.py" counts
```
→ `mechanism_unique = 54`（strict，**verified**），三重交叉验证：类别标题声明合计 54 / 文档小计行 54 / 编号表 54 → 一致 ✓

---

### E1-2 8 类别分类、门控映射数与文本引用数

```bash
cd "E:/learnflow/learnflow-backend" && "$PY" "$R/m2_conflict_analysis.py"
```
（产物：`results/m2/m2_conflict_analysis.json`、`table1_mechanism_census.csv/.tex`）

#### (a) 8 个理论类别（治理文档 §2.4，类别标题 A–H）

| 类别 | 标题 | 机制数 |
|---|---|---:|
| A | 行为主义·强化与奖励 | 8 |
| B | 承诺、损失与目标梯度 | 8 |
| C | 自我决定论：自主·胜任·关联 | 6 |
| D | 社会影响与社会学习 | 10 |
| E | 习惯形成与自我调节 | 10 |
| F | 情绪与动机触发 | 4 |
| G | UX 微交互与认知负荷 | 4 |
| H | 健康护栏与伦理 | 4 |
| | **合计** | **54** |

**重要更正**：这 8 类是**治理文档**的分类学。`app/services/mechanism_registry.py` 的 `CATEGORIES` 常量只有 **5** 个值（retention / motivation / selfreg / cognition / health = 19/18/9/4/4）。**注册表不携带 8 类编码**，8 类只能从 Markdown 文档解析。论文若写「注册表按 8 类分类」即为不实表述。

#### (b) 接线强度分层

```bash
# 门控映射数（来自 learning_orchestrator.PIPELINE_MECHANISM_MAP）
cd "E:/learnflow/learnflow-backend" && "$PY" "$R/harness.py" landing
```

**实测（`results/m2/mechanism_landing_status.json`）**：

| 分层 | 实测 | 口径依据 |
|---|---:|---|
| `landed`（`impl_ref 可达 OR 编排器接线/门控`） | **54** | `scan_mechanism_landing.py:177` |
| `orphan` | **0** | |
| 进入 `PIPELINE_MECHANISM_MAP` 步骤映射 | **34** | 步骤 6(1)+8(2)+9(2)+12(1)+13(28) |
| 仅源码文本引用（未进步骤映射） | **20** | 54−34 |
| 其中 `is_enabled("<key>")` 独立门控并真实调用 | **31** | `learning_orchestrator.py` 中 31 个字面量 |
| 3 个健康护栏按设计豁免门控 | 3 | `lai_downgrade` / `forced_rest` / `minor_protection` |

未进步骤映射的 20 个 ID（实测）：
`LF-M02, M03, M07, M09, M10, M11, M17, M23, M25, M26, M27, M28, M30, M31, M36, M40, M42, M45, M47, M54`

**「34 / 19」与「34 / 20」的关系（答案：两者都对，口径不同）**

- 治理文档《机制治理与落实方案》摘要写的是：**LF-M01–LF-M53 中 34 个具门控、19 个仅源码文本引用；LF-M54 为独立 API 模块、不进入门控映射** → 34 + 19 + 1 = 54。**该表述实测成立**：把 LF-M54（`class_pet`）从 20 个中剔除，余下正是 19 个。
- 若按「全部 54 个」为分母，则未进步骤映射 = **20**。新近的《学习成瘾风险实时识别与自适应干预》稿件已自行把 19 更正为 20（该文档第 775 行「未进步骤映射 | 19 | **20**（34+20=54 闭合）」）。
- **结论：34 无争议；「19 vs 20」纯属是否把 LF-M54 计入的计数口径差异，两个数字均可复算，不是错误。** 论文须固定一个口径并标注分母。

---

### E1-3 三类冲突在本系统注册表内的实际检出

三处数据源：`mechanism_arbitrator.py` 的 `_DIRECTION` 方向表、`BudgetPolicy` 预算策略、`learning_orchestrator.py` 的真实 `Effect` 生产者。

```bash
cd "E:/learnflow/learnflow-backend" && "$PY" "$R/m2_conflict_analysis.py"
```

#### 类型 I · 效果方向冲突（语义对消）

- **方向表覆盖率**：`_DIRECTION` 只登记 **12/54** 个机制（`mechanism_arbitrator.py:102-107`）。
  - approach（9）：`LF-M07, M08, M10, M13, M25, M26, M33, M35, M44`
  - withdraw（3）：`LF-M51, M52, M53`
- **静态潜在对（上界）**：9 × 3 = **27** 对。
- **文档锚定的同 `target_construct`（=时长）实质对**：**2 对**
  - **LF-M44 错失恐惧（approach）↔ LF-M51 强制休息（withdraw）**
  - **LF-M44 错失恐惧（approach）↔ LF-M52 未成年保护（withdraw）**
- **运行时实际可检出 = 1 例，且消解发生在第 1 层而非第 2 层**：
  全仓库**只有 2 处**构造 `Effect`（`grep -rn 'mechanism_id=' app/services/*.py`）：
  - `LF-M44`：`deep_addiction_engine.py:296`，`user_visible=True, health_critical=False, cost=1.5, priority=50`
  - `LF-M52`：`learning_orchestrator.py:986`，`user_visible=False, health_critical=True, cost=0.0, priority=100`

  `_resolve_conflicts` 只在 **user_visible** 的 Effect 之间比较方向（`mechanism_arbitrator.py:344-349`），而 M52 是 `user_visible=False` → 第 2 层方向消解**不触发**；冲突实际由**第 1 层健康一票否决**（`mechanism_arbitrator.py:157-170`）消解，M52 丢弃全部 approach。
  **这是一个可直接写入论文的精确发现：本系统的结构性对立是「健康否决」语义，而非「方向消解」语义；第 2 层的方向消解在当前 Effect 生产者集合下是死代码。**

#### 类型 II · 预算竞争

- `BudgetPolicy`（`mechanism_arbitrator.py:44-53`）：`max_per_session=3`、`max_per_day=6`、`max_cost_per_session=4.0`、`min_interval_sec=300`。
- **运行时可见非健康候选 = 1（仅 LF-M44）** → 竞争对数 = **0**。LF-M52 因 `health_critical=True` 绕过预算（`mechanism_arbitrator.py:380-382`）。
- **结构性原因**：28 个步骤 13 的次级机制只产出**评估记录**（`decision_snapshot["mechanism_evaluations"]`，`learning_orchestrator.py:1105`），**不构造 Effect、不进仲裁器、不消耗预算**。
- **故：M2 所设计的「预算竞争」在当前系统里尚无可检出的现实载体**——这是必须在论文中如实标注的缺口（非零 ≠ 可检出）。

#### 类型 III · schema 归类冲突

- **治理 8 字母 → 注册表 5 类别是多对多**，实测 **7/8** 个字母跨 ≥2 个注册表类别：

  | 治理字母 | 落入的注册表类别 |
  |---|---|
  | A | motivation, retention |
  | B | motivation, retention |
  | C | cognition, motivation, selfreg |
  | D | motivation, retention, selfreg |
  | E | cognition, motivation, retention, selfreg |
  | F | motivation, retention |
  | G | cognition, motivation |
  | H | health ✓（唯一单一映射） |

- 含义：**两套分类学并不互为精化关系**。同一机制在治理文档属 A、在注册表属 `retention`，这是"归类冲突"在信息建模层面的真实体现。

---

### E1-4 不可归类比例

```bash
cd "E:/learnflow/learnflow-backend" && "$PY" "$R/m2_conflict_analysis.py"
```

| 口径 | 实测 | 比例 |
|---|---:|---:|
| 无法被赋予 `direction` 字段（schema 关键字段缺失） | **42/54** | **77.78%** |
| 无法落入治理 8 类 | 0/54 | 0% |
| 注册表类别体系维度 | 5 类（≠ 8 类） | — |

- 42 个无方向标注的 ID 全文见 `results/m2/m2_conflict_analysis.json` → `4_unclassifiable.no_direction_ids`。
- **口径说明**：任务问的「无法落入 8 类的机制占比」实测为 **0%**（治理文档 54 条全部有 A–H 归类）。但按 M2 所声明的 `Intervention = ⟨trigger, target_construct, direction, channel, cost, side_effect, precedence⟩` schema，本系统只有 `trigger`（=stage，54/54）与 `direction`（12/54）可得，`target_construct` / `channel` / `side_effect` / `precedence` **在代码中不存在**。因此**真正有意义的"不可归类比例"是 77.8%**。C1 所述"预期 10–20% 无法归类"过于乐观，应据实上修。

#### 附：描述统计（机制普查，Table 1 素材）

```bash
cd "E:/learnflow/learnflow-backend" && "$PY" "$R/make_table1.py"
```
产物：`table1_mechanism_census.csv` / `.tex`、`table1_summary.json`。

| 维度 | 分布 |
|---|---|
| stage | during 20 / pre 14 / ambient 13 / post 7 |
| maturity | complete **9** / partial **37** / placeholder **8** |
| disposition | R 32 / K 15 / M 6 / D 1 |
| direction | unassigned 42 / approach 9 / withdraw 3 |

> ⚠ **文档漂移**：治理文档《机制治理与落实方案》第 294 行写「9 完整 / 41 部分 / 4 占位」，实测为 **9 / 37 / 8**。新稿《学习成瘾风险实时识别与自适应干预》第 478 行已写 9/37/8，与实际一致。**建议以 9/37/8 为准，旧文档需更正。**

---

## E3 账本一致性 & 资产复算

### 资产数字

```bash
cd "E:/learnflow/learnflow-backend" && "$PY" "$R/harness.py" assets            # 基本
cd "E:/learnflow/learnflow-backend" && "$PY" "$R/harness.py" assets_pytest     # 含 pytest 收集
```

| 指标 | 登记基线 | 实测 | 判定 |
|---|---:|---:|---|
| python_loc | 25,389 | **25,687** | ⚠ drifted **+298** |
| source_files | 87 | **88** | ⚠ drifted **+1** |
| service_modules | 54 | **55** | ⚠ drifted **+1** |
| api_files | 13 | 13 | ✓ |
| api_routes_defined | — | 104 | — |
| api_routes_reachable | 104 | **104** | ✓（unreachable = 0） |
| test_files | 53 | **54** | ⚠ drifted **+1** |
| test_functions | 826 | **840** | ⚠ drifted **+14** |
| **tests_collected**（pytest 实收） | 920 | **934** | ⚠ drifted **+14** |

- 全部资产指标登记为 `strict=False` → 退出码 0（**PASS**）。
- **任务给出的基线 `loc≈25389` 已漂移**：实测 **25,687**（+298 行）。数值来自当前工作树复算（`verify_asset_numbers.py --with-pytest`）；`count_verification.json` 非审计时点封版物、git HEAD 不捕获未提交改动，故「checkout 8a328430 可复现旧值」不成立，论文引用须以本次复算 25,687 / 934 为准。
- `services=55 / routes=104 / tests=934` 实测（相对登记基线 54 / 920 各漂移 +1 / +14）。

### 建表脚本可移植性

```bash
cd "E:/learnflow/learnflow-backend" && "$PY" scripts/verify_schema_portable.py
```

- **SQLite：PASS** —— 13/13 条语句成功，6/6 张表建出（`user_xp_state, skill_defs, user_skill_tree, experiments, experiment_assignments, experiment_results`）。
- **MySQL：未实测** —— 环境无 `sqlglot`、无 MySQL 服务器。脚本如实输出「MySQL 脚本【未实测】，论文附件不得声称 MySQL 已验证」。**这是诚实的失败，不是通过。**

### 状态持久化

```bash
cd "E:/learnflow/learnflow-backend" && "$PY" scripts/verify_state_persistence.py
```

- **PASS** —— 9/9 项检查通过，退出码 0。含「模拟进程重启后 `total_xp` 仍为 150」「`members` 元素还原为 `TeamMember` 实例而非 dict」「`joined_at` 还原为 `datetime`」等关键项。

### impl_ref 引用完整性

```bash
cd "E:/learnflow/learnflow-backend" && "$PY" "$R/harness.py" implref
```

- **PASSED** —— 54 条全部 OK，0 警告(BLANK)、0 硬错误（MISSING/OUT_OF_RANGE/UNPARSEABLE）。

### 数字诚信总复算

```bash
cd "E:/learnflow/learnflow-backend" && "$PY" "$R/harness.py" counts
```

| 指标 | 登记 | 实测 | 状态 |
|---|---:|---:|---|
| engine_classes (L0) | 86 | 86 | verified |
| mechanism_units (L1) | 60 | 60 | verified |
| mechanism_unique (L2) | 54 | **54** | verified (strict) |
| learning_methods | 28 | 28 | verified (strict) |
| skill_tree_nodes | 16 | 16 | verified (strict) |
| prd_claimed | 69 | **69** | verified (strict) |

→ 结论 **VERIFIED，退出码 0**。附带的既有发现：PRD §2.3 表格求和 = 69，而同文档标题/概述写 76 → **PRD 内部自相矛盾**（`internally_inconsistent = true`）。

### ⚠ E3「账本」本体的诚实说明

任务描述的 E3 是「账本一致性检查（检出预算超支 / 被抢占却仍执行 / 决策无记录 三类违规）」。

```bash
cd "E:/learnflow/learnflow-backend" && grep -rln "budget_consumed\|preempted_by\|ledger" app/
# → 无任何匹配
```

- **仓库中不存在干预账本实现**：无 `budget_consumed`、无 `preempted_by`、无 ledger 模块。`ArbitrationTrace` 只在内存/单次调用中存在（`mechanism_arbitrator.py:56-68`），未落库为只追加账本。
- 与《期刊论文拆分方案》第 463 行的自述一致：「`budget_consumed` 与 `preempted_by` 字段尚未实现，须在实现章节如实标注为待完成项」。
- **因此 M2 所定义的「三类账本违规检出率」当前无法实跑**，不能产出数字。可实跑的替代物只有上表的 schema 可移植性、状态持久化与资产复算。**论文中不得声称已做账本一致性实验。**

---

## E2 跨项目复现（已完成 2 个外部系统）

网络经代理可用（`https_proxy=http://127.0.0.1:49349`，github.com / api.github.com / pypi 均 HTTP 200）。

```bash
cd "E:/learnflow/results/m2/external"
git clone --depth 1 https://github.com/DigiDago/moodle-format_ludilearn.git ludilearn
git clone --depth 1 https://github.com/FMCorz/moodle-block_xp.git block_xp
cd "E:/learnflow/results/m2" && "$PY" m2_e2_external.py
```

### 系统 A：Ludilearn（自适应游戏化 Moodle 课程格式）

- 仓库：`https://github.com/DigiDago/moodle-format_ludilearn`，commit `eb69582fb4def6e4cbb26c2146ceb90435951c53`，GPL-3.0，PHP。
- 机制清单枚举规则：`classes/local/gameelements/*.php` 去除抽象基类与 `nogamified` → **6 个机制**：`avatar, badge, progress, ranking, score, timer`。
- 该系统同时是 LudiMoodle+ 项目（法国 ANR e-FRAN / France 2030），**明确以「自适应游戏化」为卖点**，且有 Hexad 画像适配算法（`classes/local/adaptation/hexad_scores.php`）。

**检出结果**

| 冲突类型 | 检出 | 说明 |
|---|---:|---|
| 类型 I（严格：同 target 且反向） | **0** | `score` 等为 approach；`timer` 为 withdraw（超时扣分 `timer.php:46 DEFAULT_PENALTIES=20`），但 target 不同（参与度/表现 vs 时长/节奏） |
| 类型 I（放宽上界：任意 approach×withdraw） | 5 | 若忽略 target 匹配 |
| 类型 II 预算竞争 | **无预算概念**；4 个机制（badge/progress/ranking/score）写同一用户状态 | 无速率上限 |
| 类型 III 目标冲突 | **0** | 无合规/健康护栏机制 |

**关键结构性发现**：Ludilearn 的 6 个元素**互斥激活**——`manager.php:126-146` 的 `attribution_game_element()` 在赋给某 section 新元素前，先 `DELETE` 该 section 下其它元素的 attribution（SQL 条件 `sectionid=... AND type != ...`）。**因此即使放宽到任意方向对立，类型 I 冲突也不可能被激活**：同一 section 同一时刻只有一个游戏元素生效。

→ 复现结论：**M2 的多干预冲突问题在 Ludilearn 中「按构造不存在」**，因为它用「互斥分配」而非「仲裁」来回避冲突。这反向支持 M2 的问题定位：**冲突只有在多机制并存架构中才暴露**，而本项目的 54 机制并存正是稀缺样本。

### 系统 B：Level Up XP（`block_xp`）

- 仓库：`https://github.com/FMCorz/moodle-block_xp`，commit `65541fdc9c77511a906353f6660e195eeaa51893`，GPL-3.0，PHP。

**机制清单**（枚举规则：`classes/local/{xp,leaderboard,badge,rule,division,notification,check}` + `classes/form/{cheatguard,promo}`）→ **11 个机制**：
`xp_points, levels, leaderboard, rank, badge, notification, rules, rule_limits, division, cheatguard, promotion`

| 冲突类型 | 检出 | 说明 |
|---|---:|---|
| 类型 I（严格） | **0** | 无同 target 反向对 |
| 类型 I（放宽上界） | 18 | 2 个 withdraw（`rule_limits`、`cheatguard`）× 9 个 approach |
| 类型 II 预算竞争 | **存在，且有显式上限** | 5 个机制（xp_points/levels/leaderboard/rank/badge）写同一用户状态；`classes/local/ruletype/limit_spec.php` 提供 **H/D/W/M 四级速率窗口** + `timesallowed` 上限 → 这是外部系统里对「干预预算」的独立实现 |
| 类型 III 目标冲突 | **1** | `cheatguard`（合规，防作弊拦截）vs 全部 approach 机制 |

→ 复现结论：Level Up XP 是**纯参与度系统**（无健康/福祉护栏），因此 M2 的第 1 层「健康否决」语义**无对应物**；它的预算治理落在**速率窗口**（`limit_spec`）上，与 M2 第 3 层「会话/日/成本」预算**同构但不同粒度**。这为论文的 C3 提供了跨系统对照：**干预预算这一概念在工业界系统中确实独立出现并需要治理**。

### E2 方法学局限（必须如实写入论文）

1. **schema 字段为分析师单编码**（single-coder）：`target_construct` / `direction` / `channel` 是语义标注，外部系统**不自带** `direction` 元数据。每个编码均附 `file:line` 锚点（见 `m2_e2_external.json` 的 `schema` 字段），但**未计算评分者间信度（IRR）**，不得宣称双重编码。
2. **两系统均无 `target_construct` 字典**，故「严格类型 I」检出高度依赖编码判据；报告同时给出放宽上界以暴露该敏感性。
3. **样本量**：仅 2 个外部系统，且均为 Moodle/PHP 生态，语言与架构同源 → 外推性有限。M2 计划写 2–3 个；当前完成 2 个。

---

## 交付物清单

| 文件 | 内容 |
|---|---|
| `results/M2_results.md` | 本报告 |
| `results/m2/harness.py` | 只读运行器（重定向脚本输出，不写仓库） |
| `results/m2/fingerprint.json` | 54 / `ee1a49be5732` |
| `results/m2/mechanism_landing_status.json` + `.stdout.txt` | 落地矩阵 54/54、orphan 0 |
| `results/m2/count_verification.json` + `verify_counts.stdout.txt` | 六层计数复算（VERIFIED） |
| `results/m2/asset_numbers.json` / `asset_numbers_with_pytest.json` | 资产复算（loc 25687、tests 934） |
| `results/m2/impl_ref_integrity.json` + `check_impl_ref.stdout.txt` | 54/54 OK |
| `results/m2/m2_conflict_analysis.json` / `.py` / `.stdout.txt` | **三类冲突检测 + 8 类别 + 不可归类比例** |
| `results/m2/table1_mechanism_census.csv` / `.tex` / `table1_summary.json` | 54 机制普查表（Table 1 素材） |
| `results/m2/m2_e2_external.json` / `.py` / `.stdout.txt` | **E2 两外部系统冲突检出** |
| `results/m2/external/ludilearn/`、`external/block_xp/` | 外部系统浅克隆（含各自 commit） |

**未生成**：`table1_mechanism_census.xlsx`（后端 venv 无 `openpyxl`）。CSV + LaTeX 已备。

---

## 与任务预期的差异汇总（诚实清单）

| 任务预期 | 实测 | 判定 |
|---|---|---|
| 机制总数 54 | 54 | ✅ 一致 |
| 指纹 `ee1a49be5732` | `ee1a49be5732` | ✅ 一致 |
| **8 个理论类别** | 治理文档 8 类（A–H）成立；**但注册表 `CATEGORIES` 只有 5 个** | ⚠ 需在论文中区分两套分类学 |
| **门控映射 34** | 34 | ✅ 一致 |
| **仅文本引用 19** | 20（全 54 分母）；19（LF-M01–M53 分母） | ⚠ 口径差异，两者均可复算 |
| 资产 loc≈25389 | **25687** | ⚠ 漂移 +298 |
| services 54 / routes 104 / tests 920（登记基线） | 55 / 104 / 934 | ⚠ 漂移 +1 / +14 |
| E3 账本一致性可跑 | **账本本体未实现**（无 `budget_consumed`/`preempted_by`） | ❌ 无法产出数字，已如实说明 |
| E2 至少 1 个外部系统 | **2 个**（Ludilearn、Level Up XP），均 clone 成功并给出检出结果 | ✅ 超额完成 |
| MySQL 建表验证 | **未实测**（无 sqlglot / 无服务器） | ⚠ 如实标注失败 |

**未做的事（如实声明）**：未修改仓库任何文件；未做任何需要人类被试的实验；未声称任何机制对学习有效；未计算外部系统编码的 IRR。
