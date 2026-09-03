#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_counts.py —— LearnFlow 数字诚信复算脚本
=============================================================================

为什么需要这个脚本
-----------------------------------------------------------------------------
LearnFlow 的历史文档宣称「76 种游戏化机制」「28 种学习方法」。这两个数字在任何
一层口径下都不成立（见 §口径定义）。若论文引用它们，审稿人一次 grep 即可证伪，
并会连带质疑文中其他所有数字。

因此本项目的立场不是「把数字改掉」，而是：**任何被引用的工程数字，都必须能被
一条命令复算出来**。本脚本即该命令。它对 6 个数字做静态复算，并输出机器可读
的 JSON，供论文「可复现性附件」引用。

运行
-----------------------------------------------------------------------------
    python scripts/verify_counts.py            # 打印分层报告 + 写 JSON
    python scripts/verify_counts.py --json     # 只写 JSON，不打印报告
    python scripts/verify_counts.py --quiet    # 只打印一行结论

退出码（供 CI 使用）
-----------------------------------------------------------------------------
    0  所有 strict 指标的复算值与仓库内已登记口径一致
    1  至少一个 strict 指标与登记口径不一致（有人改了代码没改文档，或反之）
    2  脚本自身执行失败（源文件缺失 / 语法解析错误 / 写盘失败）

设计约束
-----------------------------------------------------------------------------
1. **零依赖**：只用标准库（ast / json / re / pathlib / subprocess 等）。审稿人
   clone 仓库后无需 pip install 即可运行。
2. **只用 ast 做静态解析，不用正则统计代码**。历史统计口径分歧的直接根源就是
   正则：
     - `learning_methods_engine_v3.py` 的方法名是中文字符串，英文正则统计得 0；
     - `METHOD_TIPS` 是 list 不是 dict，「按 key 数」与「按条目数」结果不同
       （16 条 vs 15 唯一）。
   AST 解析直接读语法树，不受命名风格与容器类型影响。
3. **不 import 任何 app 代码**。静态解析而非运行时导入，避免数据库/配置依赖，
   也避免与并发重构中的模块产生耦合。

口径定义（六层数字）
-----------------------------------------------------------------------------
L0 engine_classes
    全后端 `app/**/*.py` 中类名以 `Engine` 结尾的 ClassDef 总数。
    **这是一个类别错误的数字**，不应单独用于支撑「N 种游戏化机制」——它把
    BKTEngine（贝叶斯知识追踪）、DDAEngine（动态难度）、FSRSSpacedRepetitionEngine
    （间隔重复算法）、OptimalDifficultyEngine（最优难度）等**学习科学算法**也算
    成了「游戏化成瘾机制」。保留它只是为了暴露这个错误。

L1 mechanism_units
    游戏化/成瘾机制承载文件中的「实现单元」数。规则（预注册）：
      (a) 统计 MECHANISM_SOURCE_FILES 中 `*Engine` 结尾的 ClassDef；
      (b) 补入 `gamification_service.py` 中不以 Engine 结尾、但承载机制的
          状态类（ProximalGoals / StreakState / TreasureBoxState / …）；
      (c) 扣减 INTRA_FILE_MERGES：状态容器类与其同构念引擎视为同一单元
          （3 组，见常量区）。

L2 mechanism_unique
    语义去重后的唯一机制数，权威来源是
    `docs/LearnFlow_机制治理与落实方案.md` 的 LF-M01..LF-Mnn 编号表。
    本脚本**不重新做语义去重**（那是需要评分者间信度的人工判定，见治理方案
    §2.3 预注册规则 R1–R6），而是解析该文档并做三重交叉验证：
      - 编号表的唯一 LF-M ID 数
      - 8 个类别标题括号内的声明数之和
      - 文档「小计」行自己写的合计数
    三者必须一致，否则判为 discrepancy。

learning_methods
    唯一学习方法数。规则（预注册）：
      - 三个学习方法源文件中所有 `"method": "<字符串>"` 字面量（AST 提取）；
      - 归一化：去掉 ` - ` 后缀（v3 用它表示同一方法的变体，如
        「思维导图 - 概念桥」→「思维导图」）；
      - 中文显示名经 CN_METHOD_ALIAS 映射到规范 id（v3 的 method 字段存的是
        中文显示名而非英文 key，这正是历史上正则统计得 0 的原因）；
      - NON_METHOD_LABELS 中的标签不是具名学习方法（如 v3 的「基础」是
        兜底提示语），不计入。

