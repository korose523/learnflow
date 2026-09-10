# LearnFlow v2 · 基于区块链的大数据处理模块设计

> 作者：洗澄明（数据工程师） · 主理人：论笃行 · v1.0 · 2026-09-02
> 前置：`docs/LearnFlow_学术论文转化方案.md` · 代码基实测：后端 81 个文件 / 23,927 行（33 services、16 表）/ 868 passed（49 测试文件）

> 复算命令（后端规模）：`find app -name "*.py" | wc -l` 与 `find app -name "*.py" -exec cat {} + | wc -l`；测试数：`python -m pytest tests/ -q` → `artifacts/count_verification.json`，HEAD=79d7f36。

---

## 0. 结论先行

| 议题 | 结论 |
|---|---|
| 技术选型 | **FISCO BCOS 联盟链（4 节点，≥2 外部节点）做热锚 + OpenTimestamps 比特币做冷锚**；链下 PostgreSQL + Parquet 事件湖。不用 Fabric，不用以太坊 L2 |
| 链上存什么 | **只有 32 字节 Merkle 根 + 批次元数据 + 凭证撤销位**。单事件摊销链上占用 ≈ 0.6 字节 |
| 学术创新点 | ① 多尺度自适应锚定（系统向，保底）② 可验证因果审计轨迹（教育×可信交叉，王牌）③ 可编辑层次化 Merkle 承诺（隐私向，冲高） |
| 最大风险 | 不是技术，是**"为区块链而区块链"的审稿人偏见** + 单人多节点导致的"名不副实"质疑 |
| 最小可行版本 | 只做 `attempts` 重构 + 事件流 + Merkle + 本地 manifest（**零区块链**），2.0 人月，无论如何都值得做 |
| 工作量 | 5.5 人月（含 DB 迁移）；纯模块 4.5 人月。分 5 阶段，每阶段有独立可发表产出 |

**定位**：不做"教育区块链平台"（该赛道已烂大街），做**学习分析的可验证数据基础设施（Verifiable Data Infrastructure for Learning Analytics）**。区块链的角色是**时间戳与承诺的公证人**，不是数据库，不是业务逻辑载体。

---

## 1. 为什么需要区块链

### 1.1 审稿人第一个问题：MySQL + 审计日志不就够了吗？

**诚实回答：在单一机构、单一信任域内，确实够了。** 现有 `audit_logs` 已在做这件事。区块链只在下列条件**同时成立**时不可替代：存在 ≥2 个互不信任主体，需就"某数据在某时刻存在且此后未被改"达成一致，且不希望任何一方有特权改写权。本项目的博士研究场景恰好满足：

**(1) 跨机构学分互认 / 学习成果流转（最硬）**
论文方案 §5.2 要求与 1–3 个班级/学校合作。一旦有第二机构，就没有共同信任根：学校 A 的 DBA 可 `UPDATE attempts SET is_correct=1` 且不留痕迹（binlog 可 purge）。WAL / append-only 触发器 / 哈希链日志都只能防意外修改，**防不了特权者主动修改——因为它们的信任根与被审计对象是同一个**。区块链提供不隶属于任何参与方的时间戳服务。

**(2) 过程性评价的抗抵赖**
当过程数据用于高利害用途（计入期末成绩、竞赛选拔、自适应分组），学生/家长可合理质疑"平台是否事后补录改记录"。平台自证清白在逻辑上不成立（自己不能给自己作证）。链上时间戳提供 **backdating-resistant 存在性证明**：事后插入一条"看起来像上周产生的"记录需逆转共识。

**(3) 学习成果凭证的离线验证 + 撤销**
W3C VC 撤销状态必须挂在一个抗审查、抗单点关停的注册表上（StatusList2021 + 链上位串根）。朴素方案"验证方回调发证方 API"会让发证方知道"谁在何时向谁出示了凭证"，构成**可链接性隐私泄漏**。区块链的读操作免费、无日志。

**(4) 算法决策的因果可审计性 —— 本项目最锋利的点**
现有 `audit_logs` 的记录者就是决策者。做因果推断（"难度策略 A 相对 B 的 ATE"）时，SUTVA 与强可忽略性要求**处理分配机制的记录完整且未被事后修改**。若平台为结果好看而选择性补记/删改决策日志，因果结论不可复现且**外部无法检出**。把「决策输入协变量 X + 处理分配 T + 模型版本/参数摘要 M」一并 Merkle 锚定后，第三方可独立重跑估计并比对报告值；漏记可通过"锚定决策数 vs 事件流决策数"密码学检出。

### 1.2 哪些**不该**用区块链

| 数据/需求 | 判定 | 理由 |
|---|---|---|
| 鼠标移动、键盘敲击、心跳 | ❌ 链下 | 高写入低价值。只入摘要统计量，明细默认不采集 |
| 题目正文、作答原文、姓名学号 | ❌ 链下，**永不进链** | 含 PII。PIPL/GDPR 被遗忘权与不可删除性直接冲突，进链即违规 |
| 聚合指标（正确率、θ）、模型参数 | ❌ 链下 | 可由明细重算，无需独立存证 |
| 单机构内部中间状态、缓存 | ❌ 链下 | 无第三方验证需求 |
| 亚秒级读写查询负载 | ❌ 链下 | 区块链不是数据库 |
| 事件哈希、Merkle 根、凭证撤销位、DID 文档哈希 | ✅ 链上 | 见 §1.3 |

### 1.3 链上/链下分界线与数据流

```
┌──────────────── 链下（可删、可改、可高速查询）───────────────────┐
│  客户端 ──HTTP──▶ FastAPI ──▶ learning_orchestrator.submit_answer │
│                                    │                             │
│                    ┌───────────────┴──────────────┐              │
│                    ▼                              ▼              │
│          [A] PostgreSQL                   [B] Redis Stream       │
│          attempts(扩展)                   learnflow:events       │
│          learning_sessions                (consumer group)       │
│          engine_decision_logs                     │              │
│                    │                              ▼              │
│                    │                    Celery worker（异步）      │
│                    │                     • JCS 规范化 (RFC 8785)  │
│                    │                     • 会话子树构建            │
│                    │                     • 落 Parquet 事件湖      │
│                    │                              │              │
│                    │                              ▼              │
│                    │                   [C] Object Store (MinIO)   │
│                    │                   events/dt=2026-09-02/*.parquet
│                    │                   manifests/batch-4127.json  │
│                    └──────────┬───────────────────┘              │
│                               ▼                                   │
│                  [D] DuckDB 批处理：小时 rollup · 离线回放数据集    │
│                               │        · 完整性巡检                │
│                               ▼                                   │
│                  [E] 查询 API（毫秒级）+ /verify 返回包含证明       │
└───────────────────────────────┬───────────────────────────────────┘
                                │ 每 T 秒 或 每 N 条（先到者触发）
                                ▼ 仅提交 bytes32 root + 批次元数据
┌──────────────── 链上（只增不改、极小）────────────────────────────┐
│  FISCO BCOS 联盟链（4 节点，国密 SM2/SM3，无 gas）                 │
│    LearnFlowAnchor.anchorBatch(root, n_events, n_sessions,        │
│                                from_ts, to_ts, manifestURI, ver)  │
│    LearnFlowAnchor.issueCredential / revokeCredential / statusRoot│
│                                │                                  │
│              日根 ──▶ OpenTimestamps ──▶ 比特币（每周 1 次，零成本）│
│              抗"4 节点全被我控制"质疑的关键保险                     │
└───────────────────────────────────────────────────────────────────┘

单事件链上足迹：32B 根 / 1024 条每批 ≈ 0.03B，加元数据摊销 ≈ 0.6B/条
```

