# LearnFlow 学习成瘾化研究：测量框架与实现基线

> 本文是 LearnFlow「学习成瘾化」研究主线的**测量层权威文档**。
> 它回答一个审稿人一定会问、而此前的文档集答不上来的问题：
> **LAI 的五个维度，各自究竟是怎么测出来的？哪些维度其实测不到？**
>
> 文中每一个数字都可由 `learnflow-backend/scripts/` 下的脚本或代码路径复算。
> 基线提交以 `README.md` 记录为准。

---

## 一、为什么需要这篇文档（缺陷披露）

LAI（学习成瘾化指数）采用五维加权框架：

| 维度 | 权重 | 语义（分越高越健康） |
|---|---|---|
| `time` 时间投入 | 0.30 | 时长 / 单次会话长度 / 夜间比例 |
| `motivation` 动机结构 | 0.25 | 内在动机占比、外在奖励依赖 |
| `control` 行为控制 | 0.25 | 能否按计划停止 |
| `cognition` 认知 | 0.10 | 内容专注度、时间感知偏差 |
| `function` 功能影响 | 0.10 | 对睡眠与社交的损害 |

**此前的实现缺陷**：`control`(25%) 与 `function`(10%) 共 **35% 的权重**，其输入
（`planned_stop_failures` / `sleep_impact` / `social_impact`）**在 `Attempt` 行为日志中
根本没有对应字段**，因此被填充为常量 `0`。而这三个输入的方向是「值越大越不健康」，
取 0 即等于**恒定为最健康**。

后果是结构性的：这两维在任何输入下都给出满分，使 LAI 综合分被系统性抬高，
**索引在设计上就无法把行为控制或功能损害判定为风险**。这不是参数调优问题，
而是测量效度问题——它会让 LAI 在论文中的所有实证结论失去意义。

**修复原则**：不允许未被测量的维度静默地按「健康」计分。按此原则实施三项改动：

1. 建立**自陈测量基础设施**（本文 §三），使这些维度第一次有了真实数据来源；
2. 令 LAI 的评分**显式接收「哪些维度已测」**（`measured_dimensions`），未测维度从加权中剔除、
   权重在已测维度上重新归一化，并在输出中携带 `coverage` 覆盖度报告；
3. 在所有对外披露 LAI 分数的地方，**同时披露覆盖度**——引用一个基于 55% 权重的分数时，
   必须说明它基于 55%。

---

## 二、双源测量设计

单一数据源无法覆盖五维。本研究的测量架构是**双源**的：

| 测量源 | 采集方式 | 可观测内容 | 覆盖维度 |
|---|---|---|---|
| **行为日志** | `Attempt` 表自动留痕 | 学习时长、单次会话时长、夜间学习比例、正确率、提示依赖 | `time`、`motivation` |
| **自陈量表** | 学生本人填写（§三） | 停止控制、睡眠影响、社交影响、时间感知偏差 | `control`、`function`、`cognition` 的时间偏差子项 |

行为源覆盖 55% 权重，自陈源补上剩余 45%。两者**不是互相验证的关系**，而是**互补**关系：
行为日志测「做了什么」，自陈测「体验如何」。二者不可互相替代。

### 代理指标的诚实标注

`time` 与 `motivation` 虽由行为日志支撑，但其构造是**代理指标**而非直接观测：

- `intrinsic_motivation_ratio` 由「平均提示使用次数」反推，是**提示依赖的代理**，
  不等于自陈的内在动机（后者需要专门的动机量表，尚未实现）；
- `content_attention_ratio` 由「正确率」线性映射，是**表现代理**，不等于注意力；
- `connection_quality`（Hari C1 社会连接替代）当前为固定默认值 0.7，**未被测量**。

这些代理关系在 `coverage.proxy_dimensions` 中显式列出，且在论文的方法学局限性中
必须声明。**不得**将这些代理指标描述为「内在动机测量」或「注意力测量」。

---

## 三、自陈测量基础设施

### 3.1 量表目录（`app/services/instrument_catalog.py`）

四份量表，目录指纹 `3531e875d286`：

| 量表 code | 名称 | LAI 维度 | 题项 | 题型 | 映射到 LAI 输入 |
|---|---|---|---|---|---|
| `SRL-STOP` | 学习停止控制量表 | `control` | 3 | 计数（0..7 次/周） | `planned_stop_failures`（三题求和） |
| `SLEEP-IMPACT` | 学习对睡眠影响量表 | `function` | 4 | Likert 1..5 | `sleep_impact`（均值归一化 `(mean−1)/4`） |
| `SOCIAL-IMPACT` | 学习对社交影响量表 | `function` | 4 | Likert 1..5 | `social_impact`（均值归一化） |
| `TIME-BIAS` | 时间感知偏差量表 | `cognition` | 3 | Likert 1..5 | `time_perception_bias`（均值归一化） |