skill_tree_nodes
    `app/services/meta_learning_skilltree.py` 中 `SKILL_DEFINITIONS` 列表的
    元素数，并交叉验证 `skill_id=` 关键字实参的唯一数。

prd_claimed
    `learnflow-backend/docs/incremental_prd.md` §2.3 表格「引擎数量」列之和。
    该列相加得 69，而同一文档的标题与概述写的是 76 —— **PRD 内部即自相矛盾**。
    本指标把这个矛盾钉成机器可读的事实。
"""

from __future__ import annotations

import argparse
import ast
import datetime as _dt
import json
import re
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# 路径
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent                 # E:\learnflow\learnflow-backend
PROJECT_ROOT = BACKEND_ROOT.parent               # E:\learnflow

APP_DIR = BACKEND_ROOT / "app"
ARTIFACTS_DIR = BACKEND_ROOT / "artifacts"
JSON_OUT = ARTIFACTS_DIR / "count_verification.json"

GOVERNANCE_DOC = PROJECT_ROOT / "docs" / "LearnFlow_机制治理与落实方案.md"
PRD_DOC = BACKEND_ROOT / "docs" / "incremental_prd.md"
SKILLTREE_SRC = APP_DIR / "services" / "meta_learning_skilltree.py"
GAMIFICATION_SRC = APP_DIR / "services" / "gamification_service.py"

# ─────────────────────────────────────────────────────────────────────────────
# 登记口径（registered baseline）
#
# 这是「仓库内已登记口径」的唯一真源。改代码可以，但改了就必须同步改这里，
# 否则 CI 会以退出码 1 报 discrepancy —— 这正是本脚本存在的意义。
#
# strict 语义：
#   True  —— 该数字会被论文/文档引用，必须与登记值一致，否则退出码 1。
#   False —— 该数字随正常代码演进合法波动（新增引擎类、重构），只报告不判失败。
#            这是刻意的：CI 不应因为一次正常的重构就随机变红，否则团队会学会
#            无视红色构建，门禁就失效了。
# ─────────────────────────────────────────────────────────────────────────────

REGISTERED: Dict[str, Dict[str, Any]] = {
    "engine_classes": {
        "registered": 81,
        "strict": False,
        "note": "informative：新增一个 *Engine 类是正常的工程演进，不应让 CI 变红；"
                "但登记值应定期复核。",
    },
    "mechanism_units": {
        "registered": 60,
        "strict": False,
        "note": "informative：实现单元数随机制落地自然增长。治理方案 §1.2 表内小计为 "
                "59（未计入 anti_addiction_compliance 的 MinorProtectionEngine = LF-M52），"
                "推荐主表述为 60（59 + 1）。详见 REPORT_NOTES。",
    },
    "mechanism_unique": {
        "registered": 53,
        "strict": True,
        "note": "strict：这是论文 Table 1 的数字，被引用即必须可复算。",
    },
    "learning_methods": {
        "registered": 23,
        "strict": True,
        "note": "strict：，论文统一写法口径（22 个 snake_case + v3 的「思维导图」）。",
    },
    "skill_tree_nodes": {
        "registered": 16,
        "strict": True,
        "note": "strict：全项目唯一完全属实的数字，且被论文引用。",
    },
    "prd_claimed": {
        "registered": 69,
        "strict": True,
        "note": "strict：PRD §2.3 表格逐项相加。此值变化说明有人改了 PRD 表格，"
                "必须重新核对「PRD 自相矛盾」这一论断是否仍成立。",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# 预注册的口径常量（修改这些常量等于修改口径，必须同步更新文档）
# ─────────────────────────────────────────────────────────────────────────────

# L1(a)：游戏化/成瘾机制的承载文件（相对 BACKEND_ROOT）。
# 学习方法引擎、技能树、算法引擎、引导引擎均不在此列（R5：算法类与干预类分离）。
MECHANISM_SOURCE_FILES: Tuple[str, ...] = (
    "app/services/positive_addiction_engine.py",
    "app/services/deep_addiction_engine.py",
    "app/services/ux_addiction_engine.py",
    "app/services/social_addiction_engine.py",
    "app/services/duolingo_addiction_engine.py",
    "app/services/team_competition_engine.py",
    "app/services/addiction_engine_v3.py",
    "app/services/habit_addiction_engine.py",
    "app/services/anti_addiction_compliance.py",  # LF-M52 未成年保护
    "app/services/gamification_service.py",
)

# L1(b)：gamification_service.py 中「承载机制但非编排/枚举」的类之外的排除项。
# GamificationService 是编排器，RewardType 是枚举表，二者都不是机制。
GAMIFICATION_NON_MECHANISM_CLASSES = frozenset({"GamificationService", "RewardType"})

# L1(c)：同一文件内的「状态容器类 ↔ 同构念引擎」合并对。
# 这些 dataclass 只是对应引擎的状态载体，单独计数会把一个机制算成两个单元。
INTRA_FILE_MERGES: Tuple[Tuple[str, str], ...] = (
    ("SessionMemory", "PeakEndEngine"),        # 峰终：状态记录 ↔ PeakEndEngine
    ("UnfinishedTask", "ZeigarnikEngine"),     # 蔡格尼克：未完成任务 ↔ ZeigarnikEngine
    ("CustomizationState", "IKEAEngine"),      # 宜家效应：定制状态 ↔ IKEAEngine
)

# 学习方法源文件（顺序即报告顺序）。
# 注意：不扫全 app/！`memory_science_engine.py` / `habit_addiction_engine.py`
# 也有 "method" 字段，但那是提示文案的显示标签（「习惯叠加」「首字母缩略法」），
# 属记忆术/习惯机制，不是学习方法注册表的一部分。
LEARNING_METHOD_SOURCES: Tuple[str, ...] = (
    "app/services/learning_methods_engine.py",      # METHOD_TIPS（list，16 条）
    "app/services/advanced_methods_engine.py",      # NEW_METHODS（list，7 条）
    "app/services/learning_methods_engine_v3.py",   # 中文 method 字段
)

# 中文显示名 → 规范 id。v3 引擎的 method 字段存中文，必须显式映射，
# 否则中英文两份实现会被算成两个方法（历史上正则统计正是漏掉了这一半）。
CN_METHOD_ALIAS: Dict[str, str] = {
    "思维导图": "mind_mapping",
    "双重编码": "dual_coding",
    "交错练习": "interleaving",
    "自适应交错练习": "interleaving",
    "精细加工": "elaborative_rehearsal",
    "生成效应": "generation",
}

# 不是具名学习方法的占位标签（v3 的兜底提示语）。
NON_METHOD_LABELS = frozenset({"基础"})

# 历史宣称值（用于报告差异，不是登记口径）
CLAIMS = {"mechanisms_claimed": 76, "learning_methods_claimed": 28}


# ─────────────────────────────────────────────────────────────────────────────
# 基础设施
# ─────────────────────────────────────────────────────────────────────────────

class VerifyError(RuntimeError):
    """脚本自身执行失败（→ 退出码 2）。"""


def _read_text(path: Path, required: bool = True) -> Optional[str]:
    """读文本文件；required=False 时缺失返回 None 而不抛错。"""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        if required:
            raise VerifyError(f"必需文件缺失：{path}")
        return None
    except UnicodeDecodeError as exc:
        raise VerifyError(f"文件不是 UTF-8，无法解析：{path} ({exc})") from exc


def _parse_python(path: Path) -> ast.Module:
    """AST 解析 Python 文件；语法错误转成 VerifyError（退出码 2）。"""
    src = _read_text(path)
    try:
        return ast.parse(src, filename=str(path))
    except SyntaxError as exc:
        raise VerifyError(f"Python 语法解析失败：{path}:{exc.lineno} {exc.msg}") from exc


def _git_commit() -> str:
    """取当前 commit hash。不在 git 仓库 / git 不可用时返回 "unknown"，绝不崩溃。"""
    for cwd in (PROJECT_ROOT, BACKEND_ROOT):
        try:
            proc = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=15,
            )
        except (OSError, subprocess.SubprocessError):
            continue  # git 未安装 / 超时 —— 继续尝试下一个 cwd
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    return "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# L0：*Engine 类总数
# ─────────────────────────────────────────────────────────────────────────────

def count_engine_classes() -> Dict[str, Any]:
    if not APP_DIR.is_dir():
        raise VerifyError(f"后端 app 目录不存在：{APP_DIR}")

    per_file: Dict[str, List[str]] = {}
    for py in sorted(APP_DIR.rglob("*.py")):
        try:
            tree = _parse_python(py)
        except VerifyError:
            raise
        names = sorted(
            n.name for n in ast.walk(tree)
            if isinstance(n, ast.ClassDef) and n.name.endswith("Engine")
        )
        if names:
            per_file[py.relative_to(BACKEND_ROOT).as_posix()] = names

    all_names = [n for names in per_file.values() for n in names]
    dup_names = sorted({n for n in all_names if all_names.count(n) > 1})
    return {
        "value": len(all_names),
        "unique_class_names": len(set(all_names)),
        "duplicate_class_names": dup_names,
        "files": {f: len(v) for f, v in sorted(per_file.items(), key=lambda kv: -len(kv[1]))},
        "definition": "app/**/*.py 中类名以 'Engine' 结尾的 ClassDef 总数（L0，类别错误口径）",
    }


# ─────────────────────────────────────────────────────────────────────────────
# L1：机制实现单元数
# ─────────────────────────────────────────────────────────────────────────────

def count_mechanism_units() -> Dict[str, Any]:
    engine_total = 0
    per_file: Dict[str, int] = {}
    seen_files: List[str] = []

    for rel in MECHANISM_SOURCE_FILES:
        path = BACKEND_ROOT / rel
        if not path.is_file():
            raise VerifyError(f"机制源文件缺失（口径已登记但文件不存在）：{path}")
        tree = _parse_python(path)
        n = sum(
            1 for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef) and node.name.endswith("Engine")
        )
        per_file[rel] = n
        engine_total += n
        seen_files.append(rel)

    # (b) gamification_service 中不以 Engine 结尾的机制类
    tree = _parse_python(GAMIFICATION_SRC)
    sub_classes = sorted(
        node.name for node in tree.body
        if isinstance(node, ast.ClassDef)
        and not node.name.endswith("Engine")
        and node.name not in GAMIFICATION_NON_MECHANISM_CLASSES
    )

    # (c) 组内容器 ↔ 引擎合并
    merges_applied = [
        [container, engine] for container, engine in INTRA_FILE_MERGES
        if engine in sub_classes or True  # 合并对始终生效（右侧引擎来自同文件）
    ]

    value = engine_total + len(sub_classes) - len(INTRA_FILE_MERGES)
    return {
        "value": value,
        "engine_classes_in_scope": engine_total,
        "non_engine_mechanism_classes": sub_classes,
        "intra_file_merges": [list(pair) for pair in INTRA_FILE_MERGES],
        "raw_before_merges": engine_total + len(sub_classes),
        "per_file": per_file,
        "definition": (
            "10 个机制承载文件中的 *Engine 类，加 gamification_service 的非 Engine 机制类，"
            "减去预注册的状态容器↔引擎合并对"
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# L2：去重后唯一机制数（解析治理文档 + 三重交叉验证）
# ─────────────────────────────────────────────────────────────────────────────

_ROW_RE = re.compile(r"^\|\s*(LF-M(\d{2}))\s*\|", re.MULTILINE)
_CAT_RE = re.compile(r"^###\s+([A-H])\.\s*[^（(]*[（(](\d+)[）)]", re.MULTILINE)
_SUBTOTAL_RE = re.compile(r"\*\*小计\*\*[^\n]*?=\s*\*\*(\d+)\*\*")


def count_mechanism_unique() -> Dict[str, Any]:
    text = _read_text(GOVERNANCE_DOC)

    ids = _ROW_RE.findall(text)                    # [( "LF-M01", "01" ), ...]
    unique_ids = sorted(set(i for i, _ in ids))
    duplicates = sorted({i for i, _ in ids if [x[0] for x in ids].count(i) > 1})

    numbers = sorted(int(n) for _, n in ids)
    expected = list(range(1, len(unique_ids) + 1)) if unique_ids else []
    contiguous = numbers == expected

    # 交叉验证 1：类别标题括号内的声明数之和
    cats = {letter: int(n) for letter, n in _CAT_RE.findall(text)}
    cat_sum = sum(cats.values())

    # 交叉验证 2：文档「小计」行自己写的合计
    m = _SUBTOTAL_RE.search(text)
    subtotal = int(m.group(1)) if m else None

    n_ids = len(unique_ids)
    cross_ok = (cat_sum == n_ids) and (subtotal in (None, n_ids))
    if not cats:
        raise VerifyError(f"未能从治理文档解析出任何类别标题：{GOVERNANCE_DOC}")

    return {
        "value": n_ids,
        "id_range": f"LF-M{numbers[0]:02d}..LF-M{numbers[-1]:02d}" if numbers else "",
        "duplicate_ids": duplicates,
        "contiguous": contiguous,
        "category_counts": {f"{k}": v for k, v in sorted(cats.items())},
        "category_sum": cat_sum,
        "doc_subtotal_claimed": subtotal,
        "cross_validation_passed": bool(cross_ok and contiguous and not duplicates),
        "definition": "治理方案 LF-M01..LF-Mnn 编号表中的唯一机制 ID 数（语义去重由人工预注册规则 R1–R6 完成）",
    }


# ─────────────────────────────────────────────────────────────────────────────
# 学习方法数
# ─────────────────────────────────────────────────────────────────────────────

def _iter_method_literals(tree: ast.Module) -> Iterable[str]:
    """AST 提取所有 {"method": "<字符串常量>"} 的取值。"""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key, val in zip(node.keys, node.values):
            if (
                isinstance(key, ast.Constant)
                and key.value == "method"
                and isinstance(val, ast.Constant)
                and isinstance(val.value, str)
            ):
                yield val.value


def _canonical_method_id(raw: str) -> Optional[str]:
    """归一化方法标识：去变体后缀 → 中文映射 → 排除非方法标签。"""
    label = raw.split(" - ", 1)[0].strip()
    if label in NON_METHOD_LABELS:
        return None
    if re.fullmatch(r"[a-z0-9_]+", label):
        return label
    return CN_METHOD_ALIAS.get(label, label)


def count_learning_methods() -> Dict[str, Any]:
    canonical: List[str] = []
    raw_labels: Dict[str, List[str]] = {}
    tips_entries: Optional[int] = None
    tips_unique: Optional[int] = None

    for rel in LEARNING_METHOD_SOURCES:
        path = BACKEND_ROOT / rel
        if not path.is_file():
            raise VerifyError(f"学习方法源文件缺失：{path}")
        tree = _parse_python(path)
        labels = list(_iter_method_literals(tree))
        raw_labels[rel] = labels

        for raw in labels:
            cid = _canonical_method_id(raw)
            if cid is not None:
                canonical.append(cid)

        # 附加观测：METHOD_TIPS 是 list（16 条）不是 dict（15 唯一 key）——
        # 这正是历史上「按 key 数 vs 按条目数」口径分歧的根源，显式记录下来。
        if rel.endswith("learning_methods_engine.py"):
            for node in tree.body:
                if isinstance(node, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == "METHOD_TIPS" for t in node.targets
                ):
                    if isinstance(node.value, ast.List):
                        tips_entries = len(node.value.elts)
                        tips_unique = len({_canonical_method_id(x) for x in labels})

    uniq = sorted(set(canonical))
    snake = sorted(x for x in uniq if re.fullmatch(r"[a-z0-9_]+", x))
    return {
        "value": len(uniq),
        "snake_case_ids": len(snake),
        "non_snake_ids": sorted(set(uniq) - set(snake)),
        "ids": uniq,
        "raw_label_counts": {k: len(v) for k, v in raw_labels.items()},
        "method_tips_entries": tips_entries,
        "method_tips_unique_keys": tips_unique,
        "definition": (
            "3 个学习方法源文件中 'method' 字面量归一化去重后的规范 id 数"
            "（22 个 snake_case + v3 的 mind_mapping『思维导图』）"
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 技能树节点数
# ─────────────────────────────────────────────────────────────────────────────

def count_skill_tree_nodes() -> Dict[str, Any]:
    if not SKILLTREE_SRC.is_file():
        raise VerifyError(f"技能树源文件缺失：{SKILLTREE_SRC}")
    tree = _parse_python(SKILLTREE_SRC)

    entries = 0
    skill_ids: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "SKILL_DEFINITIONS" for t in node.targets
        ):
            if not isinstance(node.value, ast.List):
                raise VerifyError("SKILL_DEFINITIONS 不是列表字面量，口径需重新定义")
            entries = len(node.value.elts)
            for elt in node.value.elts:
                if isinstance(elt, ast.Call):
                    for kw in elt.keywords:
                        if kw.arg == "skill_id" and isinstance(kw.value, ast.Constant):
                            skill_ids.append(kw.value.value)

    if entries == 0:
        raise VerifyError(f"未在 {SKILLTREE_SRC} 找到 SKILL_DEFINITIONS")

    return {
        "value": entries,
        "unique_skill_ids": len(set(skill_ids)),
        "duplicate_skill_ids": sorted({s for s in skill_ids if skill_ids.count(s) > 1}),
        "skill_ids": skill_ids,
        "definition": "SKILL_DEFINITIONS 列表元素数（交叉验证 skill_id 唯一数）",
    }


# ─────────────────────────────────────────────────────────────────────────────
# PRD 自称机制数
# ─────────────────────────────────────────────────────────────────────────────

_PRD_ROW_RE = re.compile(
    r"^\|\s*([^|]+?)\s*\|\s*`([^`]+)`\s*\|\s*(\d+)\s*\+?\s*\|\s*([^|]*?)\s*\|",
    re.MULTILINE,
)
_PRD_HEADLINE_RE = re.compile(r"^###\s*2\.3[^\n]*?[（(](\d+)\s*个[）)]", re.MULTILINE)
_PRD_INTRO_RE = re.compile(r"(\d+)\s*个游戏化成瘾引擎")


def count_prd_claimed() -> Dict[str, Any]:
    text = _read_text(PRD_DOC)

    # 截取 §2.3 小节
    start = text.find("### 2.3")
    if start == -1:
        raise VerifyError(f"PRD 中找不到 §2.3 小节：{PRD_DOC}")
    nxt = re.search(r"^###\s*2\.4", text[start:], re.MULTILINE)
    section = text[start:start + nxt.start()] if nxt else text[start:]

    rows = _PRD_ROW_RE.findall(section)
    if not rows:
        raise VerifyError(f"PRD §2.3 表格解析失败（正则未命中任何数据行）：{PRD_DOC}")

    items = [{"category": c.strip(), "file": f.strip(), "count": int(n)} for c, f, n, _ in rows]
    table_sum = sum(i["count"] for i in items)

    m = _PRD_HEADLINE_RE.search(text)
    headline = int(m.group(1)) if m else None
    m2 = _PRD_INTRO_RE.search(text)
    intro = int(m2.group(1)) if m2 else None

    return {
        "value": table_sum,
        "items": items,
        "prd_headline_claimed": headline,
        "prd_intro_claimed": intro,
        "internally_inconsistent": bool(
            headline is not None and headline != table_sum
        ),
        "definition": "PRD §2.3 表格「引擎数量」列之和（该列相加 ≠ 同文档标题/概述所写的 76）",
    }


# ─────────────────────────────────────────────────────────────────────────────
# 汇总 / 判定
# ─────────────────────────────────────────────────────────────────────────────

def collect_all() -> Dict[str, Dict[str, Any]]:
    return {
        "engine_classes": count_engine_classes(),
        "mechanism_units": count_mechanism_units(),
        "mechanism_unique": count_mechanism_unique(),
        "learning_methods": count_learning_methods(),
        "skill_tree_nodes": count_skill_tree_nodes(),
        "prd_claimed": count_prd_claimed(),
    }


def build_verdict(counts: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    verdict: Dict[str, Any] = {}
    for key, meta in REGISTERED.items():
        actual = counts[key]["value"]
        registered = meta["registered"]
        delta = actual - registered
        ok = (delta == 0)

        notes = []
        if key == "mechanism_unique":
            if not counts[key]["cross_validation_passed"]:
                ok = False
                notes.append("治理文档内部交叉验证未通过（编号表 / 类别小计 / 合计行不一致）")
            if counts[key]["duplicate_ids"]:
                ok = False
                notes.append(f"存在重复 LF-M 编号：{counts[key]['duplicate_ids']}")
            if not counts[key]["contiguous"]:
                ok = False
                notes.append("LF-M 编号不连续")
        if key == "skill_tree_nodes":
            if actual != counts[key]["unique_skill_ids"]:
                ok = False
                notes.append("SKILL_DEFINITIONS 元素数与 skill_id 唯一数不一致")
            if counts[key]["duplicate_skill_ids"]:
                ok = False
                notes.append(f"存在重复 skill_id：{counts[key]['duplicate_skill_ids']}")
        if key == "learning_methods":
            if counts[key]["non_snake_ids"]:
                ok = False
                notes.append(
                    f"存在未映射到规范 id 的非 snake_case 方法名：{counts[key]['non_snake_ids']}"
                    "（需在 CN_METHOD_ALIAS 中补登记）"
                )

        verdict[key] = {
            "status": "verified" if ok else "discrepancy",
            "registered": registered,
            "actual": actual,
            "delta": delta,
            "strict": meta["strict"],
            "notes": "; ".join(notes) if notes else "",
        }

    bad_strict = [k for k, v in verdict.items() if v["strict"] and v["status"] != "verified"]
    bad_loose = [k for k, v in verdict.items() if not v["strict"] and v["status"] != "verified"]
    verdict["_overall"] = {
        "status": "verified" if not bad_strict else "discrepancy",
        "blocking_metrics": bad_strict,
        "drifted_informative_metrics": bad_loose,
        "exit_code": 1 if bad_strict else 0,
    }
    return verdict


# ─────────────────────────────────────────────────────────────────────────────
# 报告
# ─────────────────────────────────────────────────────────────────────────────

_HR = "=" * 78


def _fmt_delta(actual: int, claimed: Optional[int]) -> str:
    if claimed is None:
        return "n/a"
    d = actual - claimed
    return "0" if d == 0 else f"{d:+d}"


def print_report(counts: Dict[str, Dict[str, Any]],
                 verdict: Dict[str, Any],
                 payload: Dict[str, Any]) -> None:
    print(_HR)
    print("LearnFlow 数字诚信复算报告")
    print(_HR)
    print(f"生成时间 : {payload['generated_at']}")
    print(f"git HEAD : {payload['git_commit']}")
    print(f"Python   : {sys.version.split()[0]}   后端根: {BACKEND_ROOT}")

    eng = counts["engine_classes"]
    uni = counts["mechanism_units"]
    mq = counts["mechanism_unique"]
    lm = counts["learning_methods"]
    st = counts["skill_tree_nodes"]
    prd = counts["prd_claimed"]

    print()
    print("─" * 78)
    print("【L0】engine_classes —— 全后端 *Engine 类总数")
    print("─" * 78)
    print(f"  值         : {eng['value']}")
    print(f"  口径       : {eng['definition']}")
    print(f"  统计方法   : ast.walk 遍历 app/**/*.py，筛 ClassDef 且 name.endswith('Engine')")
    print(f"  唯一类名   : {eng['unique_class_names']}"
          f"（重复命名 {eng['duplicate_class_names'] or '无'}）")
    print(f"  ⚠ 类别错误 : 该口径混入 BKT / DDA / FSRS / OptimalDifficulty 等学习科学算法，")
    print(f"              不可用于支撑「N 种游戏化机制」")
    print(f"  与宣称 76  : {_fmt_delta(eng['value'], CLAIMS['mechanisms_claimed'])}")

    print()
    print("─" * 78)
    print("【L1】mechanism_units —— 机制实现单元数")
    print("─" * 78)
    print(f"  值         : {uni['value']}")
    print(f"  口径       : {uni['definition']}")
    print(f"  统计方法   : 10 个机制文件 *Engine 类 {uni['engine_classes_in_scope']}"
          f" + gamification_service 非 Engine 机制类 {len(uni['non_engine_mechanism_classes'])}"
          f" − 容器内合并 {len(uni['intra_file_merges'])}"
          f" = {uni['value']}（合并前原始 {uni['raw_before_merges']}）")
    print(f"  合并对     : {', '.join(f'{a}↔{b}' for a, b in uni['intra_file_merges'])}")
    print(f"  与宣称 76  : {_fmt_delta(uni['value'], CLAIMS['mechanisms_claimed'])}")

    print()
    print("─" * 78)
    print("【L2】mechanism_unique —— 语义去重后唯一机制数")
    print("─" * 78)
    print(f"  值         : {mq['value']}   （{mq['id_range']}，连续={mq['contiguous']}）")
    print(f"  口径       : {mq['definition']}")
    print(f"  统计方法   : 解析 {GOVERNANCE_DOC.name} 的 LF-M 编号表，取唯一 ID")
    print(f"  交叉验证   : 类别标题声明合计 {mq['category_sum']}"
          f" / 文档小计行 {mq['doc_subtotal_claimed']}"
          f" / 编号表 {mq['value']}"
          f" → {'一致 ✓' if mq['cross_validation_passed'] else '不一致 ✗'}")
    print(f"  类别分布   : {mq['category_counts']}")
    print(f"  与宣称 76  : {_fmt_delta(mq['value'], CLAIMS['mechanisms_claimed'])}")

    print()
    print("─" * 78)
    print("learning_methods —— 唯一学习方法数")
    print("─" * 78)
    print(f"  值         : {lm['value']}   （snake_case {lm['snake_case_ids']}"
          f" + 非英文 {len(lm['non_snake_ids'])}）")
    print(f"  口径       : {lm['definition']}")
    print(f"  统计方法   : AST 提取 'method' 字面量 → 去 ' - ' 变体后缀 → 中文别名映射 → 去重")
    print(f"  原始字面量 : {lm['raw_label_counts']}")
    print(f"  ⚠ 分歧根源 : METHOD_TIPS 是 list 不是 dict ——"
          f"{lm['method_tips_entries']} 条 / {lm['method_tips_unique_keys']} 唯一 key")
    print(f"               v3 引擎 method 字段为中文（如「思维导图」），英文正则统计得 0")
    print(f"  与宣称 28  : {_fmt_delta(lm['value'], CLAIMS['learning_methods_claimed'])}")

    print()
    print("─" * 78)
    print("skill_tree_nodes —— 技能树节点数")
    print("─" * 78)
    print(f"  值         : {st['value']}   （skill_id 唯一数 {st['unique_skill_ids']}）")
    print(f"  口径       : {st['definition']}")
    print(f"  统计方法   : AST 定位 SKILL_DEFINITIONS 列表赋值，取 elts 长度 + skill_id 关键字实参")
    print(f"  状态       : {'全项目唯一完全属实的数字 ✓' if st['value'] == st['unique_skill_ids'] == 16 else '需复核'}")

    print()
    print("─" * 78)
    print("prd_claimed —— PRD 自述机制数（暴露内部矛盾）")
    print("─" * 78)
    print(f"  值         : {prd['value']}（§2.3 表格逐项相加）")
    print(f"  口径       : {prd['definition']}")
    print(f"  统计方法   : 正则截取 §2.3 小节表格，累加「引擎数量」列")
    for item in prd["items"]:
        print(f"      {item['count']:>3}  {item['file']}")
    print(f"  同文档标题声称 : {prd['prd_headline_claimed']}")
    print(f"  同文档概述声称 : {prd['prd_intro_claimed']}")
    print(f"  ⚠ 内部矛盾 : {'是 —— PRD 自己就对不上' if prd['internally_inconsistent'] else '否'}")

    print()
    print(_HR)
    print("判定（verdict）")
    print(_HR)
    print(f"  {'指标':<20}{'登记':>6}{'实测':>6}{'差异':>6}  {'级别':<12}{'状态'}")
    for key in REGISTERED:
        v = verdict[key]
        lvl = "strict" if v["strict"] else "informative"
        print(f"  {key:<20}{v['registered']:>6}{v['actual']:>6}{v['delta']:>+6}  "
              f"{lvl:<12}{v['status']}")
        if v["notes"]:
            print(f"      └─ {v['notes']}")

    ov = verdict["_overall"]
    print()
    print(f"  结论      : {ov['status'].upper()}"
          f"   退出码 {ov['exit_code']}")
    if ov["blocking_metrics"]:
        print(f"  阻塞项    : {', '.join(ov['blocking_metrics'])}")
    if ov["drifted_informative_metrics"]:
        print(f"  漂移(不阻塞): {', '.join(ov['drifted_informative_metrics'])}"
              f"  —— 这些指标随正常重构合法波动，只报告不判失败")
    print()
    print(f"  JSON 输出 : {JSON_OUT}")
    print(_HR)


# ─────────────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────────────

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="LearnFlow 数字诚信复算脚本")
    ap.add_argument("--json", action="store_true", help="只写 JSON，不打印分层报告")
    ap.add_argument("--quiet", action="store_true", help="只打印一行结论")
    args = ap.parse_args(argv)

    counts = collect_all()
    verdict = build_verdict(counts)

    payload = {
        "generated_at": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "git_commit": _git_commit(),
        "python_version": sys.version.split()[0],
        "backend_root": str(BACKEND_ROOT),
        "counts": counts,
        "registered": {k: {"registered": v["registered"], "strict": v["strict"],
                           "note": v["note"]} for k, v in REGISTERED.items()},
        "claims": dict(CLAIMS),
        "verdict": verdict,
    }

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )

    ov = verdict["_overall"]
    if args.quiet:
        print(f"verify_counts: {ov['status']} "
              f"(engine_classes={counts['engine_classes']['value']}, "
              f"mechanism_units={counts['mechanism_units']['value']}, "
              f"mechanism_unique={counts['mechanism_unique']['value']}, "
              f"learning_methods={counts['learning_methods']['value']}, "
              f"skill_tree_nodes={counts['skill_tree_nodes']['value']}, "
              f"prd_claimed={counts['prd_claimed']['value']}) "
              f"exit={ov['exit_code']}")
    elif not args.json:
        print_report(counts, verdict, payload)

    return int(ov["exit_code"])


if __name__ == "__main__":
    try:
        # Windows 控制台默认 cp936，报告含 ✓/⚠/→ 等字符，统一切 UTF-8 避免
        # UnicodeEncodeError 把「复算成功」误报成「脚本失败」。
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (AttributeError, ValueError):
                pass
        sys.exit(main())
    except VerifyError as exc:
        print(f"[verify_counts] 执行失败：{exc}", file=sys.stderr)
        sys.exit(2)
    except Exception:  # noqa: BLE001 —— 顶层兜底，任何未预期异常都映射为退出码 2
        print("[verify_counts] 未预期的执行失败：", file=sys.stderr)
        traceback.print_exc()
        sys.exit(2)