**合规要点**：链上无任何 PII，manifest 只含 salted hash；删链下原文 + 销毁 salt 即等价于「可验证删除」，天然满足 PIPL 第 47 条。链的存在不构成合规障碍。

### 1.4 预设质疑与反驳（直接写进论文 Related Work）

> **Q：这不就是 MySQL + 一个签名日志吗？**
> A：签名日志能防篡改，**不能防"签名者自己重写并重新签名"**。形式化区分：append-only log 的安全性基于"日志持有者诚实"；本方案基于"≥2f+1 节点中至少 f+1 诚实 + 比特币 PoW 不可逆转"。论文将给出二者在**特权敌手模型**下的对比实验（§5.2 攻击实验）。
>
> **Q：只有 4 个节点，还算区块链吗？**
> A：**不声称去中心化。** 声称的是"跨机构可验证性"，并在 threat model 中精确定义敌手能力上界：控制不超过 f 个联盟链节点，且无法逆转比特币 PoW。同时部署 ≥2 个外部机构持有的节点，使模型非空谈。
>
> **Q：学生数据上链不是永久留存吗？**
> A：链上只有 salted hash 与批次统计量。删除原文并销毁 salt 后，该记录的存在性证明**不可再生成**；§5.3 给出形式化定义与 O(log N) 重算代价。

---

## 2. 技术选型

### 2.1 四方案对比

| 维度 | Hyperledger Fabric | **FISCO BCOS** | 以太坊 L2 / 私链 + IPFS | Merkle + OpenTimestamps |
|---|---|---|---|---|
| 共识 / 吞吐 | Raft·BFT，3k–20k TPS | **PBFT/RPBFT，10k+ TPS** | PoS；L2 数百–数千 TPS | 无（BTC PoW，10 min 出块） |
| 部署成本 | 高：CA+Orderer+Peer+CouchDB，配置繁杂 | **低：`build_chain.sh` 一条命令起 4 节点，30 分钟** | 中：需 RPC 节点 + IPFS 网关 | **极低：pip 装即可，零节点** |
| gas | 无 | **无** | **有**（L2 按 ETH 计价） | **免费**（OTS 聚合批量写 BTC） |
| 国密 SM2/SM3 | 非原生，需自集成 | **原生，一行开关** | ❌ | ❌ |
| Python 集成 | 中偏高：官方 SDK 主推 Go/Node/Java | **低：原生 JSON-RPC，`httpx` 直连，无重 SDK** | 低：`web3.py` 最成熟 | **极低** |
| 节点门槛 | 1–2 核 | **1–2 核**（4 节点 docker-compose 单 4C8G 主机） | 需接入公共节点 | 0 节点 |
| 论文创新空间 | 大（通道隐私、私有数据集） | **大（无 gas ⇒ 锚定频率实验有自由度）** | 中（被 gas 成本锁死） | 小（只是工具） |
| 国内教育/政务落地 | 少 | **多**（教育存证、学分银行案例丰富） | 少（合规与币价风险） | 有（司法存证） |

### 2.2 推荐：FISCO BCOS（主）+ OpenTimestamps（冷锚）

1. **无 gas 是决定性优势。** 核心贡献之一是"锚定频率—成本—可验证延迟"的帕累托优化（§5.1）。在以太坊上，自变量（锚定频率）与因变量（成本）被 gas 价格锁死为线性关系，实验无自由度且不可复现（gas 波动）。联盟链无 gas，成本退化为"tx 数 × 存储字节"的确定性函数，可解析建模。
2. **国密原生 + 国内落地案例** → 对 CCF 中文刊（《软件学报》《计算机研究与发展》）审稿人是实打实加分；教育数据涉及未成年人，国产化合规不是套话。
3. **部署成本敏感，个人扛得住**：4 节点 docker-compose 单台 4C8G 云主机（≈¥100/月）；有条件把 2 节点放到合作学校/外部实验室，即成真实多主体。
4. **JSON-RPC 直连**，Python 侧只需 ~200 行 adapter。

**不选 Fabric**：功能最强但运维负担重，Python 生态弱于 Go/Node，会吃掉本应做研究的时间。**不选以太坊 L2**：gas 杀死核心实验自由度，且"公链存学生数据哈希"在国内教育场景有合规审查风险。**OTS 不做主链但必做冷锚**：免费、零运维，且即使我控制全部联盟链节点并重写历史，也无法篡改比特币上的日根时间戳。

---

## 3. 模块架构设计（六层）

### 3.1 采集层：`attempts` 重构（刚需，与区块链正交）

**实测好消息**：全后端 `Attempt(` 构造点只有 **1 处**（`learning_orchestrator.py:272`），新增列全部 nullable + 默认值 ⇒ 现有 33 个 service **零改动即可运行**。

**`learning_sessions`（新表）**

| 字段 | 类型 | 含义 |
|---|---|---|
| `id` / `user_id` | VARCHAR(36) | UUID4 / 外键索引 |
| `started_at` / `ended_at` | DATETIME(3) | 会话起止（UTC 毫秒） |
| `session_seq` | INT | 该用户第几次会话（序列建模） |
| `entry_point` | VARCHAR(32) | `home`/`assignment`/`review`/`recommend` |
| `client_ctx` | JSONB | 设备·OS·浏览器·屏幕·网络·时区·App 版本 |
| `device_fp` / `ip_prefix` | VARCHAR(64)/(48) | 设备指纹哈希；**IP 截断到 /24（v4）或 /48（v6）**，合规不存完整 IP |
| `event_count` | INT | 会话内事件数（冗余，供完整性校验） |
| `subtree_root` | BYTEA(32) | 该会话 Merkle 子树根（§5.3 可编辑结构的基础） |
| `ab_assignments` | JSONB | `{exp_id: group}` —— 修复 `ab_test_framework.py:104` 内存态丢失 |

**`attempts`（扩展，原 9 列全部保留不动）**

| 新增字段 | 类型 | 含义 / 研究用途 |
|---|---|---|
| `session_id` / `attempt_index` | VARCHAR(36) / SMALLINT | 会话归属 / 同一 task 第几次尝试 |
| `presented_at` / `responded_at` | DATETIME(3) | **展示 / 作答时刻分离**（关键） |
| `first_interaction_at` | DATETIME(3) | 分离"读题耗时"与"思考耗时" |
| `reading_ms` / `response_ms` | INT | 服务端算；取代不可靠的客户端 `time_spent` |
| `is_skipped` / `is_timeout` | BOOLEAN | 跳过 / 超时（二者区分） |
| `hint_levels_used` / `hint_timestamps` | JSONB | `[1,3]` 用了哪几层 + 请求时刻（现仅计数，丢信息） |
| `answer_normalized` | TEXT | 归一化作答（错因分析） |
| `self_confidence` | SMALLINT | 自评置信度 1–5（**元认知研究关键变量**） |
| `input_modality` | VARCHAR(16) | `choice`/`typing`/`voice`/`drag` |
| `interaction_flags` | JSONB | `{blur_count, tab_switch, idle_gap_s}` 走神信号 |
| `client_ctx` | JSONB | 逐条增量上下文 |
| `dda_decision_id` / `ab_assignment_id` | VARCHAR(36) | **因果审计：T 与 X 的绑定键** |
| `schema_version` | SMALLINT | 事件 schema 版本（数据可追溯） |
| `event_hash` / `prev_event_hash` | BYTEA(32) | Merkle 叶子 / **会话内哈希链**（第二层防篡改） |
| `anchored_batch_id` | BIGINT NULL | 已锚定批次（NULL = 待锚定） |

