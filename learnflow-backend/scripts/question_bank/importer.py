"""题库批量导入器 — 将 JSON 题目数据导入 LearnFlow 数据库"""
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# 添加项目路径
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import Base
from app.models.task import Task
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker


def _get_importer_session():
    """创建导入专用数据库会话（自动SQLite降级）"""
    from app.core.config import settings
    db_url = settings.DATABASE_URL

    # 尝试 MySQL 连接，失败则降级 SQLite（同步测试避免嵌套事件循环）
    if "mysql" in db_url:
        try:
            import pymysql
            import urllib.parse
            # 解析 DATABASE_URL: mysql+aiomysql://user:pass@host:port/db
            url_parsed = urllib.parse.urlparse(db_url.replace("mysql+aiomysql", "mysql+pymysql"))
            conn = pymysql.connect(
                host=url_parsed.hostname,
                port=url_parsed.port or 3306,
                user=url_parsed.username,
                password=url_parsed.password,
                database=url_parsed.path.lstrip("/"),
                connect_timeout=3,
            )
            conn.close()
            print("✅ MySQL 连接成功")
        except Exception:
            print("⚠️ MySQL 不可用，自动降级到 SQLite")
            db_url = f"sqlite+aiosqlite:///{BACKEND_ROOT / 'learnflow.db'}"

    engine = create_async_engine(db_url, echo=False)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False), engine

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# 难度映射：生成器用年级作为难度参考，这里做规范化
GRADE_DIFFICULTY_MAP = {
    1: (1, 3), 2: (2, 4), 3: (3, 5),
    4: (4, 6), 5: (5, 8), 6: (6, 9),
}


def normalize_difficulty(difficulty: int) -> int:
    """确保难度在 1-10 范围内"""
    return max(1, min(10, difficulty))


def transform_question(data: dict, index: int = 0) -> Task:
    """将 JSON 题数据转为 Task ORM 对象"""
    topic = data.get("topic", "未分类")
    difficulty = normalize_difficulty(data.get("difficulty", 5))
    content = data.get("content", "").strip()
    correct_answer = str(data.get("correct_answer", "")).strip()
    explanation = data.get("explanation", "").strip()
    hint_levels = data.get("hint_levels", None)
    time_estimate = data.get("time_estimate", 120)
    source = data.get("source", "imported")
    content_type = data.get("content_type", "text")

    # 确保必要字段不为空
    if not content:
        content = f"[空题目 #{index}]"
    if not correct_answer:
        correct_answer = "[待补充]"

    task = Task(
        id=str(uuid.uuid4()),
        content=content,
        content_type=content_type,
        topic=topic,
        difficulty=difficulty,
        correct_answer=correct_answer,
        explanation=explanation if explanation else None,
        hint_levels=hint_levels if isinstance(hint_levels, list) else None,
        time_estimate=time_estimate,
        source=source,
        is_approved=True,
    )
    return task


async def count_existing(session_factory) -> int:
    """统计当前数据库中的题目数"""
    async with session_factory() as db:
        result = await db.execute(select(func.count(Task.id)))
        return result.scalar() or 0


async def import_json_file(filepath: str, session_factory, batch_size: int = 500) -> dict:
    """导入单个 JSON 文件"""
    stats = {"file": os.path.basename(filepath), "total": 0, "imported": 0, "failed": 0, "errors": []}

    if not os.path.exists(filepath):
        stats["errors"].append(f"文件不存在: {filepath}")
        return stats

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        stats["errors"].append(f"JSON解析失败: {e}")
        return stats
    except Exception as e:
        stats["errors"].append(f"读取文件失败: {e}")
        return stats

    if not isinstance(data, list):
        stats["errors"].append("数据格式不是列表")
        return stats

    stats["total"] = len(data)
    tasks_to_insert = []

    for i, item in enumerate(data):
        try:
            task = transform_question(item, i)
            tasks_to_insert.append(task)
        except Exception as e:
            stats["failed"] += 1
            stats["errors"].append(f"第{i}条转换失败: {e}")

    # 分批写入数据库
    for i in range(0, len(tasks_to_insert), batch_size):
        batch = tasks_to_insert[i:i + batch_size]
        try:
            async with session_factory() as db:
                db.add_all(batch)
                await db.commit()
                stats["imported"] += len(batch)
        except Exception as e:
            stats["failed"] += len(batch)
            stats["errors"].append(f"批次 {i//batch_size} 写入失败: {e}")
            # 打印第一条错误详情
            if len(batch) > 0:
                print(f"    示例数据: {batch[0].content[:50]}...")

    return stats


