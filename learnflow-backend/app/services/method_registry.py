"""学习方法注册表 — LearnFlow 学习方法的单一事实源 (single source of truth)

背景
----
LearnFlow 的学习方法此前散落在三个引擎文件里, 没有任何统一枚举入口:

* ``app/services/learning_methods_engine.py``   —— ``METHOD_TIPS`` (15 个方法 / 16 条 tip)
* ``app/services/advanced_methods_engine.py``   —— ``NEW_METHODS`` 通过副作用 append 进
  ``METHOD_TIPS`` (7 个方法)
* ``app/services/learning_methods_engine_v3.py`` —— 若干引擎类, 其输出 dict 的 ``method``
  字段存的是中文显示名而非 snake_case key

结果是: ``get_daily_method_challenge`` 等方法只能在 22 个方法里打转 (思维导图永远调度
不到), 且"每日挑战"对 ``set(...)`` 转换结果取模 —— set 无序导致同一天不同进程可能给出
不同方法, 论文的可复现性要求无法成立。

本模块把全部 **28** 个学习方法收敛为声明式注册表: 可枚举、可调度、可开关, 并为每个
方法分配稳定 ID (``LF-L01``..``LF-L28``) 供论文附表与消融实验引用。

历史背景: 项目旧文档宣称"28 种学习方法", 但最初只有 23 个真实实现
(``LF-L01``..``LF-L23``)。本项目不"把数字改掉", 而是补上了 5 个真实、证据充分、
且与前 23 个无语义重叠的方法 (``LF-L24``..``LF-L28``, 见
``advanced_methods_v2.py``), 让 28 成为可复算的真值。详见
``docs/LearnFlow_学习方法候选核验.md``。

ID 稳定性约定
-------------
``LF-L`` 系列专属于**学习方法**, 与游戏化机制的 ``LF-M`` 系列互斥。ID 一经分配即冻结,
不得复用或重排; 新增方法只能追加新序号。

引用约定 (数字诚信)
-------------------
``evidence_ref`` 为该方法的原始文献锚点:

* tip 的 ``science`` 字段已指名出处的 (如 ``Bjork (1992)``、``Dweck``), 照录并补全年份;
* 代码里只有描述性表述、未指名出处的 (如 pomodoro、思维导图), 给出一个**真实存在**的
  经典文献锚点;
* ``evidence_note`` 原样保留代码内 ``science`` 文案, 以便审计时区分"代码原始声明"与
  "补充的文献锚点"。

``evidence_ref`` 一律不接受编造引用 —— 每一个都必须是可检索到的真实文献。

交付形态约定
------------
``delivery`` 只标记**当前代码里真实存在**的交付通道, 不做能力许诺:

* ``tip``         —— 有 ``METHOD_TIPS`` 文案 (22 个方法)
* ``interactive`` —— 有对应引擎类产出互动流程 (MemoryPalace / DualCoding / Elaboration /
  SelfExplanation / AnalogyBridge / MindMapping / get_reflection_trigger)
* ``plan``        —— 能排练习计划 (SpacedRepetitionService / InterleavingEngine)
* ``quiz``        —— 能出题 (MethodQuizEngine.QUIZZES / PretestingEngine / GenerationEffectEngine)
"""
from __future__ import annotations

import importlib
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

#: 分类枚举
CATEGORIES: Tuple[str, ...] = ("cognitive", "metacognitive", "motivational", "physiological")

#: 交付形态枚举 (内部按此顺序规范化)
DELIVERIES: Tuple[str, ...] = ("tip", "interactive", "plan", "quiz")

#: 难度枚举
DIFFICULTIES: Tuple[str, ...] = ("beginner", "intermediate", "advanced")

#: ID 形态 ``LF-L01`` .. ``LF-L28``
ID_PATTERN = re.compile(r"^LF-L(\d{2})$")

#: snake_case key 形态
KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

#: ``impl_ref`` 形态 ``<module>.py:<symbol.path>[<index>]``
IMPL_REF_PATTERN = re.compile(r"^(?P<module>[\w.]+\.py):(?P<path>.+)$")
_IMPL_TOKEN_PATTERN = re.compile(r"(?P<name>[A-Za-z_]\w*)|\[(?P<index>-?\d+)\]")

#: impl_ref 里允许出现的模块短名 -> 可导入的模块全名
MODULE_ALIASES: Dict[str, str] = {
    "learning_methods_engine.py": "app.services.learning_methods_engine",
    "advanced_methods_engine.py": "app.services.advanced_methods_engine",
    "learning_methods_engine_v3.py": "app.services.learning_methods_engine_v3",
    "advanced_methods_v2.py": "app.services.advanced_methods_v2",
}