> **为什么 `response_ms` 必须服务端算**：`time_spent` 由客户端上报，可篡改/丢失、时钟不同步。三时间戳 + 客户端上报值并存，还可用于**测量客户端上报偏差分布**——本身即一个可报告的数据质量发现。

**`engine_decision_logs`（新表，因果审计核心）**
`id` · `user_id`(idx) · `engine`(idx) · `decision_type` · `input_snapshot` JSONB（**决策时刻完整协变量 X**）· `output_json` JSONB（决策 T）· `model_version` · `param_digest`（决策所用全部参数的哈希，防"事后调参再补记"）· `session_id` · `decided_at` · `event_hash`

> 此表修复「致命缺陷 2」：`meta_learning_skilltree.py:163 PLAYER_SKILLS`、`ab_test_framework.py:103-105`、`duolingo_addiction_engine.py` 的 XP/连胜状态驻留进程内存、重启即丢。落库后既是工程修复，也是因果推断所需的 treatment assignment 记录。

### 3.2 流处理层：Redis Stream（**不是 Kafka**）

**选型理由**：`requirements.txt` 已有 `redis==5.0.0` + `celery==5.4.0`。Kafka 需 JVM + KRaft，个人项目运维负担不成比例；目标规模 10⁴–10⁵ events/day（峰值 ~500/min），Redis Stream 的 consumer group 提供至少一次投递 + PEL 故障恢复，绰绰有余。接口用 ABC 抽象，**日均 >10⁷ 时可一行切 Kafka，业务代码不动**。

```python
# app/telemetry/schemas.py
from datetime import datetime
from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator

SCHEMA_VERSION = 1

class EventType(str, Enum):
    SESSION_START      = "session.start"
    TASK_PRESENTED     = "task.presented"       # 题目展示（与作答分离）
    HINT_REQUESTED     = "hint.requested"
    ATTEMPT_SUBMITTED  = "attempt.submitted"
    ATTEMPT_SKIPPED    = "attempt.skipped"
    SESSION_END        = "session.end"
    ENGINE_DECISION    = "engine.decision"      # 算法决策（因果审计）
    REWARD_GRANTED     = "reward.granted"

class ClientContext(BaseModel):
    device_type: Literal["desktop","mobile","tablet"] | None = None
    os: str | None = None
    browser: str | None = None
    screen: str | None = None                    # "1920x1080"
    net: Literal["wifi","4g","5g","ethernet","unknown"] = "unknown"
    tz_offset_min: int | None = None             # 本地时区偏移（昼夜节律分析）
    app_version: str | None = None

class LearningEvent(BaseModel):
    """统一事件信封。所有事件共此结构，payload 按 type 变。"""
    event_id: str                                # UUID4，客户端生成，幂等键
    schema_version: int = SCHEMA_VERSION
    event_type: EventType
    occurred_at: datetime                        # 客户端事件时刻（毫秒）
    server_received_at: datetime                 # 服务端接收时刻（时钟偏移估计）
    user_id: str
    session_id: str
    session_seq: int = 0
    # —— 关联键：因果审计的 T/X/Y 绑定 ——
    task_id: str | None = None
    dda_decision_id: str | None = None
    ab_assignment_id: str | None = None
    # —— 载荷 ——
    payload: dict[str, Any] = Field(default_factory=dict)
    client_ctx: ClientContext = Field(default_factory=ClientContext)
    ip_prefix: str | None = None                 # 已截断
    device_fp: str | None = None                 # 哈希后设备指纹

    @field_validator("payload")
    @classmethod
    def _no_pii(cls, v: dict) -> dict:
        """硬约束：payload 禁止出现 PII 键名，防误采。"""
        banned = {"name","real_name","phone","email","id_card","password","token"}
        hit = banned & {k.lower() for k in v}
        if hit:
            raise ValueError(f"payload 含禁用 PII 字段: {hit}")
        return v
```

**JSON 实例（可直接用作测试用例）**

```json
{
  "event_id": "9f1c2d3e-4a5b-6c7d-8e9f-0a1b2c3d4e5f",
  "schema_version": 1,
  "event_type": "attempt.submitted",
  "occurred_at": "2026-09-02T10:23:47.512Z",
  "server_received_at": "2026-09-02T10:23:47.680Z",
  "user_id": "u_7f3a", "session_id": "s_01J9Z", "session_seq": 12,
  "task_id": "t_5c81", "dda_decision_id": "d_9b22",
  "ab_assignment_id": "e_dda_v3:control",
  "payload": {
    "attempt_index": 1,
    "presented_at": "2026-09-02T10:22:31.004Z",
    "first_interaction_at": "2026-09-02T10:22:36.220Z",
    "responded_at": "2026-09-02T10:23:47.512Z",
    "is_correct": true, "answer_normalized": "B",
    "hint_levels_used": [1, 3],
    "hint_timestamps": {"1": "2026-09-02T10:22:58.100Z", "3": "2026-09-02T10:23:20.770Z"},
    "input_modality": "choice", "self_confidence": 4,
    "interaction_flags": {"blur_count": 1, "tab_switch": 0, "idle_gap_s": 12},
    "client_reported_time_spent": 76
  },
  "client_ctx": {"device_type": "desktop", "os": "Windows", "browser": "Chrome 141",
                 "screen": "1920x1080", "net": "wifi", "tz_offset_min": -480,
                 "app_version": "2.0.0"},
  "ip_prefix": "203.0.113.0/24",
  "device_fp": "8c1f0a...e3"
}
```

**投递语义**：主流程内 `XADD`（`MAXLEN ~ 500000`），失败降级到本地 `queue.SimpleQueue` 由后台线程重试 ⇒ 遥测不阻塞答题主链路、不丢事件。事件在写 PG 的**同一事务提交后**才投递，避免"事件已入流但事务回滚"的幽灵事件。

### 3.3 批处理层：DuckDB + Parquet（不用 Spark）

- **事件湖**：`s3://learnflow-lake/events/dt=YYYY-MM-DD/hour=HH/part-*.parquet`，Snappy；单日 10⁴ 条 ≈ 2 MB。
- **manifest**：`manifests/batch-{id}.json`，含批次内有序 `event_hash` 数组 + 元数据（**无任何原文**），供第三方独立重算根校验。
- **Celery beat**：每 10 min 攒批建树锚定（热锚）｜每小时 rollup（用户×知识点×小时的正确率/中位反应时/提示依赖率）｜每日 00:05 日根 + OTS 冷锚 + 完整性巡检（比对 PG 与 Parquet 行数、重算随机 1% 批次根）｜每周导出离线回放数据集。
- **`replay_dataset.py`**：导出 `(state, action, reward, next_state, timestamp, decision_id)` 六元组 Parquet，使 §5.2 的因果重跑可被第三方独立执行。

### 3.4 区块链锚定层

