"""游戏化机制注册表 — LearnFlow 53 个游戏化/成瘾机制的单一事实源 (single source of truth)

背景
----
LearnFlow 的 53 个游戏化机制此前只存在于 ``docs/LearnFlow_机制治理与落实方案.md``
的 §2.4 清单表里, 运行时代码里没有任何统一枚举入口。``learning_orchestrator.py``
的 ``process_submission`` 用 11 个硬编码步骤把其中几个机制（宠物 LF-M22 / XP 等级
LF-M19 / 未成年保护 LF-M52 / 强制休息 LF-M51 / 风险监控 LF-M53）直接写死, 无法开关、
无法审计「这一步对应哪个机制」。

本模块把全部 **53** 个机制收敛为声明式注册表, 与 ``method_registry.py``（学习方法）
同构: 可枚举、可开关、可统一查询。每个机制带稳定 ID (``LF-M01``..``LF-M53``)、
生命周期阶段 (stage)、理论类别 (category)、理论来源 (theory_ref)、实现位置 (impl_ref)、
治理处置 (disposition: K 保留 / M 合并 / R 重构 / D 废弃)。

ID 稳定性约定
-------------
``LF-M`` 系列专属于**游戏化机制**, 与学习方法的 ``LF-L`` 系列互斥。ID 一经分配即冻结,
不得复用或重排; 新增机制只能追加新序号 (当前封顶 LF-M53)。

impl_ref 的语义差异（重要）
--------------------------
学习方法的 ``impl_ref`` 是 ``module.py:Symbol.path[0]`` 形式的**符号路径**, 可 importlib
动态解析校验；而机制的 ``impl_ref`` 是 ``file.py:line`` 形式的**文档位置引用**（治理文档
经 grep 核验得来）, 很多条目是双位置（canonical + 重复实现）或 ``ux:345`` 简写, 无法做
符号级解析。因此本注册表只把 ``impl_ref`` 当作**必填的文档引用字符串**校验（非空、形态
宽松）, 不做 importlib 符号解析——机制级别的「实现真实性」由治理文档的 grep 核验与
``verify_counts.py`` 的 AST 复算共同保证。

impl_ref 的行号漂移风险（已知技术债）
----------------------------------
``file.py:line`` 形式的行号会随源码编辑**静默失效**——任何在被引用位置上方的
插入/删除都会使行号指向错误内容，而本注册表与 ``scan_mechanism_landing.py``
都**不校验行号**（后者只取 ``:`` 之前的文件名）。这直接损害论文的可追溯性：
审稿人按 impl_ref 定位时会看到无关代码。

约定：
  * **新增或修改条目时优先使用符号级引用** ``file.py:SymbolName``，抗漂移；
  * 既有行号条目保留原样，但由 ``scripts/check_impl_ref.py`` 定期复算并报告
    漂移，不静默容忍。

与 verify_counts.py 的关系
-------------------------
``verify_counts.py`` 的 ``mechanism_unique=53`` 是从治理文档 AST 复算得来, 是本注册表的
外部交叉校验源。两者必须一致: 本注册表 ``count() == 53`` 且 ID 连续无缺口, 即与文档自洽。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 枚举
# ---------------------------------------------------------------------------

#: 生命周期阶段（机制被触发的学习旅程位置）
STAGES: Tuple[str, ...] = ("pre", "during", "post", "ambient")

#: 理论类别（动机科学维度）
CATEGORIES: Tuple[str, ...] = (
    "retention", "motivation", "selfreg", "cognition", "health",
)

#: 治理处置建议
DISPOSITIONS: Tuple[str, ...] = ("K", "M", "R", "D")

#: 成熟度（代码落地程度）
MATURITY: Tuple[str, ...] = ("complete", "partial", "placeholder")

#: ID 形态 ``LF-M01`` .. ``LF-M53``
ID_PATTERN = re.compile(r"^LF-M(\d{2})$")

#: snake_case key 形态
KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

#: impl_ref 形态（宽松，只校验非空与基本形态）。
#:
#: 允许以下写法：
#:   ``file.py``                   仅文件
#:   ``file.py:123``               行号
#:   ``file.py:123,456``           多位置（canonical + 重复实现）
#:   ``file.py:Symbol``            符号级（**推荐**，抗行号漂移）
#:   ``file.py:123,Symbol``        混合
#:   ``ux:345``                    历史简写
#:
#: 冒号后每个逗号分段可以是纯数字行号，也可以是标识符符号名。
IMPL_REF_PATTERN = re.compile(
    r"^[\w./\-]+\.py(?::(?:\d+|[A-Za-z_]\w*)(?:,\s*(?:\d+|[A-Za-z_]\w*))*$)?"  # file.py[:段(,段)*]
    r"|^[\w]+:\d+$"                                                            # 历史简写 ux:345
)


class MechanismDisabledError(RuntimeError):
    """机制被显式关闭（消融实验用）时仍尝试调度的错误"""


# ---------------------------------------------------------------------------
# 干预产物类型 (供仲裁器使用)
# ---------------------------------------------------------------------------


class EffectType(str, Enum):
    """机制执行的产出类型 —— 仲裁器据此分类处理"""

    NUDGE = "nudge"
    REMINDER = "reminder"
    NOTIFICATION = "notification"
    PROMPT = "prompt"
    BADGE = "badge"
    REWARD = "reward"


@dataclass
class Effect:
    """机制执行的产出（候选干预）。

    机制引擎**只产出 Effect 候选, 不直接下发用户可见文案**; 最终是否下发由
    ``mechanism_arbitrator.MechanismArbitrator`` 的三层漏斗决定。这是把
    "FOMO 拉回" 与 "防沉迷推开" 收敛到单一决策入口的关键设计（见治理方案 §3.3）。
    """

    mechanism_id: str
    effect_type: EffectType
    payload: Dict[str, Any]
    priority: int = 50
    cost: float = 1.0
    user_visible: bool = True
    health_critical: bool = False
    # 语义方向 (approach=拉回加时 / withdraw=推开休息 / neutral), 仲裁冲突消解用
    direction: str = "neutral"


@dataclass
class MechanismContext:
    """一次仲裁的上下文（谁、哪个会话、审计轨迹累积）"""

    user_id: str
    session_id: Optional[str] = None
    trace: List[str] = field(default_factory=list)


def registry_fingerprint() -> str:
    """注册表版本指纹 —— 实验可复现性锚点 (§3.4.2)。

    由「机制总数 + 全部 ID 的有序拼接」求短哈希得到。实验创建时写入
    ``Experiment.registry_fingerprint``，复盘时可核验实验所针对的机制集与
    当前注册表是否一致（防止论文复现时机制集漂移）。
    """
    import hashlib
    payload = f"{count()}|" + "|".join(sorted(ids()))
    return hashlib.md5(payload.encode("utf-8")).hexdigest()[:12]


class ABTestToggleProvider:
    """把 ab_test_framework 适配为注册表的机制开关来源 (§3.4.2 改造 3)。

    注意: 本项目的机制注册表是「声明式静态表」，不持有运行时按用户的开关状态；
    按用户/按实验的开关向量由 A/B 框架在运行时计算。本适配器仅作为统一入口，
    供引擎/编排器查询「某用户当前应启用哪些机制」，而无需直接依赖框架实现。
    """

    def __init__(self, framework) -> None:
        # framework: ABTestFramework 实例（鸭子类型，避免循环导入）
        self._fw = framework

    def get_toggles(self, user_id: str) -> Dict[str, bool]:
        return self._fw.get_mechanism_toggles(user_id)

    def is_enabled(self, user_id: str, mechanism_id: str,
                   health_critical: bool = False) -> bool:
        if health_critical:
            return True
        # 合并所有生效实验的开关向量（实验覆盖 > 基线默认开启）
        toggles = self.get_toggles(user_id)
        return toggles.get(mechanism_id, True)

    @property
    def framework(self):
        return self._fw


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MechanismSpec:
    """一个游戏化机制的声明式规格"""

    id: str
    key: str
    name_zh: str
    name_en: str
    stage: str
    category: str
    theory_ref: str
    impl_ref: str
    disposition: str
    maturity: str
    notes: str = ""

    def as_row(self) -> Dict[str, Any]:
        """论文附表 / 治理表用的扁平行"""
        return {
            "id": self.id,
            "key": self.key,
            "name_zh": self.name_zh,
            "name_en": self.name_en,
            "stage": self.stage,
            "category": self.category,
            "theory_ref": self.theory_ref,
            "impl_ref": self.impl_ref,
            "disposition": self.disposition,
            "maturity": self.maturity,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# 校验
# ---------------------------------------------------------------------------

_REQUIRED_FIELDS: Tuple[str, ...] = (
    "id", "key", "name_zh", "name_en", "stage", "category",
    "theory_ref", "impl_ref", "disposition", "maturity",
)


def _validate_spec(spec: MechanismSpec) -> MechanismSpec:
    """构造期校验: 任何一项不合规直接 raise, 不允许脏数据进入注册表"""
    for name in _REQUIRED_FIELDS:
        value = getattr(spec, name, None)
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValueError(f"MechanismSpec 缺少必填字段或字段为空: {name} (key={spec.key!r})")

    if not ID_PATTERN.match(spec.id):
        raise ValueError(f"非法机制 ID: {spec.id!r} (应为 LF-Mxx)")
    if not KEY_PATTERN.match(spec.key):
        raise ValueError(f"非法 mechanism key (须 snake_case): {spec.key!r}")
    if spec.stage not in STAGES:
        raise ValueError(f"非法 stage: {spec.stage!r} (key={spec.key!r}), 可选 {STAGES}")
    if spec.category not in CATEGORIES:
        raise ValueError(f"非法 category: {spec.category!r} (key={spec.key!r}), 可选 {CATEGORIES}")
    if spec.disposition not in DISPOSITIONS:
        raise ValueError(f"非法 disposition: {spec.disposition!r} (key={spec.key!r}), 可选 {DISPOSITIONS}")
    if spec.maturity not in MATURITY:
        raise ValueError(f"非法 maturity: {spec.maturity!r} (key={spec.key!r}), 可选 {MATURITY}")
    if not IMPL_REF_PATTERN.match(spec.impl_ref):
        raise ValueError(f"impl_ref 形态非法: {spec.impl_ref!r} (key={spec.key!r})")
    return spec


def _make_spec(**data: Any) -> MechanismSpec:
    """构造并校验一个 MechanismSpec; 未显式给出 notes 时默认为空串"""
    if "notes" not in data:
        data["notes"] = ""
    return _validate_spec(MechanismSpec(**data))


# ---------------------------------------------------------------------------
# 注册表数据（顺序即 ID 顺序, 顺序一经发布不再变动）
# 来源: docs/LearnFlow_机制治理与落实方案.md §2.4 完整机制清单（经 grep 核验）
# ---------------------------------------------------------------------------

_SPECS_DATA: List[Dict[str, Any]] = [
    # A. 行为主义·强化与奖励（8）
    {"id": "LF-M01", "key": "variable_ratio_reward", "name_zh": "变比率奖励（宝箱）",
     "name_en": "Variable-Ratio Reward", "stage": "during", "category": "retention",
     "theory_ref": "Skinner 1938; Ferster & Skinner 1957",
     "impl_ref": "gamification_service.py:128,139", "disposition": "K", "maturity": "complete"},
    {"id": "LF-M02", "key": "near_miss", "name_zh": "濒赢效应", "name_en": "Near-Miss Effect",
     "stage": "during", "category": "retention", "theory_ref": "Clark et al. 2009; Reid 1986",
     "impl_ref": "gamification_service.py:139", "disposition": "K", "maturity": "complete"},
    {"id": "LF-M03", "key": "dopamine_rhythm", "name_zh": "奖励节拍（多巴胺节律）",
     "name_en": "Dopamine Rhythm", "stage": "during", "category": "retention",
     "theory_ref": "Schultz 1998", "impl_ref": "gamification_service.py:460",
     "disposition": "R", "maturity": "partial", "notes": "接注册表+落库"},
    {"id": "LF-M04", "key": "instant_gratification", "name_zh": "即时满足",
     "name_en": "Instant Gratification", "stage": "during", "category": "motivation",
     "theory_ref": "Ainslie 1975", "impl_ref": "positive_addiction_engine.py:588",
     "disposition": "R", "maturity": "partial"},
    {"id": "LF-M05", "key": "surprise_delight", "name_zh": "惊喜与愉悦",
     "name_en": "Surprise & Delight", "stage": "during", "category": "motivation",
     "theory_ref": "Reiss 2004", "impl_ref": "addiction_engine_v3.py:199",
     "disposition": "R", "maturity": "partial"},
    {"id": "LF-M06", "key": "time_based_bonus", "name_zh": "时间限定加成",
     "name_en": "Time-Based Bonus", "stage": "during", "category": "retention",
     "theory_ref": "强化程序（变动时距）", "impl_ref": "duolingo_addiction_engine.py:539",
     "disposition": "K", "maturity": "complete"},
    {"id": "LF-M07", "key": "collection", "name_zh": "集换收藏",
     "name_en": "Collection / Completion", "stage": "ambient", "category": "retention",
     "theory_ref": "Zeigarnik 变体；完成欲", "impl_ref": "deep_addiction_engine.py:116",
     "disposition": "R", "maturity": "partial"},
    {"id": "LF-M08", "key": "scarcity", "name_zh": "稀缺性", "name_en": "Scarcity",
     "stage": "pre", "category": "motivation", "theory_ref": "Cialdini 1984 (Ch.7)",
     "impl_ref": "deep_addiction_engine.py:461", "disposition": "R",
     "maturity": "partial", "notes": "与 FOMO 联合仲裁"},

    # B. 承诺、损失与目标梯度（8）
    {"id": "LF-M09", "key": "loss_aversion", "name_zh": "损失厌恶", "name_en": "Loss Aversion",
     "stage": "post", "category": "retention", "theory_ref": "Kahneman & Tversky 1979",
     "impl_ref": "addiction_engine_v3.py:7", "disposition": "M", "maturity": "partial",
     "notes": "重复: gamification_service.py:419 应删"},
    {"id": "LF-M10", "key": "sunk_cost_reminder", "name_zh": "沉没成本提示",
     "name_en": "Sunk-Cost Reminder", "stage": "post", "category": "retention",
     "theory_ref": "Arkes & Blumer 1985", "impl_ref": "addiction_engine_v3.py:36",
     "disposition": "R", "maturity": "partial", "notes": "健康审查"},
    {"id": "LF-M11", "key": "streak", "name_zh": "连胜", "name_en": "Streak",
     "stage": "post", "category": "retention", "theory_ref": "连续强化；Lally et al. 2010",
     "impl_ref": "duolingo_addiction_engine.py:316", "disposition": "M", "maturity": "complete",
     "notes": "重复: gamification_service.py:118 应统一到 canonical 并落库"},
    {"id": "LF-M12", "key": "streak_sanctification", "name_zh": "连胜神圣化",
     "name_en": "Streak Sanctification", "stage": "post", "category": "retention",
     "theory_ref": "承诺 × 损失厌恶", "impl_ref": "deep_addiction_engine.py:308",
     "disposition": "R", "maturity": "partial"},
    {"id": "LF-M13", "key": "zeigarnik", "name_zh": "蔡格尼克效应", "name_en": "Zeigarnik Effect",
     "stage": "post", "category": "retention", "theory_ref": "Zeigarnik 1927",
     "impl_ref": "addiction_engine_v3.py:108", "disposition": "M", "maturity": "partial",
     "notes": "重复: gamification_service.py:578 应删"},
    {"id": "LF-M14", "key": "peak_end", "name_zh": "峰终定律", "name_en": "Peak-End Rule",
     "stage": "during", "category": "motivation",
     "theory_ref": "Kahneman 1993; Fredrickson & Kahneman 1993",
     "impl_ref": "addiction_engine_v3.py:163", "disposition": "M", "maturity": "partial",
     "notes": "重复: gamification_service.py:507 应删"},
    {"id": "LF-M15", "key": "goal_gradient", "name_zh": "目标梯度/近距目标",
     "name_en": "Goal Gradient", "stage": "during", "category": "motivation",
     "theory_ref": "Hull 1934; Locke & Latham 1990", "impl_ref": "gamification_service.py:96",
     "disposition": "R", "maturity": "partial"},
    {"id": "LF-M16", "key": "daily_challenge", "name_zh": "每日/月度挑战",
     "name_en": "Daily & Monthly Challenge", "stage": "pre", "category": "retention",
     "theory_ref": "Locke & Latham 1990", "impl_ref": "duolingo_addiction_engine.py:704,582",
     "disposition": "K", "maturity": "complete"},

    # C. 自我决定论：自主·胜任·关联（6）
    {"id": "LF-M17", "key": "autonomy_support", "name_zh": "自主性支持",
     "name_en": "Autonomy Support", "stage": "during", "category": "selfreg",
     "theory_ref": "Deci & Ryan 1985; Ryan & Deci 2000",
     "impl_ref": "habit_addiction_engine.py:159", "disposition": "M", "maturity": "partial",
     "notes": "重复: gamification_service.py:683 应删"},
    {"id": "LF-M18", "key": "ikea_effect", "name_zh": "宜家效应/自主定制",
     "name_en": "IKEA Effect", "stage": "during", "category": "motivation",
     "theory_ref": "Norton, Mochon & Ariely 2012", "impl_ref": "gamification_service.py:623,615",
     "disposition": "R", "maturity": "partial"},
    {"id": "LF-M19", "key": "xp_leveling", "name_zh": "经验值与等级",
     "name_en": "XP & Leveling", "stage": "post", "category": "motivation",
     "theory_ref": "二级强化；SDT 胜任感", "impl_ref": "duolingo_addiction_engine.py:55",
     "disposition": "R", "maturity": "placeholder",
     "notes": "最高优先级: 伪持久化（每次请求从零构造, 已修为落库）"},
    {"id": "LF-M20", "key": "progress_visualization", "name_zh": "进步可视化",
     "name_en": "Progress Visualization", "stage": "during", "category": "motivation",
     "theory_ref": "Locke & Latham 1990; Bandura 1997", "impl_ref": "positive_addiction_engine.py:649",
     "disposition": "R", "maturity": "partial"},
    {"id": "LF-M21", "key": "progressive_disclosure", "name_zh": "渐进式披露",
     "name_en": "Progressive Disclosure", "stage": "during", "category": "cognition",
     "theory_ref": "Sweller 1988; Nielsen 1994", "impl_ref": "ux_addiction_engine.py:119",
     "disposition": "R", "maturity": "partial"},
    {"id": "LF-M22", "key": "pet_companion", "name_zh": "虚拟宠物陪伴",
     "name_en": "Pet Companion (Relatedness)", "stage": "ambient", "category": "motivation",
     "theory_ref": "Ryan & Deci 2000（关联性）", "impl_ref": "pet_service.py",
     "disposition": "K", "maturity": "complete"},

    # D. 社会影响与社会学习（10）
    {"id": "LF-M23", "key": "social_proof", "name_zh": "社会认同", "name_en": "Social Proof",
     "stage": "during", "category": "motivation", "theory_ref": "Cialdini 1984 (Ch.4)",
     "impl_ref": "gamification_service.py:659", "disposition": "M", "maturity": "partial"},
    {"id": "LF-M24", "key": "social_contagion", "name_zh": "社会传染",
     "name_en": "Social Contagion", "stage": "ambient", "category": "retention",
     "theory_ref": "Christakis & Fowler 2007", "impl_ref": "positive_addiction_engine.py:506",
     "disposition": "R", "maturity": "partial"},
    {"id": "LF-M25", "key": "peer_progress", "name_zh": "同伴进度推动",
     "name_en": "Peer Progress Nudge", "stage": "pre", "category": "motivation",
     "theory_ref": "Festinger 1954（上行比较）", "impl_ref": "deep_addiction_engine.py:292",
     "disposition": "R", "maturity": "partial", "notes": "健康审查"},
    {"id": "LF-M26", "key": "friendly_competition", "name_zh": "友好竞争",
     "name_en": "Friendly Competition", "stage": "during", "category": "motivation",
     "theory_ref": "Festinger 1954; Tauer & Harackiewicz 2004",
     "impl_ref": "positive_addiction_engine.py:538", "disposition": "R", "maturity": "partial"},
    {"id": "LF-M27", "key": "leaderboard", "name_zh": "排行榜与联赛",
     "name_en": "Leaderboard & Leagues", "stage": "ambient", "category": "retention",
     "theory_ref": "Garcia & Tor 2009 (N-effect)", "impl_ref": "duolingo_addiction_engine.py:208",
     "disposition": "K", "maturity": "complete", "notes": "需开关: N-effect 有负面证据"},
    {"id": "LF-M28", "key": "business_card", "name_zh": "社交名片",
     "name_en": "Business Card / Identity Display", "stage": "ambient", "category": "retention",
     "theory_ref": "Tajfel & Turner 1979", "impl_ref": "social_addiction_engine.py:55",
     "disposition": "R", "maturity": "placeholder"},
    {"id": "LF-M29", "key": "gift_economy", "name_zh": "礼物经济", "name_en": "Gift Economy",
     "stage": "ambient", "category": "retention", "theory_ref": "Mauss 1925; Cialdini 互惠",
     "impl_ref": "social_addiction_engine.py:411", "disposition": "R", "maturity": "placeholder"},
    {"id": "LF-M30", "key": "friend_quest", "name_zh": "组队任务", "name_en": "Friend Quest",
     "stage": "during", "category": "retention", "theory_ref": "Johnson & Johnson 1989",
     "impl_ref": "duolingo_addiction_engine.py:455", "disposition": "R", "maturity": "partial",
     "notes": "落库"},
    {"id": "LF-M31", "key": "team_competition", "name_zh": "团队竞赛与赛季",
     "name_en": "Team Competition & Season", "stage": "ambient", "category": "retention",
     "theory_ref": "Johnson & Johnson 1989", "impl_ref": "team_competition_engine.py:103,288,389,487,556,651",
     "disposition": "R", "maturity": "partial", "notes": "落库"},
    {"id": "LF-M32", "key": "parent_portal", "name_zh": "家长门户", "name_en": "Parent Portal",
     "stage": "post", "category": "selfreg", "theory_ref": "Hoover-Dempsey & Sandler 1995",
     "impl_ref": "social_addiction_engine.py:288", "disposition": "R",
     "maturity": "placeholder", "notes": "合规价值高"},

    # E. 习惯形成与自我调节（10）
    {"id": "LF-M33", "key": "hook_model", "name_zh": "钩子模型", "name_en": "Hook Model",
     "stage": "pre", "category": "retention", "theory_ref": "Eyal 2014",
     "impl_ref": "positive_addiction_engine.py:67", "disposition": "R",
     "maturity": "partial", "notes": "伦理审查"},
    {"id": "LF-M34", "key": "habit_loop", "name_zh": "习惯回路", "name_en": "Habit Loop",
     "stage": "pre", "category": "selfreg", "theory_ref": "Duhigg 2012; Wood & Rünger 2016",
     "impl_ref": "positive_addiction_engine.py:262", "disposition": "R", "maturity": "partial"},
    {"id": "LF-M35", "key": "cue_prompting", "name_zh": "情境线索提示",
     "name_en": "Cue Prompting", "stage": "pre", "category": "selfreg",
     "theory_ref": "Wood & Neal 2007", "impl_ref": "positive_addiction_engine.py:322",
     "disposition": "R", "maturity": "partial", "notes": "入仲裁器"},
    {"id": "LF-M36", "key": "habit_stacking", "name_zh": "习惯叠加", "name_en": "Habit Stacking",
     "stage": "pre", "category": "selfreg", "theory_ref": "Fogg 2019",
     "impl_ref": "habit_addiction_engine.py:27", "disposition": "K", "maturity": "partial"},
    {"id": "LF-M37", "key": "temptation_bundling", "name_zh": "诱惑捆绑",
     "name_en": "Temptation Bundling", "stage": "pre", "category": "selfreg",
     "theory_ref": "Milkman, Minson & Volpp 2014", "impl_ref": "habit_addiction_engine.py:80",
     "disposition": "K", "maturity": "partial"},
    {"id": "LF-M38", "key": "implementation_intentions", "name_zh": "执行意图",
     "name_en": "Implementation Intentions", "stage": "pre", "category": "selfreg",
     "theory_ref": "Gollwitzer 1999", "impl_ref": "habit_addiction_engine.py:109",
     "disposition": "K", "maturity": "partial"},
    {"id": "LF-M39", "key": "self_regulation_goals", "name_zh": "自我调节目标",
     "name_en": "Self-Regulation Goals", "stage": "pre", "category": "selfreg",
     "theory_ref": "Zimmerman 2002; Bandura 1991", "impl_ref": "habit_addiction_engine.py:213",
     "disposition": "R", "maturity": "partial", "notes": "落库"},
    {"id": "LF-M40", "key": "skill_tree", "name_zh": "元认知技能树",
     "name_en": "Metacognitive Skill Tree", "stage": "ambient", "category": "cognition",
     "theory_ref": "Zimmerman 2002; Flavell 1979", "impl_ref": "meta_learning_skilltree.py:157",
     "disposition": "R", "maturity": "partial", "notes": "最高优先级: 落库"},
    {"id": "LF-M41", "key": "commitment_device", "name_zh": "承诺装置/预约",
     "name_en": "Appointment (Commitment Device)", "stage": "pre", "category": "selfreg",
     "theory_ref": "Rogers, Milkman & Volpp 2014 (JCR)", "impl_ref": "deep_addiction_engine.py:388",
     "disposition": "R", "maturity": "partial", "notes": "入仲裁器"},
    {"id": "LF-M42", "key": "fresh_start", "name_zh": "新起点效应", "name_en": "Fresh Start Effect",
     "stage": "pre", "category": "motivation", "theory_ref": "Dai, Milkman & Riis 2014 (Mgmt Sci)",
     "impl_ref": "addiction_engine_v3.py:51", "disposition": "K", "maturity": "partial"},

    # F. 情绪与动机触发（4）
    {"id": "LF-M43", "key": "curiosity_gap", "name_zh": "好奇心缺口", "name_en": "Curiosity Gap",
     "stage": "pre", "category": "motivation", "theory_ref": "Loewenstein 1994",
     "impl_ref": "deep_addiction_engine.py:25", "disposition": "K", "maturity": "partial",
     "notes": "健康风险最低的正向机制"},
    {"id": "LF-M44", "key": "fomo", "name_zh": "错失恐惧", "name_en": "FOMO",
     "stage": "pre", "category": "retention", "theory_ref": "Przybylski et al. 2013",
     "impl_ref": "deep_addiction_engine.py:238", "disposition": "R",
     "maturity": "partial", "notes": "强制入仲裁器"},
    {"id": "LF-M45", "key": "serendipity", "name_zh": "偶然性与惊喜", "name_en": "Serendipity",
     "stage": "during", "category": "motivation", "theory_ref": "变比率 × 内在动机",
     "impl_ref": "deep_addiction_engine.py:542", "disposition": "R", "maturity": "placeholder"},
    {"id": "LF-M46", "key": "identity_motivation", "name_zh": "身份认同动机",
     "name_en": "Identity-Based Motivation", "stage": "ambient", "category": "motivation",
     "theory_ref": "Oyserman 2007; Markus & Nurius 1986", "impl_ref": "positive_addiction_engine.py:348",
     "disposition": "K", "maturity": "partial"},

    # G. UX 微交互与认知负荷（4）
    {"id": "LF-M47", "key": "micro_interaction", "name_zh": "微交互反馈",
     "name_en": "Micro-interaction", "stage": "during", "category": "motivation",
     "theory_ref": "Norman 2004", "impl_ref": "ux_addiction_engine.py:24",
     "disposition": "R", "maturity": "partial"},
    {"id": "LF-M48", "key": "color_psychology", "name_zh": "色彩与情绪",
     "name_en": "Color Psychology", "stage": "ambient", "category": "cognition",
     "theory_ref": "Elliot & Maier 2014", "impl_ref": "ux_addiction_engine.py:210",
     "disposition": "R", "maturity": "partial"},
    {"id": "LF-M49", "key": "spatial_anchoring", "name_zh": "空间锚定",
     "name_en": "Spatial Anchoring", "stage": "ambient", "category": "cognition",
     "theory_ref": "空间一致性 / 位置记忆", "impl_ref": "ux_addiction_engine.py:290",
     "disposition": "R", "maturity": "placeholder"},
    {"id": "LF-M50", "key": "multisensory_packaging", "name_zh": "多感官包装（占位）",
     "name_en": "Multi-sensory Packaging", "stage": "during", "category": "motivation",
     "theory_ref": "—（无理论支撑）", "impl_ref": "ux_addiction_engine.py:345,482,524",
     "disposition": "D", "maturity": "placeholder", "notes": "建议删除或合并为 1 个可配置主题"},

    # H. 健康护栏与伦理（3）
    {"id": "LF-M51", "key": "forced_rest", "name_zh": "强制休息提醒",
     "name_en": "Forced Rest Reminder", "stage": "during", "category": "health",
     "theory_ref": "认知疲劳恢复", "impl_ref": "feedback_service.py:198",
     "disposition": "K", "maturity": "partial", "notes": "一票否决权"},
    {"id": "LF-M52", "key": "minor_protection", "name_zh": "未成年保护与奖励冷却",
     "name_en": "Minor Protection & Reward Cooldown", "stage": "during", "category": "health",
     "theory_ref": "监管合规 + Griffiths 2005",
     # 符号级引用（非行号）—— 见模块 docstring「impl_ref 行号漂移风险」
     "impl_ref": "anti_addiction_compliance.py:MinorProtectionEngine",
     "disposition": "K", "maturity": "complete", "notes": "一票否决权"},
    {"id": "LF-M53", "key": "lai_downgrade", "name_zh": "LAI 自适应降级",
     "name_en": "LAI Adaptive Downgrade", "stage": "ambient", "category": "health",
     "theory_ref": "自构成瘾指数量表改编", "impl_ref": "learning_addiction_index.py",
     "disposition": "R", "maturity": "placeholder", "notes": "先补采集, 否则废弃"},
]

#: 全部规格 (按 ID 升序)
SPECS: Tuple[MechanismSpec, ...] = tuple(_make_spec(**d) for d in _SPECS_DATA)

_BY_KEY: Dict[str, MechanismSpec] = {spec.key: spec for spec in SPECS}
_BY_ID: Dict[str, MechanismSpec] = {spec.id: spec for spec in SPECS}

# 构造期不变量: ID 必须 LF-M01..LF-M53 连续无缺口、无重复
if len(_BY_KEY) != len(SPECS):
    raise ValueError(f"mechanism key 重复: 共 {len(SPECS)} 条规格, 去重后 {len(_BY_KEY)} 个 key")
if len(_BY_ID) != len(SPECS):
    raise ValueError(f"mechanism id 重复: 共 {len(SPECS)} 条规格, 去重后 {len(_BY_ID)} 个 id")
_EXPECTED_IDS = [f"LF-M{i:02d}" for i in range(1, len(SPECS) + 1)]
if [spec.id for spec in SPECS] != _EXPECTED_IDS:
    raise ValueError(
        f"机制 ID 必须连续无缺口: 期望 {_EXPECTED_IDS}, 实际 {[spec.id for spec in SPECS]}"
    )

#: 显式关闭的机制 key (消融实验用; 默认全部开启)
_DISABLED: set = set()


# ---------------------------------------------------------------------------
# 可枚举 API
# ---------------------------------------------------------------------------


def all_mechanisms() -> List[MechanismSpec]:
    """全部机制规格 (按 ID 升序)"""
    return list(SPECS)


def get(key: str) -> MechanismSpec:
    """按 snake_case key 取规格; 不存在时抛 KeyError (不静默返回 None)"""
    try:
        return _BY_KEY[key]
    except (KeyError, TypeError):
        raise KeyError(f"未注册的游戏化机制: {key!r}；已注册 {len(_BY_KEY)} 个，可用 keys() 枚举")


def get_by_id(mechanism_id: str) -> MechanismSpec:
    """按 LF-Mxx ID 取规格; 不存在时抛 KeyError"""
    try:
        return _BY_ID[mechanism_id]
    except (KeyError, TypeError):
        raise KeyError(f"未注册的机制 ID: {mechanism_id!r}")


def by_stage(stage: str) -> List[MechanismSpec]:
    """按生命周期阶段枚举: pre / during / post / ambient"""
    if stage not in STAGES:
        raise ValueError(f"非法 stage: {stage!r}, 可选 {STAGES}")
    return [spec for spec in SPECS if spec.stage == stage]


def by_category(cat: str) -> List[MechanismSpec]:
    """按理论类别枚举: retention / motivation / selfreg / cognition / health"""
    if cat not in CATEGORIES:
        raise ValueError(f"非法 category: {cat!r}, 可选 {CATEGORIES}")
    return [spec for spec in SPECS if spec.category == cat]


def by_disposition(disp: str) -> List[MechanismSpec]:
    """按治理处置枚举: K 保留 / M 合并 / R 重构 / D 废弃"""
    if disp not in DISPOSITIONS:
        raise ValueError(f"非法 disposition: {disp!r}, 可选 {DISPOSITIONS}")
    return [spec for spec in SPECS if spec.disposition == disp]


def count() -> int:
    """机制总数 (当前 53)"""
    return len(SPECS)


def keys() -> List[str]:
    """全部 snake_case key (按字典序排序)"""
    return sorted(_BY_KEY)


def ids() -> List[str]:
    """全部稳定 ID (LF-M01..LF-M53)"""
    return [spec.id for spec in SPECS]


def catalog_rows() -> List[Dict[str, Any]]:
    """论文附表 / 治理表用的扁平行"""
    return [spec.as_row() for spec in SPECS]


# ---------------------------------------------------------------------------
# 开关 (消融实验)
# ---------------------------------------------------------------------------


def is_enabled(key: str) -> bool:
    """机制是否处于开启状态"""
    get(key)  # 校验存在性
    return key not in _DISABLED


def set_enabled(key: str, enabled: bool) -> None:
    """开启/关闭某个机制。key 不存在时抛 KeyError"""
    get(key)  # 校验存在性
    if enabled:
        _DISABLED.discard(key)
    else:
        _DISABLED.add(key)


def disabled_keys() -> List[str]:
    """当前被关闭的 key (有序)"""
    return sorted(_DISABLED)


def enabled_mechanisms() -> List[MechanismSpec]:
    """当前处于开启状态的机制"""
    return [spec for spec in SPECS if spec.key not in _DISABLED]


__all__ = [
    "STAGES", "CATEGORIES", "DISPOSITIONS", "MATURITY",
    "MechanismSpec", "MechanismDisabledError",
    "EffectType", "Effect", "MechanismContext",
    "registry_fingerprint", "ABTestToggleProvider",
    "SPECS", "all_mechanisms", "get", "get_by_id",
    "by_stage", "by_category", "by_disposition",
    "count", "keys", "ids", "catalog_rows",
    "is_enabled", "set_enabled", "disabled_keys", "enabled_mechanisms",
]