#: 唯一一个没有 tip 文案、只能由 v3 引擎交付的方法
MIND_MAPPING_KEY = "mind_mapping"

# B 组的 7 个方法 (pretesting..distributed_practice) 是 advanced_methods_engine 在
# **模块导入时**以副作用 append 进 METHOD_TIPS 的, 因此注册表必须强制导入该模块,
# 否则 METHOD_TIPS[16..22] 根本不存在, impl_ref 也就成了空指针。
# 该模块内有去重保护, 重复导入不会产生重复条目。
from app.services import advanced_methods_engine as _advanced_methods_engine  # noqa: F401


class MethodDisabledError(RuntimeError):
    """方法被显式关闭 (消融实验用) 时仍尝试调度的错误"""


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MethodVariant:
    """同一方法的一个难度变体

    ``memory_palace`` 是唯一拥有两个变体的方法: ``METHOD_TIPS[0]`` (advanced,
    完整宫殿) 与 ``METHOD_TIPS[1]`` (beginner, 从卧室起步)。注册表把它们合并为
    一个方法, 但保留两条可独立定位的实现引用。
    """

    difficulty: str
    impl_ref: str


@dataclass(frozen=True)
class MethodSpec:
    """一个学习方法的声明式规格"""

    id: str
    key: str
    name_zh: str
    category: str
    evidence_ref: str
    impl_ref: str
    delivery: Tuple[str, ...]
    difficulty: str
    variants: Tuple[MethodVariant, ...] = ()
    evidence_note: str = ""
    enabled: bool = True

    @property
    def variant_refs(self) -> Tuple[str, ...]:
        """全部变体的 impl_ref (主变体在前)"""
        return tuple(v.impl_ref for v in self.variants)

    def as_row(self) -> Dict[str, Any]:
        """论文附表用的扁平行"""
        return {
            "id": self.id,
            "key": self.key,
            "name_zh": self.name_zh,
            "category": self.category,
            "evidence_ref": self.evidence_ref,
            "impl_ref": self.impl_ref,
        }


# ---------------------------------------------------------------------------
# 校验
# ---------------------------------------------------------------------------

_REQUIRED_FIELDS: Tuple[str, ...] = (
    "id", "key", "name_zh", "category", "evidence_ref", "impl_ref", "delivery", "difficulty",
)


def _validate_spec(spec: MethodSpec) -> MethodSpec:
    """构造期校验: 任何一项不合规直接 raise, 不允许脏数据进入注册表"""
    for name in _REQUIRED_FIELDS:
        value = getattr(spec, name, None)
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValueError(f"MethodSpec 缺少必填字段或字段为空: {name} (key={spec.key!r})")
        if isinstance(value, tuple) and not value:
            raise ValueError(f"MethodSpec 字段 {name} 不能为空元组 (key={spec.key!r})")

    if not ID_PATTERN.match(spec.id):
        raise ValueError(f"非法方法 ID: {spec.id!r} (应为 LF-Lxx)")
    if not KEY_PATTERN.match(spec.key):
        raise ValueError(f"非法 method key (须 snake_case): {spec.key!r}")
    if spec.category not in CATEGORIES:
        raise ValueError(
            f"非法 category: {spec.category!r} (key={spec.key!r}), 可选 {CATEGORIES}"
        )
    unknown = tuple(d for d in spec.delivery if d not in DELIVERIES)
    if unknown:
        raise ValueError(f"非法 delivery: {unknown} (key={spec.key!r}), 可选 {DELIVERIES}")
    if spec.difficulty not in DIFFICULTIES:
        raise ValueError(
            f"非法 difficulty: {spec.difficulty!r} (key={spec.key!r}), 可选 {DIFFICULTIES}"
        )
    if not IMPL_REF_PATTERN.match(spec.impl_ref):
        raise ValueError(f"非法 impl_ref: {spec.impl_ref!r} (key={spec.key!r})")

    for variant in spec.variants:
        if variant.difficulty not in DIFFICULTIES:
            raise ValueError(
                f"变体难度非法: {variant.difficulty!r} (key={spec.key!r})"
            )
        if not IMPL_REF_PATTERN.match(variant.impl_ref):
            raise ValueError(f"非法变体 impl_ref: {variant.impl_ref!r} (key={spec.key!r})")
    return spec