#### 3.4.1 三层多尺度锚定

| 层 | 触发 | 锚定对象 | 目标 | 载体 |
|---|---|---|---|---|
| **热锚** | `T=600s` 或 `N=1024` 叶子（先到者） | 批次根 | 锚定延迟 P99 < 15 min | FISCO BCOS |
| **温锚** | 每日 00:05 | 当日批次根构成的日根 | 便于对账 | FISCO BCOS（1 tx/日） |
| **冷锚** | 每周一 | 当周日根 | 抗联盟链合谋 | OTS → 比特币（0 成本） |

**为什么必须"自适应"而非固定周期**（这是 §5.1 的创新点，不是随手拍的参数）：学习事件流**强突发**——课间 10 分钟 spike 可达均值 30 倍，夜间近零。固定周期在 spike 时延迟爆炸、空闲时浪费批次。

#### 3.4.2 Merkle 规范（严格遵循 RFC 6962 域分离）

叶子与内部节点用不同前缀哈希，防止"内部节点被当作叶子提交"的第二原像攻击（自研 Merkle 的经典漏洞）。

```python
# app/ledger/merkle.py
from dataclasses import dataclass
import hashlib

LEAF_PREFIX = b"\x00"    # RFC 6962 §2.1
NODE_PREFIX = b"\x01"

class Hasher:
    """可切换：sm3（FISCO 国密模式）/ keccak256（EVM）/ sha256。"""
    def __init__(self, algo: str = "sha256"): self.algo = algo
    def __call__(self, data: bytes) -> bytes:
        if self.algo == "sm3":
            from gmssl import sm3                      # pip install gmssl
            return bytes.fromhex(sm3.sm3_hash(list(data)))
        return hashlib.new(self.algo, data).digest()

def leaf_hash(canonical: bytes, h: Hasher) -> bytes:
    return h(LEAF_PREFIX + canonical)

def node_hash(left: bytes, right: bytes, h: Hasher) -> bytes:
    return h(NODE_PREFIX + left + right)

@dataclass(frozen=True)
class MerkleTree:
    leaves: tuple[bytes, ...]
    root: bytes
    _h: Hasher

    @classmethod
    def build(cls, leaves: list[bytes], h: Hasher | None = None) -> "MerkleTree":
        """RFC 6962 语义：空树根 = H()；奇数节点提升到最后一位。"""
        h = h or Hasher()
        if not leaves:
            return cls((), h(b""), h)
        level = [leaf_hash(x, h) for x in leaves]
        while len(level) > 1:
            if len(level) % 2 == 1:
                level.append(level[-1])                # 显式提升，保证证明可重构
            level = [node_hash(level[i], level[i + 1], h) for i in range(0, len(level), 2)]
        return cls(tuple(leaves), level[0], h)

    def inclusion_proof(self, index: int) -> list[tuple[bytes, str]]:
        """[(sibling_hash, 'L'|'R')]，'L' 表示 sibling 在左。"""
        h = self._h
        level = [leaf_hash(x, h) for x in self.leaves]
        proof, idx = [], index
        while len(level) > 1:
            if len(level) % 2 == 1:
                level.append(level[-1])
            sib, pos = (level[idx + 1], "R") if idx % 2 == 0 else (level[idx - 1], "L")
            proof.append((sib, pos))
            level = [node_hash(level[i], level[i + 1], h) for i in range(0, len(level), 2)]
            idx //= 2
        return proof

def verify_inclusion(leaf: bytes, index: int, proof: list[tuple[bytes, str]],
                     root: bytes, h: Hasher | None = None) -> bool:
    h = h or Hasher()
    acc = leaf_hash(leaf, h)
    for sib, pos in proof:
        acc = node_hash(sib, acc, h) if pos == "L" else node_hash(acc, sib, h)
    return acc == root
```

**规范化（决定可复现性）——RFC 8785 JCS**

```python
# app/ledger/canonical.py
import json

def jcs_canonicalize(obj) -> bytes:
    """RFC 8785：UTF-8、键按 UTF-16 码元排序、无空白、数字用 ES6 Number::toString。
    生产用 pip install json-canonicalization；此处为无依赖实现（键序/分隔符/NaN 已处理）。"""
    def _sort(o):
        if isinstance(o, dict):
            return {k: _sort(o[k]) for k in sorted(o, key=lambda s: s.encode("utf-16-be"))}
        if isinstance(o, list):
            return [_sort(v) for v in o]
        return o
    return json.dumps(_sort(obj), ensure_ascii=False, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")

def event_leaf(event: dict, salt: bytes) -> bytes:
    """叶子 = JCS(事件) ‖ salt。salt 由 KMS 持有，销毁 salt 即实现可验证删除。"""
    return jcs_canonicalize(event) + salt
```

#### 3.4.3 链码（Solidity，FISCO BCOS 兼容）

```solidity
// contracts/LearnFlowAnchor.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.11;

/// @title 学习事件批次锚定 + 凭证状态注册表（链上只存承诺，零 PII）
contract LearnFlowAnchor {
    struct Batch {
        bytes32 merkleRoot;     // 批次 Merkle 根
        uint64  eventCount;
        uint64  sessionCount;
        uint64  fromTs;         // 毫秒 epoch
        uint64  toTs;
        uint16  schemaVersion;
        string  manifestURI;    // 链下 manifest（内容寻址）
        address submitter;
        uint64  blockTime;      // 链上可信时间源
    }

    Batch[] public batches;
    mapping(bytes32 => uint256) public rootToBatchId;   // 根去重
    uint256[] public dailyRoots;
    address public immutable owner;
    mapping(address => bool) public submitters;          // 各机构节点
    mapping(bytes32 => bool) public revokedVC;           // 凭证撤销位（精简版）

    event BatchAnchored(uint256 indexed batchId, bytes32 indexed root,
                        uint64 eventCount, uint64 fromTs, uint64 toTs);
    event DailyRootAnchored(uint256 indexed dayIndex, bytes32 root);

    modifier onlySubmitter() { require(submitters[msg.sender], "not authorized"); _; }
    constructor() { owner = msg.sender; submitters[msg.sender] = true; }
    function setSubmitter(address a, bool ok) external { require(msg.sender == owner); submitters[a] = ok; }

    // ---- 核心接口 ----
    function anchorBatch(bytes32 merkleRoot, uint64 eventCount, uint64 sessionCount,
                         uint64 fromTs, uint64 toTs, uint16 schemaVersion,
                         string calldata manifestURI)
                         external onlySubmitter returns (uint256 batchId);

    function anchorDailyRoot(bytes32 root, uint64 dayIndex) external onlySubmitter;

    function getBatch(uint256 batchId) external view returns (Batch memory);
    function latestBatchId() external view returns (uint256);
    function verifyInclusion(uint256 batchId, bytes32 leaf, bytes32[] calldata proof,
                             uint256 index) external view returns (bool);

    // —— 凭证状态（StatusList2021 位串根）——
    function issueCredential(bytes32 vcHash, bytes32 subjectDIDHash,
                             uint64 expiresAt) external onlySubmitter;
    function revokeCredential(bytes32 vcHash, bytes1 reason) external onlySubmitter;
    function isRevoked(bytes32 vcHash) external view returns (bool);
    function statusListRoot() external view returns (bytes32);
    function statusListEpoch() external view returns (uint64);
}
```

#### 3.4.4 Python 适配器（可插拔，L0 阶段零依赖）