计分口径在提交时**冻结**在记录上（`raw_total` / `normalized` / `catalog_fingerprint`），
使日后题项或计分规则变更时，历史数据仍能复现其原始分数，而不会被新规则追溯改写。

### 3.2 ⚠️ 量表题项来源与信效度局限（必须声明）

四份量表的题项均为**本项目自行编写（purpose-built）**，**并非**照搬受版权保护的既有量表
（如 Bergen 社交媒体成瘾量表 BSMAS、DSM-5 网络游戏障碍 IGD-9 条目）。

| | 说明 |
|---|---|
| **好处** | 无版权与授权问题；题项可直接对齐本系统的模型输入（外部量表通常不能） |
| **代价** | **自编题项尚未经过独立信效度检验**（无重测信度、无结构效度、无与既有量表的聚合效度证据） |

因此：

- 任何引用这些量表结果的研究材料**必须**在局限性中声明该事实；
- **不得**宣称这些题项「已验证」「已标定」「已被效度检验」；
- **不得**仅凭本量表分数做临床或病理学判断；
- 「自编量表的信效度验证（重测信度 / 内部一致性 / 与 BSMAS、IGD-9 的聚合与区分效度）」
  本身是一个有方法学贡献的后续可发表方向——当前状态是**待验证**，不是**已验证**。

### 3.3 数据新鲜度

自陈作答有效期 **28 天**（`self_report_service.MAX_AGE_DAYS`）。超过有效期的记录
不再支撑当前评分，防止用数月前的一次作答永久维持一个结论。

### 3.4 覆盖度契约

维度「已测」的判定规则：

- `time` / `motivation`：无自陈要求，由行为日志代理支撑，**恒视为已测**；
- `control`：需 `SRL-STOP` 有效作答；
- `function`：需 `SLEEP-IMPACT` **与** `SOCIAL-IMPACT` **同时**有效（缺一即未测）；
- `cognition`：需 `TIME-BIAS` 有效作答。

由此得到的权重基础（`coverage.weight_basis`）：

| 已采集的自陈数据 | 已测维度 | 权重基础 |
|---|---|---|
| 无 | time, motivation | **0.55** |
| + `SRL-STOP` | + control | 0.80 |
| + `SLEEP-IMPACT` + `SOCIAL-IMPACT` | + function | 0.90 |
| + `TIME-BIAS` | + cognition | 1.00 |

**零自陈数据时 LAI 只基于 55% 的权重**。这是设计意图，不是缺陷：它把「测不到」
如实报告出来，而不是用假数据把分数凑满。

---

## 四、接口与代码路径

### 4.1 自陈测量 API（`app/api/instrument.py`，前缀 `/api/v1/instruments`）

| 方法 | 路径 | 用途 |
|---|---|---|
| `GET` | `/instruments` | 量表列表（含题项），可按 `?dimension=` 过滤 |
| `GET` | `/instruments/catalog` | 目录元信息 + 指纹（论文中锚定测量版本用） |
| `GET` | `/instruments/{code}` | 单份量表题项 + 计分方法 |
| `POST` | `/instruments/{code}/responses` | 提交作答（服务端计分并落库） |
| `GET` | `/instruments/me/responses` | 本人作答历史 |
| `GET` | `/instruments/me/coverage` | 本人 LAI 测量覆盖度 |

> **本模块不登记为游戏化机制。** 它是**测量基础设施**而非行为干预机制，
> 故不进入 `mechanism_registry`——权威机制计数保持 **54**（`LF-M01`…`LF-M54`）不变。
> 其干预侧对应物是既有的 `LF-M53`（LAI 自适应降级）；本模块只负责把该降级决策
> 所依赖的输入变成真实测量所得，不自行实施干预。

### 4.2 LAI 评分接口

```python
LearningAddictionIndex.assess(..., measured_dimensions={"time", "motivation", "control"})
```

- `measured_dimensions=None`（默认）：**旧口径**，等价于「五维均已测」，仅为向后兼容保留；
  **新的调用方不应使用**。
- 传集合：未测维度 `weighted_score = 0`、`measured = False`、不报 `risk_flag`；
  权重在已测维度上重新归一化（保持 0–100 量纲）。