async def import_all(skip_existing_check: bool = False):
    """导入 data/ 目录下所有 JSON 文件"""
    print("=" * 60)
    print("📦 LearnFlow 题库批量导入器")
    print("=" * 60)

    # 创建数据库会话（带 MySQL→SQLite 自动降级）
    session_factory, engine = _get_importer_session()

    # 确保数据库表已创建
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 统计现有题目
    existing = await count_existing(session_factory)
    print(f"\n📊 当前数据库题目数: {existing}")

    # 查找所有 JSON 文件
    json_files = sorted(Path(DATA_DIR).glob("*.json"))
    if not json_files:
        print(f"\n⚠️  {DATA_DIR} 目录下没有找到 JSON 文件")
        print("   请先运行生成器: python scripts/question_bank/generators/math_generator.py")
        return

    print(f"\n📁 找到 {len(json_files)} 个题库文件:")
    for f in json_files:
        size_kb = os.path.getsize(f) / 1024
        print(f"   {f.name} ({size_kb:.1f} KB)")

    # 逐个导入
    print("\n🚀 开始导入...\n")
    total_imported = 0
    total_failed = 0

    for json_file in json_files:
        filename = json_file.name
        print(f"  📥 导入 {filename}...", end=" ", flush=True)
        stats = await import_json_file(str(json_file), session_factory)
        total_imported += stats["imported"]
        total_failed += stats["failed"]
        print(f"✅ {stats['imported']}/{stats['total']} 导入成功"
              + (f" ❌ {stats['failed']} 失败" if stats['failed'] > 0 else ""))

        if stats["errors"]:
            for err in stats["errors"][:3]:
                print(f"     ⚠ {err}")
            if len(stats["errors"]) > 3:
                print(f"     ... 还有 {len(stats['errors']) - 3} 个错误")

    # 最终统计
    final_count = await count_existing(session_factory)
    print(f"\n{'=' * 60}")
    print(f"📊 导入完成!")
    print(f"   导入成功: {total_imported} 题")
    print(f"   导入失败: {total_failed} 题")
    print(f"   数据库总题数: {final_count} 题 (新增 {final_count - existing} 题)")
    print(f"{'=' * 60}")

    # 按知识点统计
    async with session_factory() as db:
        from sqlalchemy import text
        result = await db.execute(
            text("SELECT topic, COUNT(*) as cnt FROM tasks GROUP BY topic ORDER BY cnt DESC LIMIT 20")
        )
        print(f"\n📈 Top 20 知识点分布:")
        for row in result:
            print(f"   {row[0]}: {row[1]} 题")


async def dry_run():
    """预演模式：只统计不导入"""
    print("🔍 预演模式 — 仅统计，不实际导入\n")
    json_files = sorted(Path(DATA_DIR).glob("*.json"))
    total = 0
    for f in json_files:
        with open(f, "r", encoding="utf-8") as fp:
            data = json.load(fp)
            count = len(data) if isinstance(data, list) else 0
            print(f"   {f.name}: {count} 题")
            total += count
    print(f"\n   📊 总计: {total} 题待导入")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="LearnFlow 题库导入器")
    parser.add_argument("--dry-run", action="store_true", help="预演模式，仅统计")
    parser.add_argument("--force", action="store_true", help="跳过存量检查")
    args = parser.parse_args()

    if args.dry_run:
        asyncio.run(dry_run())
    else:
        asyncio.run(import_all(skip_existing_check=args.force))


if __name__ == "__main__":
    main()