```python
# app/ledger/backends/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass(frozen=True)
class AnchorReceipt:
    backend: str
    anchor_id: str | None        # 链上 batchId
    tx_hash: str | None
    root: bytes
    block_time_ms: int | None
    chain_ref: dict              # {chain, contract, block} 或 OTS 的 {ots_file_uri}

class AnchorBackend(ABC):
    @abstractmethod
    async def anchor(self, root: bytes, meta: dict) -> AnchorReceipt: ...
    @abstractmethod
    async def verify(self, receipt: AnchorReceipt, leaf: bytes, index: int,
                     proof: list[tuple[bytes, str]]) -> bool: ...

# app/ledger/backends/fisco.py —— 只需 JSON-RPC，无重 SDK
import httpx, time

class FiscoBCOSBackend(AnchorBackend):
    """FISCO BCOS JSON-RPC Channel。国密模式下交易签名走 SM2（见官方 python-sdk）。"""
    def __init__(self, rpc_url: str, contract: str, account_pem: str, sm_crypto: bool = True):
        self.rpc_url, self.contract, self.pem, self.sm = rpc_url, contract, account_pem, sm_crypto

    async def anchor(self, root: bytes, meta: dict) -> AnchorReceipt:
        payload = {"jsonrpc": "2.0", "id": 1,
                   "method": "call",
                   "params": [{"to": self.contract, "data": self._encode(
                       "anchorBatch", ["0x" + root.hex(), meta["event_count"],
                        meta["session_count"], meta["from_ts"], meta["to_ts"],
                        meta["schema_version"], meta["manifest_uri"]])}]}
        async with httpx.AsyncClient(timeout=10) as c:
            r = (await c.post(self.rpc_url, json=payload)).json()
        if r.get("error"):
            raise RuntimeError(f"FISCO anchor failed: {r['error']}")
        res = r["result"]
        return AnchorReceipt("fisco-bcos", str(int(res["logs"][0]["data"][-64:], 16)),
                             res["transactionHash"], root, int(time.time() * 1000),
                             {"chain": "fisco-bcos", "contract": self.contract,
                              "block": int(res["blockNumber"], 16)})

    async def verify(self, receipt, leaf, index, proof) -> bool:
        from app.ledger.merkle import verify_inclusion, Hasher
        return verify_inclusion(leaf, index, proof, receipt.root,
                                Hasher("sm3" if self.sm else "keccak256"))
```

同接口另有 `MemoryBackend`（测试）、`OpenTimestampsBackend`（冷锚）、`EthL2Backend`（备用）。切换只改环境变量 `LEDGER_BACKEND=memory|ots|fisco`。

### 3.5 凭证层：W3C VC（用 SD-JWT / RFC 9901，先务实不做 JSON-LD ZKP）

```jsonc
{
  "iss": "did:web:learnflow.edu.cn",
  "sub": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
  "iat": 1783000000, "exp": 1814536000,
  "vc_type": "LearningAchievementCredential",
  "credentialSubject": {                       // _sd 内各项可选择性披露
    "_sd": ["WyI...mastery_math_algebra",      // mastery: 0.87
            "WyI...attempts_count",            // 312
            "WyI...median_response_ms",        // 8420
            "WyI...evidence_batch_id"]         // 指向链上锚定批次
  },
  "evidence": {                                // ← 与 Blockcerts 的本质差异
    "type": "MerkleInclusionProof", "batchId": 4127,
    "merkleRoot": "0x9a3f...",
    "manifestURI": "s3://learnflow-lake/manifests/batch-4127.json",
    "verifier": "https://learnflow.edu.cn/verify"   // 独立校验器，离线可跑
  },
  "credentialStatus": {
    "type": "StatusList2021Entry",
    "statusListCredential": "https://learnflow.edu.cn/status/1",
    "statusListIndex": 8821, "statusPurpose": "revocation"
  }
}
```

**关键设计**：`evidence.merkleRoot` 使凭证**不是学校的自述，而是可回溯到原始事件流的密码学证据**——验证方可下载 manifest、重算根、与链上 `batchId` 的根比对，确认"这个掌握度数值确实由一批已被时间戳固定的事件算出"。MIT Blockcerts 只锚定凭证本身，不锚定生成凭证的证据链。

**选择性披露**：SD-JWT 让持有者只披露"代数掌握度 ≥ 0.8"而不暴露题数与反应时。撤销位根上链，验证方**批量拉取位串**，不向发证方泄露"谁在验证谁"。

### 3.6 查询层：链下高性能 + 链上可验证

- 常规查询走 PostgreSQL（B-tree / GIN），毫秒级，全链路不碰链。
- `GET /v1/ledger/verify/{event_id}` → `{event_hash, merkle_proof, batch_id, tx, chain_ref, ots_proof}`；任何第三方可用 `app/ledger/verifier.py` **离线独立校验**（该脚本不依赖 LearnFlow 任何服务，是论文可复现性包的一部分）。
- 前端"我的学习报告"页提供"验证此条记录"按钮，学生/家长可自行验证——把密码学能力暴露给被评价方，是**用户研究切入点**（可与团队 HCI 方向论文结合）。

---

## 4. 与现有代码的集成方案

### 4.1 新增目录树

```
app/
├── ledger/                      # 【新】区块链锚定层
│   ├── config.py                # LEDGER_BACKEND / 批次阈值 / 国密开关
│   ├── canonical.py             # RFC 8785 JCS + salt 管理
│   ├── merkle.py                # RFC 6962 Merkle（§3.4.2）
│   ├── policy.py                # 多尺度自适应锚定策略（创新点①算法）
│   ├── anchor_service.py        # 编排：攒批→建树→锚定→回写 anchored_batch_id
│   ├── manifest.py  verifier.py # manifest 生成 / 【独立可运行】离线校验器
│   └── backends/{base,memory,opentimestamps,fisco,eth_l2}.py
├── telemetry/                   # 【新】采集层
│   ├── schemas.py  emitter.py  context.py   # 事件模型 / XADD / UA·IP→ctx
│   ├── hooks.py  middleware.py  consumer.py # 装饰器 / 注入 session_id / 消费组
├── analytics/                   # 【新】批处理层
│   ├── jobs/{rollup_hourly,export_parquet,replay_dataset}.py
│   └── integrity_audit.py  duckdb_pool.py
├── credentials/                 # 【新】凭证层
│   └── issuer.py  presentation.py  status_list.py
├── models/
│   ├── telemetry.py             # 【新】LearningSession / Attempt 扩展 / EngineDecisionLog
│   └── ledger.py                # 【新】AnchorBatch / CredentialRecord / RevocationEpoch
└── services/audit.py            # 【仅扩展 8 行，签名行为不变】
```

### 4.2 与 `app/services/audit.py`：**扩展，绝不替换**

现有 `write_audit()` 是未成年人保护合规路径，**签名与行为 100% 不变**，仅在其事务内追加投递：