def _make_spec(**data: Any) -> MethodSpec:
    """构造并校验一个 MethodSpec; 未显式给出 variants 时由主 impl_ref 推导"""
    delivery_raw: Iterable[str] = data.get("delivery") or ()
    data["delivery"] = tuple(d for d in DELIVERIES if d in set(delivery_raw))
    if not data.get("variants"):
        data["variants"] = (
            MethodVariant(difficulty=data["difficulty"], impl_ref=data["impl_ref"]),
        )
    else:
        data["variants"] = tuple(data["variants"])
    return _validate_spec(MethodSpec(**data))


# ---------------------------------------------------------------------------
# 注册表数据 (顺序即 ID 顺序, 顺序一经发布不再变动)
# ---------------------------------------------------------------------------

# A. learning_methods_engine.py 的 METHOD_TIPS[0..15] — 15 个方法
_A_SPECS: List[Dict[str, Any]] = [
    {
        "id": "LF-L01",
        "key": "memory_palace",
        "name_zh": "记忆宫殿",
        "category": "cognitive",
        "evidence_ref": "Yates (1966), The Art of Memory; Maguire et al. (2003)",
        "evidence_note": "2500年前的古希腊人发明, 现代fMRI证明激活了大脑的空间记忆区。",
        "impl_ref": "learning_methods_engine.py:METHOD_TIPS[0]",
        "delivery": ("tip", "interactive", "quiz"),
        "difficulty": "advanced",
        "variants": (
            MethodVariant("advanced", "learning_methods_engine.py:METHOD_TIPS[0]"),
            MethodVariant("beginner", "learning_methods_engine.py:METHOD_TIPS[1]"),
        ),
    },
    {
        "id": "LF-L02",
        "key": "feynman",
        "name_zh": "费曼技巧",
        "category": "cognitive",
        "evidence_ref": "Feynman (1985), Surely You're Joking, Mr. Feynman!",
        "evidence_note": "诺贝尔物理学奖得主费曼的学习方法: 教=最好的学。",
        "impl_ref": "learning_methods_engine.py:METHOD_TIPS[2]",
        "delivery": ("tip", "quiz"),
        "difficulty": "beginner",
    },
    {
        "id": "LF-L03",
        "key": "spaced_repetition",
        "name_zh": "间隔重复",
        "category": "cognitive",
        "evidence_ref": "Ebbinghaus (1885); Cepeda et al. (2006)",
        "evidence_note": "艾宾浩斯遗忘曲线: 24小时后遗忘70%。间隔复习让记忆曲线重新上升。",
        "impl_ref": "learning_methods_engine.py:METHOD_TIPS[3]",
        "delivery": ("tip", "plan", "quiz"),
        "difficulty": "beginner",
    },
    {
        "id": "LF-L04",
        "key": "interleaving",
        "name_zh": "交错练习",
        "category": "cognitive",
        "evidence_ref": "Bjork (1992); Rohrer & Taylor (2007)",
        "evidence_note": "Bjork (1992): 交错练习比集中练习的长期记忆效果高出43%。",
        "impl_ref": "learning_methods_engine.py:METHOD_TIPS[4]",
        "delivery": ("tip", "plan", "quiz"),
        "difficulty": "intermediate",
    },
    {
        "id": "LF-L05",
        "key": "elaborative_rehearsal",
        "name_zh": "精细复述",
        "category": "cognitive",
        "evidence_ref": "Craik & Lockhart (1972)",
        "evidence_note": "Craik & Lockhart: 加工层次越深, 记忆越牢固。",
        "impl_ref": "learning_methods_engine.py:METHOD_TIPS[5]",
        "delivery": ("tip", "interactive"),
        "difficulty": "beginner",
    },
    {
        "id": "LF-L06",
        "key": "chunking",
        "name_zh": "组块化",
        "category": "cognitive",
        "evidence_ref": "Miller (1956); Cowan (2001)",
        "evidence_note": "工作记忆只能同时处理4±1个组块。组块化让你处理更多信息。",
        "impl_ref": "learning_methods_engine.py:METHOD_TIPS[6]",
        "delivery": ("tip",),
        "difficulty": "beginner",
    },
    {
        "id": "LF-L07",
        "key": "dual_coding",
        "name_zh": "双重编码",
        "category": "cognitive",
        "evidence_ref": "Paivio (1971)",
        "evidence_note": "Paivio的双重编码理论: 两个通道同时编码, 回忆概率翻倍。",
        "impl_ref": "learning_methods_engine.py:METHOD_TIPS[7]",
        "delivery": ("tip", "interactive"),
        "difficulty": "beginner",
    },
    {
        "id": "LF-L08",
        "key": "active_recall",
        "name_zh": "主动回忆",
        "category": "cognitive",
        "evidence_ref": "Karpicke & Roediger (2008)",
        "evidence_note": "Karpicke & Roediger: 主动回忆是最有效的学习方法之一。",
        "impl_ref": "learning_methods_engine.py:METHOD_TIPS[8]",
        "delivery": ("tip", "quiz"),
        "difficulty": "beginner",
    },
    {
        "id": "LF-L09",
        "key": "retrieval_practice",
        "name_zh": "检索练习",
        "category": "cognitive",
        "evidence_ref": "Roediger & Karpicke (2006)",
        "evidence_note": "测试效应(Testing Effect): 做一次测试的记忆效果相当于重新学习4次。",
        "impl_ref": "learning_methods_engine.py:METHOD_TIPS[9]",
        "delivery": ("tip",),
        "difficulty": "beginner",
    },
    {
        "id": "LF-L10",
        "key": "metacognition",
        "name_zh": "元认知反思",
        "category": "metacognitive",
        "evidence_ref": "Flavell (1979)",
        "evidence_note": "Flavell: 元认知能力是学生成绩的最佳预测指标之一。",
        "impl_ref": "learning_methods_engine.py:METHOD_TIPS[10]",
        "delivery": ("tip", "interactive"),
        "difficulty": "intermediate",
    },
    {
        "id": "LF-L11",
        "key": "pomodoro",
        "name_zh": "番茄学习法",
        "category": "physiological",
        "evidence_ref": "Cirillo (2018), The Pomodoro Technique",
        "evidence_note": "注意力在25分钟后开始显著下降。短休息能让后续的注意力恢复。",
        "impl_ref": "learning_methods_engine.py:METHOD_TIPS[11]",
        "delivery": ("tip",),
        "difficulty": "beginner",
    },
    {
        "id": "LF-L12",
        "key": "sq3r",
        "name_zh": "SQ3R阅读法",
        "category": "cognitive",
        "evidence_ref": "Robinson (1946)",
        "evidence_note": "Robinson (1946): 结构化阅读比被动阅读的效率高4倍。",
        "impl_ref": "learning_methods_engine.py:METHOD_TIPS[12]",
        "delivery": ("tip",),
        "difficulty": "intermediate",
    },
    {
        "id": "LF-L13",
        "key": "growth_mindset",
        "name_zh": "生长型思维",
        "category": "motivational",
        "evidence_ref": "Dweck (2006), Mindset",
        "evidence_note": "Dweck: 相信智力可成长的学生比相信智力固定的学生成绩高30%。",
        "impl_ref": "learning_methods_engine.py:METHOD_TIPS[13]",
        "delivery": ("tip",),
        "difficulty": "beginner",
    },
    {
        "id": "LF-L14",
        "key": "sleep_memory",
        "name_zh": "睡眠巩固记忆",
        "category": "physiological",
        "evidence_ref": "Walker (2017); Rasch & Born (2013)",
        "evidence_note": "Walker (2017): 睡眠中, 海马体将短期记忆'重放'到皮层, 实现长期巩固。",
        "impl_ref": "learning_methods_engine.py:METHOD_TIPS[14]",
        "delivery": ("tip",),
        "difficulty": "beginner",
    },
    {
        "id": "LF-L15",
        "key": "exercise_memory",
        "name_zh": "运动增强记忆",
        "category": "physiological",
        "evidence_ref": "Cotman & Berchtold (2002)",
        "evidence_note": "运动后BDNF水平上升, 促进海马体神经生成。运动=大脑肥料。",
        "impl_ref": "learning_methods_engine.py:METHOD_TIPS[15]",
        "delivery": ("tip",),
        "difficulty": "beginner",
    },
]

