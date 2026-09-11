"""自陈测量量表目录 — LearnFlow 成瘾化研究的自陈测量基础设施

背景与动机
----------
LAI（学习成瘾化指数）的五维框架中，**「行为控制」与「功能影响」两维（合计 35% 权重）**
无法从 ``Attempt`` 行为日志中观测。此前这两维由硬编码常量驱动
（``planned_stop_failures=0`` / ``sleep_impact=0`` / ``social_impact=0``），
导致索引结构性偏向「不成瘾」——无论真实行为如何，这两维恒为满分。

本模块提供自陈（self-report）侧的采集定义，与行为日志构成**双源测量**：

===========  ==========================================  ==================
测量源        可观测内容                                   覆盖的 LAI 维度
===========  ==========================================  ==================
行为日志      ``Attempt``：时长 / 夜间比例 / 提示依赖       time(30%)、motivation(25%)
自陈量表      本目录四份量表                                control(25%)、function(10%)、
                                                          cognition 的时间偏差子项(10%)
===========  ==========================================  ==================

设计原则：**不允许未被测量的维度静默地按「健康」计分。**
调用方必须显式声明哪些维度已测（见 ``LearningAddictionIndex.assess`` 的
``measured_dimensions`` 参数）；未测维度从加权中剔除并计入 ``coverage``，
而不是给一个伪造的满分。

题项来源与诚实声明（重要）
--------------------------
本目录题项为**本项目自行编写**（purpose-built），**并非**照搬受版权保护的既有量表
（如 Bergen 社交媒体成瘾量表 BSMAS、DSM-5 网络游戏障碍 IGD-9）。取舍与后果：

1. **好处**：避免版权与授权问题，且题项可直接对齐本系统的模型输入（外部量表通常不能）。
2. **代价**：自编题项**尚未经过独立信效度检验**。

因此 —— 任何使用本量表结果的研究材料**必须**在局限性中声明这一点，且**不得**宣称
这些题项「已验证」「已标定」。把「自编量表的信效度验证」作为后续工作是合法的、
且本身具有方法学贡献的可发表方向。

计分规则
--------
- ``likert`` 题项：原始 1..5；``reverse=True`` 的题项按 ``6 - value`` 反转；
  量表分 = 反转后均值线性归一化到 ``[0, 1]``（越高 = 该问题越严重）。
- ``count`` 题项：值域 0..7（过去 7 天发生的次数），量表分 = 各题之和。

维度映射约定
------------
``InstrumentSpec.dimension`` 直接给出该量表结果应写入哪个 LAI 输入键，
使聚合逻辑无需硬编码映射表；新增量表只改本目录即可。
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ──────────────────────────────────────────────────────────────────────
# 规格定义
# ──────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class InstrumentItemSpec:
    """单个题项。"""

    order: int
    text_zh: str
    reverse: bool = False
    #: likert 题用 1..5；count 题用 0..7（过去 7 天次数）
    max_value: int = 5


@dataclass(frozen=True)
class InstrumentSpec:
    """一份自陈量表。"""

    code: str
    name_zh: str
    dimension: str
    item_type: str            # "likert" | "count"
    items: Tuple[InstrumentItemSpec, ...]
    #: 该量表结果喂给 LAI 的哪个输入键
    lai_input: str
    #: 计分后向 LAI 输入的换算说明（人类可读，供审计）
    mapping_note: str
    #: 适用年龄段：any / secondary / senior
    age_band: str = "any"
    #: 施测频率建议
    cadence: str = "weekly"
    #: 理论/文献依据说明（非受版权保护量表的替代说明）
    provenance: str = "本项目自编（purpose-built），未经独立信效度验证"

    @property
    def item_count(self) -> int:
        return len(self.items)

    @property
    def max_total(self) -> int:
        return sum(i.max_value for i in self.items)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "name_zh": self.name_zh,
            "dimension": self.dimension,
            "item_type": self.item_type,
            "item_count": self.item_count,
            "age_band": self.age_band,
            "cadence": self.cadence,
            "provenance": self.provenance,
            "lai_input": self.lai_input,
            "mapping_note": self.mapping_note,
            "items": [
                {
                    "order": i.order,
                    "text_zh": i.text_zh,
                    "reverse": i.reverse,
                    "max_value": i.max_value,
                }
                for i in self.items
            ],
        }


# ──────────────────────────────────────────────────────────────────────
# 四份量表定义
# ──────────────────────────────────────────────────────────────────────

#: 行为控制：计划停止失败（喂 LAI.planned_stop_failures）
_SRL_STOP = InstrumentSpec(
    code="SRL-STOP",
    name_zh="学习停止控制量表（过去 7 天）",
    dimension="control",
    item_type="count",
    items=(
        InstrumentItemSpec(1, "过去 7 天，有多少次你「计划学到某个时间就停」，但实际超出了计划？", max_value=7),
        InstrumentItemSpec(2, "过去 7 天，有多少次因为学习而推迟了本该做的事（吃饭、睡觉、运动、家务）？", max_value=7),
        InstrumentItemSpec(3, "过去 7 天，有多少次到了该停的时候，你感到「就是停不下来」？", max_value=7),
    ),
    lai_input="planned_stop_failures",
    mapping_note="三题求和即为「本周计划停止失败次数」，直接作为该 LAI 输入；"
                 "无需换算，语义与 LAI 阈值 planned_stop_failure_limit（次/周）一致。",
    cadence="weekly",
)

#: 功能影响 — 睡眠（喂 LAI.sleep_impact，归一化 0-1）
_SLEEP_IMPACT = InstrumentSpec(
    code="SLEEP-IMPACT",
    name_zh="学习对睡眠影响量表（过去 7 天）",
    dimension="function",
    item_type="likert",
    items=(
        InstrumentItemSpec(1, "因为学习，我的入睡时间被推迟了。"),
        InstrumentItemSpec(2, "因为学习，我的睡眠总时长不够。"),
        InstrumentItemSpec(3, "白天我会因为睡眠不足而困倦、注意力难集中。"),
        InstrumentItemSpec(4, "我曾在睡前想着没学完的内容而难以放松。"),
    ),
    lai_input="sleep_impact",
    mapping_note="四题均值（1..5）线性归一化到 [0,1]，即 (mean-1)/4；"
                 "0=无影响，1=影响最重。",
    cadence="weekly",
)

#: 功能影响 — 社交（喂 LAI.social_impact，归一化 0-1）
_SOCIAL_IMPACT = InstrumentSpec(
    code="SOCIAL-IMPACT",
    name_zh="学习对社交影响量表（过去 7 天）",
    dimension="function",
    item_type="likert",
    items=(
        InstrumentItemSpec(1, "因为学习，我减少了和家人相处的时间。"),
        InstrumentItemSpec(2, "因为学习，我减少了和同学朋友线下见面的次数。"),
        InstrumentItemSpec(3, "因为学习，我推掉过原本想参加的社交活动。"),
        InstrumentItemSpec(4, "比起和人面对面相处，我更愿意独自继续学习。"),
    ),
    lai_input="social_impact",
    mapping_note="四题均值线性归一化到 [0,1]，即 (mean-1)/4；0=无影响，1=影响最重。",
    cadence="weekly",
)

#: 认知 — 时间感知偏差（喂 LAI.time_perception_bias，归一化 0-1）
_TIME_BIAS = InstrumentSpec(
    code="TIME-BIAS",
    name_zh="时间感知偏差量表",
    dimension="cognition",
    item_type="likert",
    items=(
        InstrumentItemSpec(1, "我常低估自己实际花了多少时间在学习上。"),
        InstrumentItemSpec(2, "学习时，我觉得时间过得比预期的快得多。"),
        InstrumentItemSpec(3, "常在被提醒或被打断时，才发现已经过去很久。"),
    ),
    lai_input="time_perception_bias",
    mapping_note="三题均值线性归一化到 [0,1]，即 (mean-1)/4；0=无偏差，1=偏差最大。",
    cadence="monthly",
)

#: 目录（新增量表在此追加；code 一经发布即冻结，不得复用）
INSTRUMENTS: Tuple[InstrumentSpec, ...] = (
    _SRL_STOP,
    _SLEEP_IMPACT,
    _SOCIAL_IMPACT,
    _TIME_BIAS,
)

_BY_CODE: Dict[str, InstrumentSpec] = {s.code: s for s in INSTRUMENTS}


# ──────────────────────────────────────────────────────────────────────
# 查询与计分
# ──────────────────────────────────────────────────────────────────────

def all_instruments() -> List[InstrumentSpec]:
    """返回全部量表定义。"""
    return list(INSTRUMENTS)


def get_instrument(code: str) -> Optional[InstrumentSpec]:
    """按 code 取量表；不存在返回 None。"""
    return _BY_CODE.get(code)


def instruments_for_dimension(dimension: str) -> List[InstrumentSpec]:
    """按 LAI 维度（control / function / cognition / time / motivation）取量表。"""
    return [s for s in INSTRUMENTS if s.dimension == dimension]


def scoring_method(code: str) -> str:
    """返回某量表应使用的计分方法名（供 API 层与审计使用）。"""
    spec = get_instrument(code)
    if spec is None:
        raise KeyError(f"未知量表 code: {code}")
    return "sum_count" if spec.item_type == "count" else "mean_normalized"


def score(code: str, answers: List[int]) -> Dict[str, object]:
    """对一份作答计分。

    Args:
        code: 量表 code。
        answers: 与题项**同序**的作答值列表。likert 题值域 1..5；count 题值域 0..7。

    Returns:
        ``{"raw_total": int, "normalized": float, "lai_input": str, "lai_value": float}``

    Raises:
        KeyError: 未知量表。
        ValueError: 作答数量不匹配，或取值越界。
    """
    spec = get_instrument(code)
    if spec is None:
        raise KeyError(f"未知量表 code: {code}")
    if len(answers) != spec.item_count:
        raise ValueError(
            f"量表 {code} 需要 {spec.item_count} 项作答，实际收到 {len(answers)} 项"
        )

    processed: List[int] = []
    for item, value in zip(spec.items, answers):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"量表 {code} 第 {item.order} 题作答必须为整数，实际为 {value!r}")
        if item_type_out_of_range(value, item.max_value):
            raise ValueError(
                f"量表 {code} 第 {item.order} 题作答 {value} 超出「0..{item.max_value}」"
            )
        if spec.item_type == "likert":
            if not 1 <= value <= item.max_value:
                raise ValueError(
                    f"量表 {code} 第 {item.order} 题为 Likert 题，作答需在 1..{item.max_value}，实际 {value}"
                )
            processed.append((item.max_value + 1 - value) if item.reverse else value)
        else:
            processed.append(value)

    if spec.item_type == "count":
        raw_total = sum(processed)
        normalized = min(1.0, raw_total / (spec.item_count * 7)) if spec.item_count else 0.0
    else:
        mean = sum(processed) / len(processed)
        raw_total = int(round(sum(processed)))
        # 1..5 → 0..1
        normalized = round((mean - 1.0) / 4.0, 4)

    return {
        "raw_total": raw_total,
        "normalized": normalized,
        "lai_input": spec.lai_input,
        "lai_value": float(raw_total) if spec.item_type == "count" else normalized,
    }


def item_type_out_of_range(value: int, max_value: int) -> bool:
    """计数题允许 0；Likert 题最小值由 score() 单独校验。"""
    return value < 0 or value > max_value


def catalog_fingerprint() -> str:
    """量表目录指纹 —— 供审计与可复现性引用（题项或计分变更时应变化）。"""
    import hashlib

    blob = "|".join(
        f"{s.code}:{s.item_type}:{s.lai_input}:" + ",".join(
            f"{i.order}{i.text_zh}{int(i.reverse)}{i.max_value}" for i in s.items
        )
        for s in INSTRUMENTS
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]