```python
# app/services/audit.py —— 仅新增 8 行
from app.telemetry.emitter import emit_best_effort   # 未启用时是 no-op

async def write_audit(db, kind, user_id=None, input_json=None, output_json=None,
                      subject=None, age_band=None) -> None:
    try:
        log = AuditLog(user_id=user_id, kind=kind, input_json=input_json or {},
                       output_json=output_json or {}, subject=subject, age_band=age_band)
        db.add(log); await db.flush()
    except Exception as e:
        logging.getLogger(__name__).warning("审计写入失败：%s", e)
        return
    # ↓ 新增：同步投递决策事件到遥测流（best-effort，永不阻断主流程）
    emit_best_effort({"event_type": "engine.decision", "user_id": user_id,
                      "payload": {"kind": kind.value, "input": input_json or {},
                                  "output": output_json or {},
                                  "subject": subject, "age_band": age_band},
                      "occurred_at": log.created_at})
```

另新增 `write_audit_verifiable(...)` 供**需强审计**的路径（难度决策、A/B 分组、风险判定）显式调用，写入 `engine_decision_logs` 并纳入 Merkle。旧的三参数调用点一个都不动。

### 4.3 新增 ORM 模型（`app/models/ledger.py`）

```python
class AnchorBatch(Base):
    """链上锚定批次的链下镜像（链上 tx 是真相来源，此表只是缓存+索引）"""
    __tablename__ = "anchor_batches"
    id              = Column(BigInteger, primary_key=True, autoincrement=True)
    tier            = Column(SAEnum(AnchorTier), nullable=False, index=True)  # HOT/WARM/COLD
    merkle_root     = Column(LargeBinary(32), nullable=False, unique=True, index=True)
    event_count     = Column(BigInteger, nullable=False)
    session_count   = Column(BigInteger, nullable=False)
    from_ts         = Column(BigInteger, nullable=False)          # 毫秒 epoch，避免时区歧义
    to_ts           = Column(BigInteger, nullable=False, index=True)
    schema_version  = Column(SmallInteger, nullable=False, default=1)
    manifest_uri    = Column(String(512), nullable=False)
    backend         = Column(String(16), nullable=False)          # fisco / ots / memory
    tx_hash         = Column(String(128), nullable=True)
    chain_ref       = Column(JSON, default=dict)                  # {contract, block, ots_uri}
    anchored_at     = Column(DateTime, default=lambda: datetime.now(UTC), index=True)
    parent_batch_id = Column(BigInteger, ForeignKey("anchor_batches.id"), nullable=True)  # 温/冷→热

class CredentialRecord(Base):
    __tablename__ = "credential_records"
    id                = Column(String(36), primary_key=True, default=_new_id)
    user_id           = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    vc_hash           = Column(LargeBinary(32), nullable=False, unique=True, index=True)
    sd_jwt            = Column(Text, nullable=False)
    status_index      = Column(Integer, nullable=False)           # StatusList2021 位索引
    evidence_batch_id = Column(BigInteger, ForeignKey("anchor_batches.id"), nullable=True)
    issued_at         = Column(DateTime, default=lambda: datetime.now(UTC))
    revoked_at        = Column(DateTime, nullable=True)
    revoke_reason     = Column(String(64), nullable=True)

class RevocationEpoch(Base):
    """撤销位串世代管理：根上链，位串链下公开（验证方批量拉取，防链接）"""
    __tablename__ = "revocation_epochs"
    epoch          = Column(Integer, primary_key=True)
    bitstring_gzip = Column(LargeBinary, nullable=False)
    root           = Column(LargeBinary(32), nullable=False)
    onchain_tx     = Column(String(128), nullable=True)
    created_at     = Column(DateTime, default=lambda: datetime.now(UTC))
```

### 4.4 数据库迁移建议：**必须迁到 PostgreSQL 14+**

| 诉求 | SQLite（现状兜底） | MySQL 8（现状默认） | **PostgreSQL 14+（推荐）** |
|---|---|---|---|
| append-only 事件表并发写 | ❌ 单写者，`database is locked` | ✅ | ✅ |
| 按月分区（事件表必然膨胀） | ❌ | ⚠️ 手工 partition，语法受限 | ✅ 声明式 `PARTITION BY RANGE` |
| JSONB + GIN（`client_ctx` 查询） | ❌ JSON 无索引 | ⚠️ 函数索引较弱 | ✅ 原生 |
| 32 字节哈希高效存储 | ⚠️ BLOB | ✅ BINARY(32) | ✅ bytea |
| `ON CONFLICT DO NOTHING`（事件幂等） | ✅ | ⚠️ `INSERT IGNORE` 语义有坑 | ✅ |

**迁移成本 2–3 人日**，可与 P0 并行。SQLAlchemy 2.0 已方言无关，工作量在类型变体 `JSONB().with_variant(JSON(), "mysql", "sqlite")` 与仅 PG 执行的分区 DDL。**MySQL 8 也能跑通全部功能**（仅失去分区与 GIN），故迁移不是阻塞项。

### 4.5 对 33 个 service 的侵入性：**实测极低**

```python
# app/telemetry/hooks.py
def audit_decision(engine: str, decision_type: str, model_version: str = "1.0"):
    """装饰器：自动记录算法输入协变量 X 与输出 T，零侵入业务函数体。
    用法：@audit_decision("optimal_difficulty", "difficulty", model_version="2.1")"""
    def deco(fn):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            result = await fn(*args, **kwargs)
            try:
                emit_best_effort({"event_type": "engine.decision", "payload": {
                    "engine": engine, "decision_type": decision_type,
                    "input": _extract_state(kwargs), "output": _safe(result),
                    "model_version": model_version}})
            except Exception:
                pass                                  # 遥测永不阻断主流程
            return result
        return wrapper
    return deco
```

| 钩子 | 涉及文件 | 改动 |
|---|---|---|
| `@audit_decision`（6 个决策点：难度·奖励·风险·下一题·分组·提示） | `optimal_difficulty.py`、`duolingo_addiction_engine.py`、`risk_monitor.py`、`learning_orchestrator.py`、`ab_test_framework.py`、`gamification_service.py` | 各 **+2 行** |
| FastAPI 中间件注入 `session_id` | `app/main.py` | **+3 行** |
| `Attempt` 扩展字段赋值 | `learning_orchestrator.py:272` | **+12 行** |
| `write_audit` 追加投递 | `audit.py` | **+8 行** |
| 其余 26 个 service | — | **0 行** |

**总侵入 ≤ 40 行、触及 8 个文件**，且 `TELEMETRY_ENABLED=false` / `LEDGER_ENABLED=false` 可一键关闭。

**「致命缺陷 2」的修复策略**：不改引擎内部实现，在引擎读内存态时**回源 DB**。以 `meta_learning_skilltree.py:163 PLAYER_SKILLS` 为例，新增 `SkillTreeStore` 适配器，`cls.PLAYER_SKILLS` 降级为 LRU 缓存，miss 时查 `engine_state_snapshots` 表。同样 2 行接入，不动 16 技能树任何逻辑。

---

## 5. 论文创新点（核心）

> CCF 分区以《CCF 推荐国际学术会议和期刊目录（2022）》为准，投稿前请核对本单位最新认定细则。

### 5.1 贡献一：多尺度自适应锚定的在线批处理优化（系统向 · 保底）

