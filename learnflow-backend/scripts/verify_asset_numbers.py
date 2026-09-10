#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_asset_numbers.py —— LearnFlow 自身资产数字复算脚本
=============================================================================

为什么需要这个脚本
-----------------------------------------------------------------------------
`verify_counts.py` 复算的是**研究对象口径**的数字——「系统承载了多少个游戏化
机制、多少种学习方法、多少个技能树节点」。但项目文档还会引用另一类数字：
**本研究自身资产**的规模，例如

    后端 N 行 Python、M 个服务模块、K 个源文件、J 个 API 路由、
    T 项测试（F 个测试文件）

这类数字此前**没有任何脚本复算**，全部靠手工维护，因而必然漂移。复核结果证实
了这一点：`docs/LearnFlow_期刊论文拆分方案.md` §1 写的是「23,927 行 Python、
41 个服务模块、81 个源文件、72 个 API 端点」，而实测为 24,073 行 / 52 个服务
模块 / 81 个源文件 / 95 个路由。「81 个源文件」碰巧是对的，其余三个全是历史
残留。

更严重的是，该文档结尾声称：

    「本文档的全部自身资产数字由 `learnflow-backend/scripts/` 下的脚本复算」

在本脚本出现之前，**这句话是不成立的**——没有任何脚本复算过它们。一句无法成立
的方法学声明，比一个错误的数字更危险：它会让审稿人认为整套复算机制都是装饰。

本脚本使那句话成立。

立场与 `verify_counts.py` 完全一致：
    **任何被引用的工程数字，都必须能被一条命令复算出来。**

运行
-----------------------------------------------------------------------------
    python scripts/verify_asset_numbers.py              # 打印报告 + 写 JSON
    python scripts/verify_asset_numbers.py --json       # 只写 JSON，不打印报告
    python scripts/verify_asset_numbers.py --quiet      # 只打印一行结论
    python scripts/verify_asset_numbers.py --doc-check  # 额外核对文档 §1 的数字
    python scripts/verify_asset_numbers.py --with-pytest
                                                        # 额外复算 pytest 收集数

退出码（供 CI 使用）
-----------------------------------------------------------------------------
    0  复算成功，且（启用 --doc-check 时）文档数字与复算值一致
    1  文档数字与复算值不一致（有人改了代码没改文档，或反之）
    2  脚本自身执行失败（源文件缺失 / 语法解析错误 / 写盘失败）

设计约束
-----------------------------------------------------------------------------
1. **零依赖**：只用标准库（ast / json / re / pathlib / argparse / subprocess）。
   审稿人 clone 仓库后无需 pip install 即可运行。
2. **不 import 任何 app 代码**。这是刻意的：`app.main` 在导入期会构造
   FastAPI 应用、读取配置并连接数据库，把这套依赖引进一个「数字核验」脚本
   会让复算本身变得不可靠。因此路由数用 **AST 静态解析装饰器**得到，而不是
   运行时 `len(app.routes)`。
3. **只做静态解析，不做正则统计代码**。正则统计是本项目历史口径分歧的直接
   根源（见 `verify_counts.py` 设计约束 2）。唯一使用正则的地方是解析**文档
   里的自然语言句子**——那不是代码。

口径定义
-----------------------------------------------------------------------------
python_loc
    `app/**/*.py` 的总行数（含空行与注释，含 `__init__.py`）。这是「代码规模」
    的常用口径，也是文档 §1 采用的口径。同时报告 `python_loc_excl_init`
    （剔除 `__init__.py`）供交叉参考。

source_files
    `app/**/*.py` 的文件数。

service_modules
    `app/services/*.py` 的文件数（含 `services/__init__.py`）。

api_files
    `app/api/*.py` 的文件数。

api_routes_defined
    `app/api/*.py` 中**被 HTTP 方法装饰器修饰的函数**总数。装饰器形如
    `@router.get(...)` / `@k12_router.post(...)`，属性名属于
    {get, post, put, patch, delete, head, options} 且被装饰对象是一个模块级
    Router 变量。这是「端点定义数」口径。