# B. advanced_methods_engine.py 的 NEW_METHODS — append 后落在 METHOD_TIPS[16..22]
_B_SPECS: List[Dict[str, Any]] = [
    {
        "id": "LF-L16",
        "key": "pretesting",
        "name_zh": "预习效应",
        "category": "cognitive",
        "evidence_ref": "Kornell, Hays & Bjork (2009)",
        "evidence_note": "Kornell (2009): 先行测试组的最终成绩高出对照组50%。",
        "impl_ref": "learning_methods_engine.py:METHOD_TIPS[16]",
        "delivery": ("tip", "quiz"),
        "difficulty": "beginner",
    },
    {
        "id": "LF-L17",
        "key": "generation",
        "name_zh": "生成效应",
        "category": "cognitive",
        "evidence_ref": "Slamecka & Graf (1978)",
        "evidence_note": "Slamecka & Graf (1978): 自己生成的词汇比直接阅读的记忆率高300%。",
        "impl_ref": "learning_methods_engine.py:METHOD_TIPS[17]",
        "delivery": ("tip", "quiz"),
        "difficulty": "beginner",
    },
    {
        "id": "LF-L18",
        "key": "self_explanation",
        "name_zh": "自我解释",
        "category": "metacognitive",
        "evidence_ref": "Chi, Bassok, Lewis, Reimann & Glaser (1989)",
        "evidence_note": "Chi (1989): 自我解释组的理解深度是对照组的2倍。",
        "impl_ref": "learning_methods_engine.py:METHOD_TIPS[18]",
        "delivery": ("tip", "interactive"),
        "difficulty": "intermediate",
    },
    {
        "id": "LF-L19",
        "key": "analogy",
        "name_zh": "类比学习",
        "category": "cognitive",
        "evidence_ref": "Gentner (1983)",
        "evidence_note": "Gentner (1983): 类比推理是人类认知的核心机制。",
        "impl_ref": "learning_methods_engine.py:METHOD_TIPS[19]",
        "delivery": ("tip", "interactive"),
        "difficulty": "intermediate",
    },
    {
        "id": "LF-L20",
        "key": "concrete_examples",
        "name_zh": "具体例子",
        "category": "cognitive",
        "evidence_ref": "Pashler et al. (2007)",
        "evidence_note": "概念的具体化使学习速度提升40% (Pashler, 2007)。",
        "impl_ref": "learning_methods_engine.py:METHOD_TIPS[20]",
        "delivery": ("tip",),
        "difficulty": "beginner",
    },
    {
        "id": "LF-L21",
        "key": "successive_relearning",
        "name_zh": "连续重学",
        "category": "cognitive",
        "evidence_ref": "Bahrick (1979)",
        "evidence_note": "Bahrick (1979): 连续重学使长期记忆保持率提升到90%+。",
        "impl_ref": "learning_methods_engine.py:METHOD_TIPS[21]",
        "delivery": ("tip", "plan"),
        "difficulty": "intermediate",
    },
    {
        "id": "LF-L22",
        "key": "distributed_practice",
        "name_zh": "分布式练习",
        "category": "cognitive",
        "evidence_ref": "Cepeda et al. (2006)",
        "evidence_note": "分布练习效应是最稳健的学习发现之一 (Cepeda 2006)。",
        "impl_ref": "learning_methods_engine.py:METHOD_TIPS[22]",
        "delivery": ("tip", "plan"),
        "difficulty": "beginner",
    },
]

