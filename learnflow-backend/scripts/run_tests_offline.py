#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""零第三方依赖的离线测试运行器（降级通道，不被 pytest 收集）。

为什么需要它
------------
`pytest.ini` 里 `testpaths = tests`、`python_files = test_*.py`，因此本文件放在
`scripts/` 下**不会被 pytest 收集**，不会改变全量 pytest 计数（现行 936 条口径，
见 `docs/` 各处与 `verify_counts.py`）。它的用途是：

* 在**没有 pytest / SQLAlchemy / FastAPI / numpy** 的受限环境（如离线审稿机、
  只装了标准库 Python 的机器）里，仍然能对**不依赖框架的部分**（本研究中特指
  难度公制层 `app.services.difficulty_fusion` 与 `app.services.optimal_difficulty`）
  跑一遍既有的 pytest 风格用例，确认重构没有回归；
* 对本机能跑的子集给出明确的 PASS/FAIL，对因缺依赖而跑不了的模块明确标注
  SKIP 及原因，而不是静默通过——避免"看起来全绿其实没跑"。

实现要点
--------
1. 用 `importlib.util.spec_from_file_location` **按文件路径直接加载**被测模块，
   并把它注册进 `sys.modules` 的**规范名** `app.services.<name>`；
   同时伪造空的 `app` / `app.services` 命名空间包。
   这是绕开 `app.services.__init__` 重依赖（sqlalchemy/fastapi）的关键：
   正常 `import app.services.X` 会先执行 `app/services/__init__.py` 从而炸掉，
   而本运行器让 `from app.services.X import Y` 直接命中已注册模块。
2. 提供最小 `pytest` 替身模块（`raises` / `approx` / `mark` / `fixture` / `skip`），
   满足测试文件顶部的 `import pytest` 与最常用的断言样式。
3. 逐个模块执行：导入失败 → SKIP(dependency)；对 `Test*` 类实例化后跑 `test_*`
   方法，缺 fixture 的方法会以 TypeError 报 ERROR 而不是被吞掉。

用法
----
    python scripts/run_tests_offline.py                    # 跑默认白名单
    python scripts/run_tests_offline.py --all              # 扫 tests/ 全量（缺依赖的会 SKIP）
    python scripts/run_tests_offline.py --module tests/test_difficulty_fusion.py
    python scripts/run_tests_offline.py --quiet