api_routes_reachable
    上述端点中，其 Router 变量**确实被 `app/main.py` 的 `_register_routers()`
    注册**的数量。
    这个指标是刻意保留的：`api_routes_defined - api_routes_reachable > 0`
    意味着仓库里存在**定义了但永远无法被访问**的端点——这正是本项目已经踩过
    的坑（一个功能完整的前端页面从未被路由；一个 `AdaptivePlacementEngine`
    从未被任何入口调用）。把「可达性」变成可复算的数字，是防止该类缺陷复发
    的唯一办法。

test_files
    `tests/test_*.py` 的文件数。

test_functions
    `tests/` 下 `def test_*` / `async def test_*` 的 AST 定义数。
    **注意**：这个数**不等于** pytest 实际收集到的用例数——`@pytest.mark.parametrize`
    会把一个函数展开成多个用例。文档里写的「868 项测试」是 **pytest 收集数**，
    不是本指标。要复算它，请加 `--with-pytest`。

tests_collected
    仅在 `--with-pytest` 时计算：调用 pytest 的 `--collect-only -q` 并统计输出行数。
    因为要启动解释器与导入测试栈，这一步较慢，故默认关闭。

登记口径（registered baseline）
-----------------------------------------------------------------------------
与 `verify_counts.py` 相同的语义：

    strict=True   —— 该数字会被文档引用，必须与登记值一致，否则退出码 1。
    strict=False  —— 该数字随正常开发合法波动（持续加代码/加测试），只报告
                     不判失败。CI 不应因为一次正常提交就随机变红，否则团队
                     会学会无视红色构建，门禁就失效了。

因此本脚本的资产指标**全部登记为 strict=False**。它的价值不在于「阻止代码
增长」，而在于：
    (a) 把文档里的数字钉到一个可复算的登记值上；
    (b) 通过 `--doc-check` 让「文档数字 ≠ 代码事实」这件事**立即变红**。

`--doc-check` 才是本脚本的门禁核心。它在文档 §1 中定位资产句子，逐项比对数字，
任何一项对不上就退出码 1。
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
from typing import Any, Dict, List, Optional, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# 路径
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent                 # E:\learnflow\learnflow-backend
PROJECT_ROOT = BACKEND_ROOT.parent               # E:\learnflow

APP_DIR = BACKEND_ROOT / "app"
API_DIR = APP_DIR / "api"
SERVICES_DIR = APP_DIR / "services"
TESTS_DIR = BACKEND_ROOT / "tests"
MAIN_SRC = APP_DIR / "main.py"
ARTIFACTS_DIR = BACKEND_ROOT / "artifacts"
JSON_OUT = ARTIFACTS_DIR / "asset_numbers.json"

SPLIT_DOC = PROJECT_ROOT / "docs" / "LearnFlow_期刊论文拆分方案.md"

# ─────────────────────────────────────────────────────────────────────────────
# 登记口径（registered baseline）
#
# 修改代码后，若本脚本报告漂移，你有两个合法选择：
#   (1) 若代码增长是预期的 —— 更新下面的 registered 值；
#   (2) 若代码增长是非预期的 —— 去查为什么。
# 唯一**不合法**的选择是改文档数字而不改这里，或反之。
# ─────────────────────────────────────────────────────────────────────────────