# C. learning_methods_engine_v3.py 里唯一的新方法 (其余 v3 引擎是 A/B 的等价复刻)
_C_SPECS: List[Dict[str, Any]] = [
    {
        "id": "LF-L23",
        "key": MIND_MAPPING_KEY,
        "name_zh": "思维导图",
        "category": "cognitive",
        "evidence_ref": "Buzan (1974); Nesbit & Adesope (2006)",
        "evidence_note": "v3 引擎原文: 将知识点可视化为连接图, 帮助理解知识结构。",
        "impl_ref": "learning_methods_engine_v3.py:MindMappingEngine.generate_knowledge_map",
        "delivery": ("interactive",),
        "difficulty": "beginner",
        "variants": (
            MethodVariant(
                "beginner",
                "learning_methods_engine_v3.py:MindMappingEngine.generate_knowledge_map",
            ),
        ),
    },
]

# D. advanced_methods_v2.py — 把"28 种学习方法"从宣称变为真值的 5 个新增方法。
#    每个都有真实引擎实现 (不是文案), 且与 A/B/C 的 23 个无语义重叠。
_D_SPECS: List[Dict[str, Any]] = [
    {
        "id": "LF-L24",
        "key": "worked_examples",
        "name_zh": "例题-解题对",
        "category": "cognitive",
        "evidence_ref": "Sweller (1988); Renkl (2005, Educational Psychology Review)",
        "evidence_note": "先示范完整解再逐步渐隐(fading), 比直接刷题的长时保持更优。",
        "impl_ref": "advanced_methods_v2.py:WorkedExamplesEngine.build_faded_sequence",
        "delivery": ("interactive", "plan"),
        "difficulty": "beginner",
    },
    {
        "id": "LF-L25",
        "key": "keyword_mnemonic",
        "name_zh": "关键词记忆法",
        "category": "cognitive",
        "evidence_ref": "Atkinson & Raugh (1975)",
        "evidence_note": "用母语中发音相近的词做声音桥 + 夸张意象, 专攻外语/生词。",
        "impl_ref": "advanced_methods_v2.py:KeywordMnemonicEngine.build_mnemonic",
        "delivery": ("interactive",),
        "difficulty": "beginner",
    },
    {
        "id": "LF-L26",
        "key": "productive_failure",
        "name_zh": "有效失败",
        "category": "metacognitive",
        "evidence_ref": "Kapur (2008, Cognition and Instruction, 26(3):379-424); "
                       "Sinha & Kapur (2021)",
        "evidence_note": "先尝试解决/生成方案再接受教学, 且必须有结构化归纳; "
                         "无归纳的纯失败是'无效失败', 无同等收益。",
        "impl_ref": "advanced_methods_v2.py:ProductiveFailureEngine.build_session",
        "delivery": ("interactive",),
        "difficulty": "intermediate",
    },
    {
        "id": "LF-L27",
        "key": "summarization",
        "name_zh": "摘要法",
        "category": "cognitive",
        "evidence_ref": "Wittwer & Renkl (2010, Educational Psychology Review)",
        "evidence_note": "对一段文本抽取主干、压缩成 1-3 句, 训练选择性与压缩能力。",
        "impl_ref": "advanced_methods_v2.py:SummarizationEngine.build_prompt",
        "delivery": ("interactive",),
        "difficulty": "intermediate",
    },
    {
        "id": "LF-L28",
        "key": "varied_practice",
        "name_zh": "变异练习",
        "category": "cognitive",
        "evidence_ref": "Schmidt & Bjork (1992, Psychological Science, 3(2):77-82)",
        "evidence_note": "保持同一任务类型, 改变表面特征/情境, 防止套模板。",
        "impl_ref": "advanced_methods_v2.py:VariedPracticeEngine.generate_variants",
        "delivery": ("plan",),
        "difficulty": "beginner",
    },
]