退出码：0 = 无任何 FAIL/ERROR；1 = 有 FAIL/ERROR（SKIP 不影响退出码，但会计数打印）。
"""
import argparse
import contextlib
import importlib.util
import os
import sys
import traceback
from pathlib import Path
from typing import List, Tuple

BACKEND = Path(__file__).resolve().parents[1]

# 需要按文件路径注入到 sys.modules 的模块：规范名 -> 相对 BACKEND 的路径
_STUB_MODULES = {
    "difficulty_fusion": "app/services/difficulty_fusion.py",
    "difficulty_m4": "app/services/difficulty_m4.py",
    "optimal_difficulty": "app/services/optimal_difficulty.py",
}

# 默认只跑已知在无第三方依赖下可运行的研究相关用例（不依赖 DB / HTTP / fixture）
_DEFAULT_MODULES = [
    "tests/test_difficulty_fusion.py",
    "tests/test_difficulty_m4.py",
]


# ═══════════════════════════════════════════════════════════════════════
# 最小 pytest 替身
# ═══════════════════════════════════════════════════════════════════════
class _RaisesContext:
    def __init__(self, expected, match=None):
        self.expected = expected
        self.match = match
        self.excinfo = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            raise AssertionError(f"DID NOT RAISE {self.expected}")
        if not issubclass(exc_type, self.expected):
            return False  # 异常类型不符 → 继续向外抛，等价于测试失败
        if self.match is not None and self.match not in str(exc):
            raise AssertionError(f"异常消息不匹配: 期望含 {self.match!r}, 实得 {exc!r}")
        self.excinfo = exc
        return True


class _Approx:
    def __init__(self, expected, rel=1e-6, abs=1e-9):  # noqa: A002 - 与 pytest 同名
        self.expected = expected
        self.rel = rel if rel is not None else 1e-6
        self.abs = abs if abs is not None else 1e-9

    def __eq__(self, actual):
        if isinstance(self.expected, (list, tuple)):
            if len(actual) != len(self.expected):
                return False
            return all(_Approx(e, self.rel, self.abs) == a
                       for e, a in zip(self.expected, actual))
        return abs(actual - self.expected) <= max(self.abs, self.rel * abs(self.expected))

    def __repr__(self):
        return f"approx({self.expected!r})"


class _Mark:
    def __getattr__(self, _name):
        def deco(*_a, **_kw):
            if len(_a) == 1 and callable(_a[0]) and not _kw:
                return _a[0]

            def inner(fn):
                return fn
            return inner
        return deco


class _PytestShim:
    """只实现本项目测试用到的最小子集。用到不支持的能力会显式报错，绝不静默通过。"""
    mark = _Mark()
    raises = staticmethod(lambda exc, match=None: _RaisesContext(exc, match))
    approx = staticmethod(lambda x, rel=1e-6, abs=1e-9: _Approx(x, rel, abs))
    fixture = staticmethod(lambda *a, **k: (a[0] if a and callable(a[0]) and not k
                                            else (lambda f: f)))
    skip = staticmethod(lambda reason="": None)
    fail = staticmethod(lambda msg="": (_ for _ in ()).throw(AssertionError(msg)))

    @staticmethod
    def parametrize(argnames, argvalues, **_kw):
        def deco(fn):
            fn._parametrize = (argnames, list(argvalues))
            return fn
        return deco

    @staticmethod
    def main(*_a, **_kw):
        raise RuntimeError("run_tests_offline: 请勿在本运行器内调用 pytest.main()")


class Skipped(Exception):
    """测试主动跳过。"""


_PytestShim.skip_exception = Skipped
_PytestShim.Skipped = Skipped


# ═══════════════════════════════════════════════════════════════════════
# sys.modules 注入（绕开 app.services.__init__ 的重依赖）
# ═══════════════════════════════════════════════════════════════════════
def _install_namespace_packages() -> None:
    """注册空的 ``app`` 与 ``app.services`` 包对象，让规范导入名可用。"""
    import types

    app_pkg = sys.modules.get("app")
    if app_pkg is None:
        app_pkg = types.ModuleType("app")
        app_pkg.__path__ = [str(BACKEND / "app")]
        sys.modules["app"] = app_pkg
    svc = sys.modules.get("app.services")
    if svc is None:
        svc = types.ModuleType("app.services")
        svc.__path__ = [str(BACKEND / "app" / "services")]
        setattr(app_pkg, "services", svc)
        sys.modules["app.services"] = svc


def install_stub_modules() -> List[str]:
    """把 `_STUB_MODULES` 里的模块按文件路径加载并注册到规范名。返回成功注入的名字列表。"""
    _install_namespace_packages()
    loaded = []
    for name, rel in _STUB_MODULES.items():
        target = BACKEND / rel
        if not target.exists():
            continue
        spec = importlib.util.spec_from_file_location(f"app.services.{name}", target)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[f"app.services.{name}"] = mod
        setattr(sys.modules["app.services"], name, mod)
        spec.loader.exec_module(mod)
        loaded.append(f"app.services.{name}")
    return loaded


# ═══════════════════════════════════════════════════════════════════════
# 执行器
# ═══════════════════════════════════════════════════════════════════════
class Result:
    def __init__(self) -> None:
        self.passed: List[str] = []
        self.failed: List[Tuple[str, str]] = []
        self.errors: List[Tuple[str, str]] = []
        self.skipped: List[Tuple[str, str]] = []

    @property
    def ok(self) -> bool:
        return not self.failed and not self.errors


def _run_callable(fn, res: Result, label: str) -> None:
    try:
        fn()
    except AssertionError as exc:
        res.failed.append((label, f"AssertionError: {exc}"))
    except TypeError as exc:
        # 典型原因：该用例依赖 pytest fixture，本运行器无法提供
        res.errors.append((label, f"{type(exc).__name__}: {exc}"))
    except Exception as exc:  # noqa: BLE001 - 需要如实收集任何失败
        tb = traceback.format_exc(limit=6)
        res.errors.append((label, f"{type(exc).__name__}: {exc}\n{tb}"))
    else:
        res.passed.append(label)


def _expand_parametrize(fn, cls_instance, res: Result, base: str) -> None:
    argnames, values = fn._parametrize
    names = [a.strip() for a in argnames.split(",")] if isinstance(argnames, str) else list(argnames)
    for idx, val in enumerate(values):
        kwargs = dict(zip(names, val)) if len(names) > 1 else {names[0]: val}
        label = f"{base}[{idx}]"

        def call(_kw=kwargs):
            return fn(**_kw)
        _run_callable(call, res, label)


def _members_in_definition_order(obj) -> List[str]:
    """按**定义顺序**取成员名（pytest/unittest 也是定义顺序，不能用 dir() 的字母序）。

    顺序敏感的反例：`tests/test_team_competition.py` 里 `test_cannot_join_full_team`
    会把 u2…u12 注册进队伍，若按字母序它排在 `test_join_team` 之前，后者就会因为
    "u2 已加入过"而假失败。
    """
    seen, names = set(), []
    for klass in getattr(obj, "__mro__", [obj]):
        for name in vars(klass):
            if name not in seen:
                seen.add(name)
                names.append(name)
    return names


def run_module(path: Path, res: Result, verbose: bool = True) -> None:
    label = path.relative_to(BACKEND).as_posix()
    try:
        spec = importlib.util.spec_from_file_location(
            f"_offline_{path.stem}", path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
    except Skipped as exc:
        res.skipped.append((label, f"模块级跳过: {exc}"))
        return
    except Exception as exc:  # noqa: BLE001
        deps = {"sqlalchemy", "fastapi", "numpy", "jose", "passlib", "pydantic",
                "httpx", "redis", "pandas", "matplotlib", "scipy", "sklearn"}
        why = f"{type(exc).__name__}: {exc}"
        if any(d in why for d in deps):
            res.skipped.append((label, f"缺第三方依赖 → {why}"))
        else:
            res.errors.append((label, f"导入失败 → {why}"))
        return

    before = len(res.passed) + len(res.failed) + len(res.errors) + len(res.skipped)

    # 1) 模块级 test_* 函数
    for fname in _members_in_definition_order(mod):
        if not fname.startswith("test_"):
            continue
        fn = getattr(mod, fname)
        if not callable(fn):
            continue
        full = f"{label}::{fname}"
        if hasattr(fn, "_parametrize"):
            _expand_parametrize(fn, None, res, full)
        else:
            _run_callable(fn, res, full)

    # 2) Test* 类
    for cname in _members_in_definition_order(mod):
        if not cname.startswith("Test"):
            continue
        cls = getattr(mod, cname)
        if not isinstance(cls, type):
            continue
        inst = cls()
        for mname in _members_in_definition_order(cls):
            if not mname.startswith("test_"):
                continue
            fn = getattr(inst, mname)
            if not callable(fn):
                continue
            full = f"{label}::{cname}::{mname}"
            if hasattr(fn, "_parametrize"):
                _expand_parametrize(fn, inst, res, full)
            else:
                _run_callable(fn, res, full)

    touched = (len(res.passed) + len(res.failed) + len(res.errors)
               + len(res.skipped)) - before
    if verbose:
        if touched == 0:
            print(f"  ⏭  {label}: 无可运行用例")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="零第三方依赖的离线测试运行器")
    ap.add_argument("--module", action="append", default=[],
                    help="指定测试模块（相对 learnflow-backend 的路径），可重复")
    ap.add_argument("--all", action="store_true", help="扫描 tests/ 下全部 test_*.py")
    ap.add_argument("--quiet", action="store_true", help="精简输出")
    args = ap.parse_args(argv)

    print("=" * 78)
    print("LearnFlow · 离线测试运行器（零第三方依赖降级通道）")
    print(f"  Python {sys.version.split()[0]} | 后端根 {BACKEND}")
    print("=" * 78)

    injected = install_stub_modules()
    sys.modules["pytest"] = _PytestShim()  # type: ignore[assignment]
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))

    if not args.quiet:
        print(f"已注入 {len(injected)} 个模块到 sys.modules：")
        for name in injected:
            print(f"    {name}")
        print("-" * 78)

    if args.module:
        targets = [(BACKEND / m) for m in args.module]
    elif args.all:
        targets = sorted((BACKEND / "tests").glob("test_*.py"))
    else:
        targets = [BACKEND / m for m in _DEFAULT_MODULES]

    res = Result()
    for path in targets:
        if not path.exists():
            res.errors.append((str(path), "文件不存在"))
            continue
        run_module(path, res, verbose=not args.quiet)

    npass, nfail = len(res.passed), len(res.failed)
    nerr, nskip = len(res.errors), len(res.skipped)

    if not args.quiet:
        if nfail or nerr:
            print("-" * 78)
            print("失败明细：")
            for name, why in res.failed + res.errors:
                print(f"  ✗ {name}\n      {why}")
        if nskip:
            print("-" * 78)
            print("跳过明细（**未执行**，不算通过）：")
            for name, why in res.skipped:
                print(f"  ⏭ {name}\n      {why}")

    print("=" * 78)
    verdict = "✅ PASS" if res.ok else "❌ FAIL"
    print(f"{verdict}：可运行用例 {npass} 通过 / {nfail} 失败 / {nerr} 错误 / {nskip} 跳过")
    if not res.ok:
        print("  ↑ 存在 FAIL 或 ERROR，请以完整 pytest 环境复核。")
    print("=" * 78)
    return 0 if res.ok else 1


if __name__ == "__main__":
    with contextlib.suppress(BrokenPipeError):
        sys.exit(main())