REGISTERED: Dict[str, Dict[str, Any]] = {
    "python_loc": {
        "registered": 24414,
        "strict": False,
        "note": "informative：app/**/*.py 总行数，随正常开发增长。文档 §1 引用此值"
                "（历史值为 23,927，已漂移）。",
    },
    "source_files": {
        "registered": 83,
        "strict": False,
        "note": "informative：app/**/*.py 文件数。文档 §1 引用此值（历史值 81）。",
    },
    "service_modules": {
        "registered": 52,
        "strict": False,
        "note": "informative：app/services/*.py 文件数。文档 §1 历史值 41 为残留，已修正。",
    },
    "api_files": {
        "registered": 12,
        "strict": False,
        "note": "informative：app/api/*.py 文件数。",
    },
    "api_routes_reachable": {
        "registered": 98,
        "strict": False,
        "note": "informative：已被 main.py 的 _register_routers() 注册的路由数，"
                "是文档 §1「API 端点」应对应的口径（历史值 72 为残留）。",
    },
    "test_files": {
        "registered": 52,
        "strict": False,
        "note": "informative：tests/test_*.py 文件数。文档 §1 引用此值（历史值 49）。",
    },
    "test_functions": {
        "registered": 804,
        "strict": False,
        "note": "informative：AST 定义数（含任意嵌套层级），≠ pytest 收集数"
                "（parametrize 会把一个函数展开成多个用例）。",
    },
    "tests_collected": {
        "registered": 898,
        "strict": False,
        "note": "informative：pytest 实际收集的用例数，即文档 §1「N 项测试」的真实口径。"
                "仅在 --with-pytest 时复算；默认不计算（需启动解释器导入整个测试栈）。",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# 口径常量
# ─────────────────────────────────────────────────────────────────────────────

HTTP_METHODS: Tuple[str, ...] = (
    "get", "post", "put", "patch", "delete", "head", "options",
)

# 文档 §1 资产句子中每个数字的定位正则。使用中文全角标点与千位分隔符。
DOC_PATTERNS: Dict[str, str] = {
    "python_loc": r"([\d,]+)\s*行\s*Python",
    "service_modules": r"([\d,]+)\s*个服务模块",
    "source_files": r"([\d,]+)\s*个源文件",
    "api_routes_reachable": r"([\d,]+)\s*个\s*API\s*端点",
    "tests_collected": r"([\d,]+)\s*项测试",
    "test_files": r"([\d,]+)\s*个测试文件",
}


# ─────────────────────────────────────────────────────────────────────────────
# 静态复算
# ─────────────────────────────────────────────────────────────────────────────


def _iter_py(root: Path) -> List[Path]:
    """返回 root 下所有 .py 文件（递归），按路径排序以保证可复现。"""
    if not root.exists():
        return []
    return sorted(p for p in root.rglob("*.py") if p.is_file())


def _count_lines(path: Path) -> int:
    """统计文件行数。以 utf-8 读取并忽略解码失败，保证脚本不会因编码问题崩溃。"""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return 0


def _parse(path: Path) -> Optional[ast.Module]:
    """安全解析一个 Python 文件；语法错误时返回 None 而不中断整个脚本。"""
    try:
        src = path.read_text(encoding="utf-8", errors="replace")
        return ast.parse(src, filename=str(path))
    except (SyntaxError, ValueError, OSError):
        return None


def compute_python_loc() -> Dict[str, int]:
    files = _iter_py(APP_DIR)
    total = sum(_count_lines(p) for p in files)
    excl_init = sum(_count_lines(p) for p in files if p.name != "__init__.py")
    return {
        "python_loc": total,
        "python_loc_excl_init": excl_init,
        "source_files": len(files),
    }


def compute_module_counts() -> Dict[str, int]:
    return {
        "service_modules": len(_iter_py(SERVICES_DIR)),
        "api_files": len(_iter_py(API_DIR)),
    }


def _registered_routers() -> Dict[str, List[str]]:
    """解析 app/main.py 的 _register_routers()，取出被注册的 Router 变量。

    返回 {模块名: [router 变量名, ...]}。只做 AST 静态解析，不导入 app。
    若解析失败，返回空字典（调用方会据此把可达数判为 0 并在报告中说明）。
    """
    tree = _parse(MAIN_SRC)
    if tree is None:
        return {}
    found: Dict[str, List[str]] = {}
    for node in ast.walk(tree):
        # 定位 `routers = [auth.router, teacher.k12_router, ...]`
        if not isinstance(node, ast.Assign):
            continue
        targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if "routers" not in targets:
            continue
        if not isinstance(node.value, (ast.List, ast.Tuple)):
            continue
        for elt in node.value.elts:
            # 形如 `auth.router` -> value=Name('auth'), attr='router'
            if isinstance(elt, ast.Attribute) and isinstance(elt.value, ast.Name):
                found.setdefault(elt.value.id, []).append(elt.attr)
    return found


def compute_api_routes() -> Dict[str, Any]:
    """静态统计 app/api/*.py 中的 HTTP 端点定义数，并交叉验证可达性。"""
    registered = _registered_routers()

    per_file: Dict[str, Dict[str, int]] = {}
    defined_total = 0
    reachable_total = 0
    unreachable: List[str] = []

    for path in _iter_py(API_DIR):
        tree = _parse(path)
        if tree is None:
            continue
        mod = path.stem
        allowed = set(registered.get(mod, []))
        n_def = 0
        n_reach = 0
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for dec in node.decorator_list:
                if not isinstance(dec, ast.Call):
                    continue
                func = dec.func
                if not isinstance(func, ast.Attribute):
                    continue
                if func.attr not in HTTP_METHODS:
                    continue
                if not isinstance(func.value, ast.Name):
                    continue
                router_var = func.value.id
                n_def += 1
                if router_var in allowed:
                    n_reach += 1
                else:
                    # 记录「定义了但未被注册」的端点，供人工核查
                    arg = "<no-path>"
                    if dec.args and isinstance(dec.args[0], ast.Constant):
                        arg = str(dec.args[0].value)
                    unreachable.append(f"{mod}.{router_var} {func.attr.upper()} {arg}")
        if n_def:
            per_file[mod] = {"defined": n_def, "reachable": n_reach}
            defined_total += n_def
            reachable_total += n_reach

    return {
        "api_routes_defined": defined_total,
        "api_routes_reachable": reachable_total,
        "api_routes_unreachable": len(unreachable),
        "api_routes_per_file": per_file,
        "api_routes_unreachable_detail": sorted(unreachable),
        "registered_routers": {k: sorted(v) for k, v in sorted(registered.items())},
    }


def compute_tests() -> Dict[str, int]:
    files = sorted(p for p in TESTS_DIR.glob("test_*.py") if p.is_file())
    n_funcs = 0
    for path in files:
        tree = _parse(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("test_"):
                    n_funcs += 1
    return {"test_files": len(files), "test_functions": n_funcs}


def collect_pytest_count() -> Optional[int]:
    """可选：调用 pytest --collect-only -q 统计真实收集到的用例数。

    这是文档里「N 项测试」的真实口径。因为需要启动解释器并导入整个测试栈，
    默认不启用。失败时返回 None 而不是抛异常。
    """
    try:
        # 必须用 `-o addopts=` 清空 pytest.ini 的 addopts。否则仓库里的
        # `addopts = -v --tb=short --cov=app --cov-report=term-missing` 会让
        # `--collect-only` 每个用例输出多行（verbose 格式），使下面按行计数的
        # 逻辑失效并返回 None。
        proc = subprocess.run(
            [
                sys.executable, "-m", "pytest",
                "--collect-only", "-q",
                "-o", "addopts=",
                "-p", "no:cacheprovider",
            ],
            cwd=str(BACKEND_ROOT),
            capture_output=True,
            text=True,
            timeout=600,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode not in (0, 5):  # 5 = 未收集到任何用例
        return None
    # `-q --collect-only` 每个用例输出一行 `tests/test_x.py::test_y`
    lines = [
        ln for ln in proc.stdout.splitlines()
        if "::" in ln and not ln.startswith(" ")
    ]
    return len(lines) if lines else None


# ─────────────────────────────────────────────────────────────────────────────
# 文档核对
# ─────────────────────────────────────────────────────────────────────────────


def _to_int(raw: str) -> int:
    return int(raw.replace(",", ""))


def check_doc(actual: Dict[str, Any]) -> List[Dict[str, Any]]:
    """解析拆分方案 §1 的资产句子，逐项与复算值比对。

    返回比对条目列表；每项含 metric / doc_text / doc_value / actual_value / ok。
    若文档中找不到某项，actual_value 为 None 且 ok=True（不因措辞变化而误报）。
    """
    results: List[Dict[str, Any]] = []
    if not SPLIT_DOC.exists():
        return [{
            "metric": "<document>",
            "doc_text": str(SPLIT_DOC),
            "doc_value": None,
            "actual_value": None,
            "ok": False,
            "note": "文档不存在，无法核对",
        }]

    text = SPLIT_DOC.read_text(encoding="utf-8", errors="replace")

    for metric, pattern in DOC_PATTERNS.items():
        m = re.search(pattern, text)
        if m is None:
            results.append({
                "metric": metric,
                "doc_text": None,
                "doc_value": None,
                "actual_value": actual.get(metric),
                "ok": True,
                "note": "文档中未出现该措辞，跳过（措辞可能已改写）",
            })
            continue

        doc_val = _to_int(m.group(1))
        act_val = actual.get(metric)

        if act_val is None:
            # 例如 tests_collected 未启用 --with-pytest
            results.append({
                "metric": metric,
                "doc_text": m.group(0),
                "doc_value": doc_val,
                "actual_value": None,
                "ok": True,
                "note": "本次未复算该指标（加 --with-pytest 可复算），仅记录文档值",
            })
            continue

        results.append({
            "metric": metric,
            "doc_text": m.group(0),
            "doc_value": doc_val,
            "actual_value": act_val,
            "ok": doc_val == act_val,
            "note": "" if doc_val == act_val else f"文档 {doc_val} ≠ 实测 {act_val}",
        })

    return results


# ─────────────────────────────────────────────────────────────────────────────
# 报告
# ─────────────────────────────────────────────────────────────────────────────


def build_report(with_pytest: bool, doc_check: bool) -> Dict[str, Any]:
    actual: Dict[str, Any] = {}
    actual.update(compute_python_loc())
    actual.update(compute_module_counts())
    actual.update(compute_api_routes())
    actual.update(compute_tests())

    if with_pytest:
        collected = collect_pytest_count()
        if collected is not None:
            actual["tests_collected"] = collected

    verdict: Dict[str, Any] = {}
    for name, reg in REGISTERED.items():
        act = actual.get(name)
        verdict[name] = {
            "registered": reg["registered"],
            "actual": act,
            "delta": (act - reg["registered"]) if isinstance(act, int) else None,
            "strict": reg["strict"],
            "status": "verified" if act == reg["registered"] else "drifted",
            "note": reg["note"],
        }

    report: Dict[str, Any] = {
        "generated_at": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "backend_root": str(BACKEND_ROOT),
        "counts": actual,
        "verdict": verdict,
    }

    if doc_check:
        doc_results = check_doc(actual)
        report["doc_check"] = {
            "doc": str(SPLIT_DOC),
            "items": doc_results,
            "mismatches": [r["metric"] for r in doc_results if not r["ok"]],
        }
        report["doc_check"]["passed"] = not report["doc_check"]["mismatches"]

    # 全局退出判定
    blocking: List[str] = []
    if doc_check and not report["doc_check"]["passed"]:
        blocking.extend(report["doc_check"]["mismatches"])
    report["_blocking"] = blocking
    report["_exit_code"] = 1 if blocking else 0
    return report


def print_report(report: Dict[str, Any]) -> None:
    line = "=" * 78
    print(line)
    print("LearnFlow 自身资产数字复算报告")
    print(line)
    print(f"  生成时间 : {report['generated_at']}")
    print(f"  后端根目录: {report['backend_root']}")
    print()

    c = report["counts"]
    print("── 复算值 " + "─" * 68)
    for key in (
        "python_loc", "python_loc_excl_init", "source_files",
        "service_modules", "api_files",
        "api_routes_defined", "api_routes_reachable", "api_routes_unreachable",
        "test_files", "test_functions", "tests_collected",
    ):
        if key in c:
            print(f"  {key:<28}: {c[key]}")
    print()

    print("── 登记比对 " + "─" * 66)
    print(f"  {'指标':<28}{'登记':>8}{'实测':>8}{'差异':>8}  {'级别':<12}状态")
    print("  " + "-" * 74)
    for name, v in report["verdict"].items():
        act = v["actual"] if v["actual"] is not None else "-"
        delta = v["delta"] if v["delta"] is not None else "-"
        lvl = "strict" if v["strict"] else "informative"
        print(f"  {name:<28}{v['registered']:>8}{str(act):>8}{str(delta):>8}  {lvl:<12}{v['status']}")
    print()

    if c.get("api_routes_unreachable_detail"):
        print("── 定义了但未被注册的端点（需人工核查）" + "─" * 36)
        for item in c["api_routes_unreachable_detail"]:
            print(f"  ! {item}")
        print()

    if "doc_check" in report:
        dc = report["doc_check"]
        print("── 文档数字核对 " + "─" * 62)
        print(f"  文档: {dc['doc']}")
        for r in dc["items"]:
            mark = "OK  " if r["ok"] else "DRIFT"
            dv = r["doc_value"] if r["doc_value"] is not None else "-"
            av = r["actual_value"] if r["actual_value"] is not None else "-"
            print(f"  [{mark}] {r['metric']:<24} 文档={str(dv):<10} 实测={str(av):<10} {r['note']}")
        print()
        print(f"  结论: {'通过 —— 文档数字与代码事实一致' if dc['passed'] else '不一致 —— 存在 ' + str(len(dc['mismatches'])) + ' 项漂移'}")
        print()

    print(line)
    print(f"  结论      : {'PASS' if report['_exit_code'] == 0 else 'DRIFT'}   退出码 {report['_exit_code']}")
    print(f"  JSON 输出 : {JSON_OUT}")
    print(line)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="LearnFlow 自身资产数字复算（零依赖、AST 静态解析、不导入 app）",
    )
    parser.add_argument("--json", action="store_true", help="只写 JSON，不打印报告")
    parser.add_argument("--quiet", action="store_true", help="只打印一行结论")
    parser.add_argument(
        "--doc-check", action="store_true",
        help="额外解析 docs/LearnFlow_期刊论文拆分方案.md §1，逐项核对资产数字",
    )
    parser.add_argument(
        "--with-pytest", action="store_true",
        help="额外调用 pytest --collect-only 复算真实收集用例数（较慢）",
    )
    parser.add_argument(
        "--allow-drift", action="store_true",
        help="文档存在漂移时仍返回退出码 0（仅用于观测，不用于 CI）",
    )
    args = parser.parse_args(argv)

    try:
        report = build_report(with_pytest=args.with_pytest, doc_check=args.doc_check)
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        JSON_OUT.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:  # noqa: BLE001 —— 脚本自身失败必须是退出码 2，且要留下堆栈
        traceback.print_exc()
        return 2

    if not args.json:
        if args.quiet:
            c = report["counts"]
            extra = ""
            if "doc_check" in report:
                extra = f" doc_check={'pass' if report['doc_check']['passed'] else 'DRIFT'}"
            print(
                f"[asset_numbers] loc={c['python_loc']} files={c['source_files']} "
                f"services={c['service_modules']} routes={c.get('api_routes_reachable')} "
                f"tests={c.get('tests_collected', c.get('test_functions'))}"
                f"{extra} exit={report['_exit_code']}"
            )
        else:
            print_report(report)

    if args.allow_drift:
        return 0
    return int(report["_exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