#: 全部规格 (按 ID 升序)
SPECS: Tuple[MethodSpec, ...] = tuple(
    _make_spec(**data) for data in (*_A_SPECS, *_B_SPECS, *_C_SPECS, *_D_SPECS)
)

_BY_KEY: Dict[str, MethodSpec] = {spec.key: spec for spec in SPECS}
_BY_ID: Dict[str, MethodSpec] = {spec.id: spec for spec in SPECS}

# 构造期不变量: ID 必须 LF-L01..LF-LNN 连续无缺口、无重复
if len(_BY_KEY) != len(SPECS):
    raise ValueError(f"method key 重复: 共 {len(SPECS)} 条规格, 去重后 {len(_BY_KEY)} 个 key")
if len(_BY_ID) != len(SPECS):
    raise ValueError(f"method id 重复: 共 {len(SPECS)} 条规格, 去重后 {len(_BY_ID)} 个 id")
_EXPECTED_IDS = [f"LF-L{i:02d}" for i in range(1, len(SPECS) + 1)]
if [spec.id for spec in SPECS] != _EXPECTED_IDS:
    raise ValueError(
        f"方法 ID 必须连续无缺口: 期望 {_EXPECTED_IDS}, 实际 {[spec.id for spec in SPECS]}"
    )

#: 显式关闭的方法 key (消融实验用; 默认全部开启)
_DISABLED: set = set()


# ---------------------------------------------------------------------------
# impl_ref 解析
# ---------------------------------------------------------------------------