- **方向**：分布式系统 / 可信数据管理
- **科学问题**：给定有写入成本与确认延迟的锚定服务、以及**强突发**的事件到达过程，如何在线决定"何时攒批、批多大"，在**锚定延迟尾分布约束**下最小化链上成本？
- **Novelty**：
  - 现有存证工作（Guardtime、Factom、Blockcerts、各类"基于区块链的溯源"）几乎全用**固定周期或固定批量**，未把锚定决策建模为优化问题。
  - 本文形式化为**机会约束在线批处理**：`min Σ cost(batch_i) s.t. P(anchor_delay > τ) ≤ ε`（延迟 = 网络确认 + 排队 + 攒批）。
  - 提出 (a) 基于 Holt-Winters / 贝叶斯到达率预测的**阈值触发策略**，给出与最优离线策略的 **competitive ratio 上界**；(b) **Skip-list 稀疏锚定**——高峰只锚骨架层（每 2^k 叶锚 1 个），空闲后台补齐完整包含证明，把突发期延迟从 O(N) 降到 O(log N) 而成本几乎不增；(c) 三层多尺度的**成本–延迟–抗合谋三维帕累托前沿**解析模型。
- **为什么锋利**：**不依赖"教育"成立**。审稿人无法以"区块链+教育没新意"拒稿——这是纯分布式系统问题，教育只是负载来源。这是本设计最重要的风险对冲。
- **实验**：数据 = ① 真实部署事件流（≥1 学期、N≥60、≥30,000 事件）；② **EdNet-KT1**（~1.3 亿交互 + 真实时间戳分布）驱动负载仿真，构造可控 burst ratio 1×–50×；③ 合成 Poisson + 周期 spike 对照。基线 = 固定周期（60/300/900s）、固定批量（256/1024/4096）、每事件锚定、Guardtime 式定时公证 + (b) 的消融。指标 = `anchor_delay_p99`、`chain_tx/day`、单事件摊销链上字节、证明生成/验证耗时、相对最优的 regret、尾约束违反率。
- **Venue**：`IEEE TPDS`（CCF A，冲）→ `IEEE TSC`（CCF B）/ `ACM TOIT`（CCF B）→ `Future Generation Computer Systems`（CCF C, SCI IF≈6.2，**最现实落点**）→ 中文《计算机研究与发展》（CCF A 中文）。

### 5.2 贡献二：可验证因果审计轨迹 VCAT（教育 × 可信计算交叉 · 王牌）

- **方向**：可信计算 / 算法审计 / 学习分析（交叉）
- **科学问题**：自适应系统的算法决策（难度、反馈、分组）影响学生结果。做因果推断时，"处理分配记录是否被事后修改"目前**完全依赖平台自证**，外部无法检出。如何在不泄露隐私的前提下使因果结论**可独立复现、可密码学审计**？
- **Novelty**：
  - 现有"区块链+教育"（Sony Global Education、MIT Blockcerts、Learning Machine、EU EBSI Diploma）**只锚定结果**（成绩/证书），不锚定**决策过程**。它们能证明"张三得了 A"，不能证明"系统当初确实按声明策略给他推了难度 6 而非 3"。
  - 提出 **Causal Provenance**：把 `(X 协变量快照, T 处理分配, M 模型版本+参数摘要)` 与 Y 一起 Merkle 锚定，形成不可事后修改的"处理分配公证"。
  - 定义**审计完整性** `completeness = |anchored_decisions| / |decisions_in_stream|`，可通过比对链下事件流与链上批次计数**密码学检出漏记**（纯签名日志做不到：签名者可整批不签且无人知晓）。
  - 原语 `reproduce(anchor_id, decision_id) -> (X, T, Y)`，第三方可独立重跑 ATE 并比对论文报告值。与 `causal-analyst` 直接协同：本模块供数据基础设施，因果岗供估计方法与实证。
- **为什么审稿人买账**：命中"算法问责 / 可解释 AI / 研究可复现性"三个热点，且有真实合规驱动（未成年人保护、教育算法治理）。
- **实验**：真实部署 A/B（项目已有 `ab_test_framework.py`，现成优势），N≥60、≥12 周。基线 = ① 无锚定 audit log；② **纯签名 append-only log（必打的关键基线，用它展示"特权敌手可无痕改写"）**；③ 只锚结果不锚决策（对标 Blockcerts）。**攻击实验（论文亮点）**：模拟 DBA 执行 (a) 改历史决策 (b) 选择性删除 (c) 事后调参补记，测量各方案**检测率与检测延迟**；本方案目标 100% 检出、延迟 ≤ 1 锚定周期。指标 = 重算 ATE 与报告 ATE 偏差、审计完整性、漏记检测率、存储放大、P99 请求延迟增量（要求 < 5 ms）。
- **Venue**：`IEEE TLT`（SCI，系统+教育，最契合）→ `Computers & Education`（IF≈8.5，需强化教育实证）→ `FGCS`（CCF C）→ 中文《软件学报》《计算机学报》（CCF A 中文）。`ACM FAccT` / `AIES` 可先投 workshop 试水。

### 5.3 贡献三：可编辑层次化 Merkle 承诺 RHMC（隐私向 · 冲高）

- **方向**：可信计算 / 隐私工程
- **科学问题**：区块链不可删除 vs PIPL/GDPR 被遗忘权的结构性冲突；以及公开 manifest 导致的行为模式泄漏。
- **Novelty**：
  - 现有两种极端：(a) 只存哈希 → 无法删除（违反 PIPL 第 47 条）；(b) 变色龙哈希可编辑区块链（Derler et al., ESORICS 2019）→ 需复杂构造与陷门托管，工程难落地。
  - 提出**结构可编辑性**：Merkle 组织为「**用户子树 → 批次树**」两层。删除用户 u 全部数据 = 用 `TOMBSTONE_u` 替换其子树后**只重算 u 到根的一条路径**，代价 **O(log_d N) 次哈希 + 1 次链上交易**；新根 R' 与原根 R 的关系可由公开"删除证明"验证。相比变色龙哈希：(i) 无需陷门托管；(ii) 删除事件本身**上链留痕**，形成可审计的删除历史（合规审计员恰恰需要看到"你确实删了"）；(iii) 实现 < 100 行。
  - 量化**可验证性–隐私权衡**：给出 manifest 公开粒度 g 与去匿名化成功率的关系，及给定隐私预算下的最优粒度策略。
- **实验**：EdNet-KT1 做**成员推断 / 链接攻击**评估；真实部署数据测删除代价。基线 = 单用户删除全树重建 O(N)、变色龙哈希、链上存原文（合规反例）。指标 = 删除延迟、重算哈希数、删除证明大小与验证时间、去匿名化攻击 AUC、不可链接性、存储放大。
- **Venue**：`Computers & Security`（CCF B）→ `IEEE TDSC`（CCF A，冲）→ `FGCS`（CCF C）→ 中文《软件学报》（CCF A 中文）。

### 5.4 博士论文主线

> 命题：**《学习分析的可验证数据基础设施：多尺度锚定、因果审计与隐私保护》**
> 第 3 章 多尺度自适应锚定（性能）｜第 4 章 可验证因果审计轨迹（可信+因果）｜第 5 章 可编辑层次化承诺与隐私–可验证权衡（隐私）｜第 6 章 LearnFlow v2 实现与真实部署实证
>
> 主线：**在"高吞吐、强突发、含敏感个人信息"的学习事件流上，如何以最小代价获得最强可验证性，并在隐私约束下可撤销地维持它。** 三章构成"性能—可信—隐私"完整三角，不是三篇拼凑论文。

---

## 6. 落地风险与工作量

### 6.1 诚实的风险评估