- 空集或含未知维度名 → `ValueError`（拒绝用错口径产生看似合理的分数）。
- 返回值新增 `coverage`：
  `{explicit, measured, unmeasured, weight_basis, complete}`。

### 4.3 行为日志侧聚合（`app/api/gamification.py`）

`_aggregate_lai_inputs()` 从近 7 天 `Attempt` 聚合行为指标后，由
`_with_self_report()` **叠加**新鲜自陈值（自陈是直接观测，优先级高于行为代理）。
`GET /api/v1/gamification/lai/dashboard` 随后：

```python
measured = await measured_dimensions(db, target.id)
assessment = lai_engine.assess(**inputs, measured_dimensions=measured)
result["measurement"] = await coverage_report(db, target.id)
```

即仪表盘的响应中**同时**包含分数与其测量覆盖度，使任何消费该分数的下游
（前端、论文、家长报告）都无法在不看到覆盖度的情况下引用分数。

### 4.4 数据落盘

| 组件 | 位置 |
|---|---|
| 量表目录 | `app/services/instrument_catalog.py` |
| 作答模型 | `app/models/instrument.py`（表 `self_report_responses`） |
| 聚合 / 覆盖度 | `app/services/self_report_service.py` |
| API | `app/api/instrument.py` |
| 回归测试 | `tests/test_self_report_measurement.py`（22 项） |

---

## 五、数据伦理边界

`self_report_responses` 存放的是**未成年人自陈的心理与行为数据**（睡眠、社交、自控感受），
敏感度高于普通业务数据。约束：

| 约束 | 实现 |
|---|---|
| **数据最小化** | 仅采集量表所需字段，不记录设备、位置等标识 |
| **仅本人可读写** | `user_id` 强制取自登录态，不接受请求体传入；无全表导出端点 |
| **同意范围** | 提交时解析 `ConsentType.DATA_RESEARCH` 状态并**标记**在记录上（`context.research_consent`）；采集属产品功能，同意状态用于研究分析时的样本筛除，依既有设计**不阻断**提交 |
| **归档排除** | **不得**随代码仓库或公开 artifact 归档（与 `artifacts/state/`、`artifacts/experiments.json` 同级处置） |
| **伦理审查** | 涉及人类被试的研究须先取得伦理审查批准；本基础设施提供采集能力，**不构成**伦理批准 |

> 未成年人的研究同意依 `research_consent` 模块判定：未成年被试必须由**家长角色**
> 授权，学生自授无效。标记式判定永不抛异常，绝不允许同意判定失败导致提交 500。

---

## 六、当前局限（论文中必须声明）

1. **自编量表未经信效度检验**（§3.2）——这是本测量体系最重要的局限。
2. **45% 权重依赖自陈**，而自陈存在社会赞许性偏差（学生可能低报睡眠/社交损害），
   方向性后果是**低估**成瘾风险。
3. **`motivation` 与 `time` 为代理指标**（§二），非直接观测。
4. **`connection_quality` 未被测量**，当前为固定默认 0.7。
5. **测量覆盖度随时间波动**：28 天有效期意味着覆盖度会随作答过期而下降，
   跨时间的 LAI 分数比较必须同时比较覆盖度。
6. **未做测量不变性检验**（跨学段 / 性别的因子结构一致性），因此跨群体比较需谨慎。

上述局限不是「待补的边角」，而是本研究**方法学贡献的一部分**：把测量效度问题
显式暴露出来，本身即区别于常见的「用一个未验证的综合指数作结论」的做法。
「自编量表的信效度验证」是明确的后续工作，且可直接支撑一篇独立的方法学论文。

---

## 七、与既有文档的关系

| 文档 | 关系 |
|---|---|
| `docs/LearnFlow_抗成瘾层_论文表图.md` | 抗成瘾层的**结果**表图（LAI 场景对比、仲裁器降权） |
| `docs/LearnFlow_学习成瘾化研究_补充文献测绘.md` | 成瘾化的**理论文献**支撑（A 心理学 / B 游戏设计 / C 实证） |
| `docs/LearnFlow_机制治理与落实方案.md` | 54 个机制的治理与落地状态（权威机制计数） |
| `docs/_重写规范_事实基线与学术体例.md` | 数字口径与学术体例的强制规范 |
| **本文** | 成瘾化研究的**测量层**权威定义与诚实边界 |

**写作顺序约束**：本文的数字（指纹、题项数、权重基础、覆盖度）均为代码事实。
任何文档若要引用，必须先由 `verify_asset_numbers.py --doc-check` 与
`instrument_catalog.catalog_fingerprint()` 复算，不得手工填写。