def resolve_impl_ref(impl_ref: str) -> Any:
    """把 ``module.py:Symbol.path[0]`` 解析为真实对象

    用 ``importlib`` 动态导入, 逐级 ``getattr`` / 下标取值。解析不到 (模块不存在、
    符号不存在、下标越界) 一律 raise, 不做静默降级 —— 注册表里的每一条实现引用
    都必须是可 grep、可导入的真实代码位置。
    """
    match = IMPL_REF_PATTERN.match(impl_ref or "")
    if not match:
        raise ValueError(f"非法 impl_ref: {impl_ref!r}")

    module_name = match.group("module")
    path = match.group("path")
    full_module = MODULE_ALIASES.get(module_name)
    if full_module is None:
        raise ValueError(f"impl_ref 模块未在 MODULE_ALIASES 中登记: {module_name!r}")

    module = importlib.import_module(full_module)

    obj: Any = None
    try:
        for token in _IMPL_TOKEN_PATTERN.finditer(path):
            name, index = token.group("name"), token.group("index")
            if obj is None:
                if name is None:
                    raise ValueError(f"impl_ref 必须以符号名开头: {impl_ref!r}")
                obj = getattr(module, name)
                continue
            if name is not None:
                obj = getattr(obj, name)
            else:
                obj = obj[int(index)]
    except (AttributeError, IndexError, KeyError) as exc:
        # 符号不存在 / 下标越界 / dict 缺键 —— 统一为解析失败, 不让底层异常泄漏
        raise ValueError(f"impl_ref 解析失败: {impl_ref!r} ({exc.__class__.__name__}: {exc})")
    if obj is None:
        raise ValueError(f"impl_ref 未解析出任何符号: {impl_ref!r}")
    return obj


def spec_tip(spec: MethodSpec) -> Any:
    """取回某方法主变体指向的实现对象 (tip dict 或引擎方法)"""
    return resolve_impl_ref(spec.impl_ref)


# ---------------------------------------------------------------------------
# 可枚举 API
# ---------------------------------------------------------------------------


def all_methods() -> List[MethodSpec]:
    """全部方法规格 (按 ID 升序)"""
    return list(SPECS)


def get(key: str) -> MethodSpec:
    """按 snake_case key 取规格; 不存在时抛 KeyError (不静默返回 None)"""
    try:
        return _BY_KEY[key]
    except (KeyError, TypeError):
        raise KeyError(f"未注册的学习方法: {key!r}；已注册 {len(_BY_KEY)} 个，可用 keys() 枚举")


def get_by_id(method_id: str) -> MethodSpec:
    """按 LF-Lxx ID 取规格; 不存在时抛 KeyError"""
    try:
        return _BY_ID[method_id]
    except (KeyError, TypeError):
        raise KeyError(f"未注册的方法 ID: {method_id!r}")


def by_category(cat: str) -> List[MethodSpec]:
    """按分类枚举: cognitive / metacognitive / motivational / physiological"""
    if cat not in CATEGORIES:
        raise ValueError(f"非法 category: {cat!r}, 可选 {CATEGORIES}")
    return [spec for spec in SPECS if spec.category == cat]


def by_delivery(delivery: str) -> List[MethodSpec]:
    """按交付形态枚举: tip / interactive / plan / quiz"""
    if delivery not in DELIVERIES:
        raise ValueError(f"非法 delivery: {delivery!r}, 可选 {DELIVERIES}")
    return [spec for spec in SPECS if delivery in spec.delivery]


def count() -> int:
    """方法总数 (当前 28)"""
    return len(SPECS)


def keys() -> List[str]:
    """全部 snake_case key, **按字典序排序**

    排序是有意为之: 每日挑战对 ``keys()`` 取模, 只有顺序确定才能保证同一天
    在任何进程里都给出同一个方法 (可复现性)。
    """
    return sorted(_BY_KEY)


def ids() -> List[str]:
    """全部稳定 ID (LF-L01..LF-L28)"""
    return [spec.id for spec in SPECS]


def catalog_rows() -> List[Dict[str, Any]]:
    """论文附表用的扁平行: id / key / name_zh / category / evidence_ref / impl_ref"""
    return [spec.as_row() for spec in SPECS]


# ---------------------------------------------------------------------------
# 开关 (消融实验)
# ---------------------------------------------------------------------------


def is_enabled(key: str) -> bool:
    """方法是否处于开启状态"""
    return key not in _DISABLED


def set_enabled(key: str, enabled: bool) -> None:
    """开启/关闭某个方法。key 不存在时抛 KeyError"""
    get(key)  # 校验存在性
    if enabled:
        _DISABLED.discard(key)
    else:
        _DISABLED.add(key)


def disabled_keys() -> List[str]:
    """当前被关闭的 key (有序)"""
    return sorted(_DISABLED)


def enabled_methods() -> List[MethodSpec]:
    """当前处于开启状态的方法"""
    return [spec for spec in SPECS if spec.key not in _DISABLED]


# ---------------------------------------------------------------------------
# 调度层
# ---------------------------------------------------------------------------


