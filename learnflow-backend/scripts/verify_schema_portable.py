#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证 LearnFlow 核心资产「可移植建表脚本」是否真的能在其目标方言下执行。

这是论文可复现性交付物的一部分：不能只是「看起来对」，必须真跑。

- SQLite : 用标准库 sqlite3 在临时内存库上逐条执行 schema_core_assets.sqlite.sql，
           并查 sqlite_master 确认 6 张表都已建出。
- MySQL  : 优先用 sqlglot 按 mysql 方言解析每条语句做语法校验（不连服务器）；
           若环境中没有 sqlglot、也无可用 MySQL 服务器，则明确报告
           「MySQL 未实测」，绝不谎称已验证。

运行：
    python scripts/verify_schema_portable.py
退出码：SQLite 任一条失败或预期表缺失 -> 非 0；MySQL 仅作尽力校验，不影响退出码。
"""
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SQLITE_FILE = os.path.join(HERE, "schema_core_assets.sqlite.sql")
MYSQL_FILE = os.path.join(HERE, "schema_core_assets.mysql.sql")

EXPECTED_TABLES = [
    "user_xp_state",
    "skill_defs",
    "user_skill_tree",
    "experiments",
    "experiment_assignments",
    "experiment_results",
]


def read_sql(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def split_statements(sql):
    """按行切分、跳过 -- 注释、以行尾分号断句。

    本交付物 DDL 不含字符串内的分号，足够稳健；比 executescript 更能逐条汇报结果。
    """
    stmts = []
    buf = []
    for line in sql.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            # 仍保留注释行之外的逻辑：注释行不进入语句缓冲
            if buf:
                buf.append(line)
            continue
        buf.append(line)
        if stripped.endswith(";"):
            text = "\n".join(buf).strip()
            if text:
                stmts.append(text)
            buf = []
    tail = "\n".join(buf).strip()
    if tail:
        stmts.append(tail)
    return stmts


def verify_sqlite():
    print("=" * 70)
    print("SQLite 3 实测（sqlite3 内存库逐条执行）")
    print("=" * 70)
    sql = read_sql(SQLITE_FILE)
    stmts = split_statements(sql)
    print(f"脚本: {os.path.basename(SQLITE_FILE)}  语句数: {len(stmts)}\n")

    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON;")
    ok = 0
    fail = 0
    for i, stmt in enumerate(stmts, 1):
        preview = stmt.splitlines()[0].strip()
        try:
            conn.execute(stmt)
            ok += 1
            print(f"  [{i:02d}] OK    {preview[:60]}")
        except sqlite3.Error as e:
            fail += 1
            print(f"  [{i:02d}] FAIL  {preview[:60]}  -> {e}")
    conn.commit()

    # 查 sqlite_master 确认表已建出
    print()
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    built = {r[0] for r in cur.fetchall()}
    missing = [t for t in EXPECTED_TABLES if t not in built]
    for t in EXPECTED_TABLES:
        mark = "OK " if t in built else "MISSING"
        print(f"  表 {t:24s} ... {mark}")
    conn.close()

    print()
    if fail == 0 and not missing:
        print(f"SQLite 结果: 通过 — 全部 {ok} 条语句成功，{len(EXPECTED_TABLES)} 张表均已建出。")
        return True
    print(f"SQLite 结果: 失败 — {fail} 条错误，缺失表 {missing}。")
    return False


def verify_mysql():
    print()
    print("=" * 70)
    print("MySQL 8.0 校验")
    print("=" * 70)
    sql = read_sql(MYSQL_FILE)
    stmts = split_statements(sql)
    print(f"脚本: {os.path.basename(MYSQL_FILE)}  语句数: {len(stmts)}")

    try:
        import sqlglot  # type: ignore
    except ImportError:
        print()
        print("  [!] 环境中未安装 sqlglot，且无可用 MySQL 服务器。")
        print("  [!] MySQL 脚本【未实测】——仅做了人工核对，未做可靠的机器校验。")
        print("  [!] 论文附件不得声称 MySQL 已验证；请在具备 MySQL 8.0 或")
        print("      pip install sqlglot 的环境再补一次校验。")
        return False

    ok = 0
    fail = 0
    for i, stmt in enumerate(stmts, 1):
        preview = stmt.splitlines()[0].strip()
        try:
            sqlglot.parse(stmt, read="mysql")
            ok += 1
            print(f"  [{i:02d}] PARSE-OK  {preview[:60]}")
        except Exception as e:  # sqlglot 解析异常类型不固定
            fail += 1
            print(f"  [{i:02d}] PARSE-FAIL {preview[:60]}  -> {e}")
    print()
    if fail == 0:
        print(f"MySQL 结果: 经 sqlglot(mysql 方言) 语法解析全部通过（未连服务器执行）。")
    else:
        print(f"MySQL 结果: sqlglot 解析有 {fail} 条失败，需人工复核。")
    return fail == 0


def main():
    sqlite_ok = verify_sqlite()
    mysql_ok = verify_mysql()
    print()
    print("-" * 70)
    print(f"SQLite 实测通过: {sqlite_ok}")
    print(f"MySQL 实测/解析: {'通过(sqlglot)' if mysql_ok else '未实测/失败'}")
    print("-" * 70)
    # 退出码只由 SQLite 实测决定；MySQL 无服务器时按用户要求如实标注、不阻断。
    sys.exit(0 if sqlite_ok else 1)


if __name__ == "__main__":
    main()