| 风险 | 严重度 | 表现 | 缓解 |
|---|---|---|---|
| **"为区块链而区块链"审稿人抵触** | 🔴 最高 | 该领域低质论文多，条件反射式拒稿 | ① 题目/framing 回避"教育区块链"，改用 Verifiable Data Infrastructure；② Related Work 主动设 "Why not just a signed append-only log?" 并用**对比攻击实验**回答；③ 贡献一完全剥离教育语境对冲 |
| **节点数不足"名不副实"** | 🔴 高 | 4 节点全是自己的 → 可合谋重写 | ① ≥2 节点交合作学校/外部实验室持有；② **OTS 比特币冷锚**——即使联盟链全被控制也无法逆转 BTC 时间戳；③ 论文**不声称去中心化**，只称"跨机构可验证性"，threat model 中给出敌手能力上界 |
| **零真实用户数据** | 🟠 中高 | 868 个测试全是单元测试（49 测试文件） | 先用 **EdNet-KT1 驱动仿真**完成贡献一（性能实验只需真实负载形状，不需真实教育数据）；贡献二必须等真实数据。数据战略见论文方案 §5.2 |
| **部署运维成本** | 🟡 中 | FISCO 4 节点长期维护 | docker-compose 单主机起步（≈¥100/月），运维脚本化（`make chain-up/chain-health/chain-backup`）；**OTS 冷锚零运维**，联盟链挂掉也不影响数据可信性 |
| **工程挤占研究时间** | 🟡 中 | 博士核心产出是论文 | 严守 L0→L3 分阶段，**每阶段独立可发表**；L0（零区块链）已能支撑贡献二所需全部数据基础设施 |
| **未成年人数据合规** | 🟡 中 | 教育数据上链需过伦理审查 | 链上零 PII；`ConsentRecord` 已有 `DATA_RESEARCH` / `PARENT_BINDING` 类型可复用；`LEDGER_ENABLED=false` 使不参与研究的用户完全不进流 |
| **审稿周期** | 🟢 低 | 区块链期刊 6–12 个月 | L1 完成即投 workshop/short paper 试水 |

### 6.2 降级方案（MVP = L0）

**零区块链，2.0 人月，无论后续做不做链都值得做：**

1. `attempts` 重构（§3.1）+ `learning_sessions` + `engine_decision_logs`
2. Redis Stream 事件流 + Celery consumer 落 Parquet
3. RFC 8785 规范化 + RFC 6962 Merkle + 本地 manifest 落盘
4. 完整性巡检 + 离线校验器 `verifier.py`
5. 修复内存态丢失（`PLAYER_SKILLS` / AB 分组 / XP 状态落库）

**MVP 已解决**「致命缺陷 1」（字段缺失）与「致命缺陷 2」（状态丢失），并产出可复现、带密码学完整性保证的学习事件数据集——这本身就是**贡献二所需的全部数据基础设施**，也是任何学习分析论文的硬通货。

**渐进升级（每级独立可发表）**：**L1**（+0.5 人月）接 OTS 冷锚 → 免费零运维，立刻具备不可篡改时间戳，可投 workshop；**L2**（+1.5 人月）FISCO 热锚 + 链码 + 多尺度策略 + EdNet 仿真实验台 → **贡献一完整成立**；**L3**（+1.5 人月）VC/SD-JWT + StatusList2021 + 可验证删除 → **贡献三成立**。

### 6.3 路线图与工作量

| 阶段 | 内容 | 人月 | 产出 |
|---|---|---|---|
| **P0 地基** | DB 迁移评估（→PG）、`attempts` 重构 + 3 新表、Alembic 迁移、回填、868 测试全绿（49 测试文件） | 1.0 | 可用事件数据集；修复缺陷 1、2 |
| **P1 流与树（=L0 MVP）** | Redis Stream、Celery consumer、JCS 规范化、RFC 6962 Merkle、manifest、DuckDB rollup、完整性巡检、离线 verifier | 1.0 | 可复现事件湖；论文 Data Infrastructure 章节 |
| **P2 冷锚（L1）** | OTS 适配器、周级冷锚调度、验证 API、前端"验证此记录" | 0.5 | 时间戳公证；workshop/short paper |
| **P3 联盟链（L2）** | FISCO 4 节点（含 2 外部）、Solidity 链码、JSON-RPC 适配器、多尺度策略、EdNet 负载仿真实验台 | 1.5 | **贡献一（系统向论文）** |
| **P4 凭证隐私（L3）** | SD-JWT 签发/披露、StatusList2021、RHMC 可验证删除、EdNet 去匿名化实验 | 1.5 | **贡献三（隐私向论文）** |
| **P5 实证** | 真实部署、A/B 主实验、特权敌手对比实验、因果重跑 | 与数据战略并行，不计入本模块 | **贡献二（教育×可信论文）** |
| **合计** | **P0–P4 = 5.5 人月**（纯模块 4.5；MVP=L0 仅 2.0） | | 3 篇期刊 + 博士论文 3 章 |

---

## 附录 A · 关键配置

```bash
# .env 新增（全部有安全默认，未配置时模块降级为 no-op）
TELEMETRY_ENABLED=true
TELEMETRY_STREAM=learnflow:events
TELEMETRY_MAXLEN=500000

LEDGER_ENABLED=false                 # 开发默认关；P2 起打开
LEDGER_BACKEND=memory                # memory | ots | fisco | eth_l2
LEDGER_HASHER=sm3                    # sm3 | keccak256 | sha256
LEDGER_HOT_MAX_WAIT_S=600            # 热锚：最大等待
LEDGER_HOT_MAX_LEAVES=1024           # 热锚：最大叶子数
LEDGER_WARM_CRON="5 0 * * *"         # 温锚：日根
LEDGER_COLD_CRON="0 3 * * 1"         # 冷锚：OTS → BTC

FISCO_RPC_URL=http://127.0.0.1:8545
FISCO_GROUP_ID=group0
FISCO_CONTRACT_ADDR=0x...
FISCO_ACCOUNT_PEM=./keys/node0.pem
FISCO_SM_CRYPTO=true

KMS_SALT_KEY_ID=learnflow/event-salt  # salt 托管，销毁即删除
```

## 附录 B · 新依赖（全部可选，MVP 不强制）

```txt
json-canonicalization>=0.2     # RFC 8785 JCS（MVP 可用内置实现替代）
duckdb>=1.0                    # 嵌入式 OLAP（替代 Spark）
pyarrow>=16.0                  # Parquet
sd-jwt>=0.4                    # SD-JWT 选择性披露（L3）
opentimestamps-client>=0.7     # OTS 冷锚（L2）
gmssl>=3.2                     # 国密 SM2/SM3（FISCO 国密模式，L2）
# redis>=5.0 / celery>=5.4 已有
```

## 附录 C · 与其他岗位的接口约定

| 对接方 | 本模块提供 | 需要对方提供 |
|---|---|---|
| `causal-analyst` | `reproduce(anchor_id, decision_id) -> (X,T,Y)`；审计完整性指标；A/B 分组不可篡改记录 | 哪些协变量需进 `input_snapshot`；ATE 复现要求 |
| `robustness-auditor` | 完整性巡检报告；特权敌手攻击实验台（改/删/补记三种攻击） | 威胁模型形式化表述；检测率统计口径 |
| `lit-reviewer` | 技术选型对比表；三位候选 venue 的相关工作地图 | Blockcerts / Guardtime / Factom / 可编辑区块链的精确对标文献 |