def render(method_key: str, topic: str = "", **ctx: Any) -> Dict[str, Any]:
    """统一调度入口: 一次调用渲染任意一种学习方法

    路由规则:
    * ``mind_mapping`` (LF-L23) —— 走 ``MindMappingEngine.generate_knowledge_map``,
      ``ctx["sub_topics"]`` 提供分支子节点
    * 其余 22 个 —— 走 ``LearningMethodEngine.render_tip``, 复用既有 tip 渲染
      路径, 因此必然经过 ``ground_topic`` 做知识点代入

    Args:
        method_key: 学习方法 snake_case key
        topic: 当前知识点
        **ctx: 可选 ``difficulty`` (选变体) / ``sub_topics`` (思维导图) / ``scene``

    Returns:
        统一带 ``method_id`` / ``method_key`` / ``topic`` 三个埋点字段的 dict

    Raises:
        KeyError: 方法未注册
        MethodDisabledError: 方法被消融实验关闭
    """
    spec = get(method_key)
    if spec.key in _DISABLED:
        raise MethodDisabledError(f"学习方法已被关闭: {spec.key} ({spec.id})")

    scene = ctx.get("scene", "generic")

    if spec.key == MIND_MAPPING_KEY:
        # 延迟导入: 避免与 learning_methods_engine 形成模块级循环依赖
        from app.services.learning_methods_engine_v3 import MindMappingEngine

        sub_topics = list(ctx.get("sub_topics") or [])
        payload = MindMappingEngine.generate_knowledge_map(topic, sub_topics)
        return {
            **payload,
            "method_id": spec.id,
            "method_key": spec.key,
            "name_zh": spec.name_zh,
            "topic": topic,
            "scene": scene,
        }

    # D 组 5 个方法: 真实引擎实现, 由 advanced_methods_v2 路由
    if spec.key in ("worked_examples", "keyword_mnemonic",
                    "productive_failure", "summarization", "varied_practice"):
        from app.services import advanced_methods_v2 as v2

        engine_call = {
            "worked_examples": lambda: v2.WorkedExamplesEngine.build_faded_sequence(
                ctx.get("problem", f"关于「{topic}」的例题"),
                ctx.get("full_solution", [f"第1步: 分析「{topic}」", f"第2步: 求解", f"第3步: 验证"]),
            ),
            "keyword_mnemonic": lambda: v2.KeywordMnemonicEngine.build_mnemonic(
                ctx.get("target", topic),
                ctx.get("target_lang", "英语"),
                ctx.get("native_keyword", f"与「{topic}」谐音的词"),
                ctx.get("imagery", "一幅夸张的连接画面"),
            ),
            "productive_failure": lambda: v2.ProductiveFailureEngine.build_session(
                ctx.get("problem", f"一个关于「{topic}」、你还没学过的难题"),
                topic,
            ),
            "summarization": lambda: v2.SummarizationEngine.build_prompt(
                ctx.get("passage", f"一段关于「{topic}」的讲解文字"),
            ),
            "varied_practice": lambda: v2.VariedPracticeEngine.generate_variants(
                topic,
                ctx.get("base_template", "情境: {context}，请解决「{topic}」相关问题。"),
                ctx.get("contexts", ["学校", "家里", "超市"]),
            ),
        }[spec.key]
        payload = engine_call()
        return {
            **payload,
            "method_id": spec.id,
            "method_key": spec.key,
            "name_zh": spec.name_zh,
            "topic": topic,
            "scene": scene,
        }

    # 其余 22 个: 走 LearningMethodEngine.render_tip, 必然经过 ground_topic
    from app.services.learning_methods_engine import LearningMethodEngine

    difficulty = ctx.get("difficulty") or spec.difficulty
    payload = LearningMethodEngine.render_tip(
        spec.key, topic, difficulty=difficulty, scene=scene
    )
    return {
        **payload,
        "method_id": spec.id,
        "method_key": spec.key,
        "name_zh": spec.name_zh,
        "topic": topic,
    }


__all__ = [
    "CATEGORIES",
    "DELIVERIES",
    "DIFFICULTIES",
    "MethodSpec",
    "MethodVariant",
    "MethodDisabledError",
    "SPECS",
    "MIND_MAPPING_KEY",
    "all_methods",
    "get",
    "get_by_id",
    "by_category",
    "by_delivery",
    "count",
    "keys",
    "ids",
    "catalog_rows",
    "is_enabled",
    "set_enabled",
    "disabled_keys",
    "enabled_methods",
    "render",
    "resolve_impl_ref",
    "spec_tip",
]
