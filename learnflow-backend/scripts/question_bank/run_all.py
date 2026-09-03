#!/usr/bin/env python
"""LearnFlow 题库一键构建脚本

用法:
    python scripts/question_bank/run_all.py              # 全部: 生成 + 导入
    python scripts/question_bank/run_all.py --generate-only  # 仅生成 JSON
    python scripts/question_bank/run_all.py --import-only    # 仅导入已有 JSON
    python scripts/question_bank/run_all.py --dry-run        # 预演
    python scripts/question_bank/run_all.py --small          # 小批量测试 (各Topic 50题)
    python scripts/question_bank/run_all.py --medium         # 中等量 (各Topic 200题)
    python scripts/question_bank/run_all.py --large          # 大批量 (各Topic 500题)

生成规模预估:
    --small:  ~5,000 题
    --medium: ~20,000 题
    --large:  ~50,000 题
"""
import argparse
import os
import sys
import time
from pathlib import Path

# 确保项目路径正确
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def run_generators(math_count: int, chinese_count: int, english_count: int):
    """运行全部生成器"""
    print("=" * 60)
    print("🧮 阶段一：题目生成")
    print("=" * 60)
    print(f"   数学: {math_count} 题/知识点")
    print(f"   语文: {chinese_count} 题/知识点")
    print(f"   英语: {english_count} 题/知识点")
    print()

    total = 0

    # 数学
    print("📐 [1/3] 数学题库生成中...")
    t0 = time.time()
    from generators.math_generator import MathGenerator
    mg = MathGenerator()
    path = mg.generate_and_save(questions_per_grade_topic=math_count, filename="math_questions.json")
    with open(path, "r", encoding="utf-8") as f:
        import json
        count = len(json.load(f))
    total += count
    print(f"   ✅ 数学: {count} 题 ({time.time() - t0:.1f}s)")

    # 语文
    print("\n📝 [2/3] 语文题库生成中...")
    t0 = time.time()
    from generators.chinese_generator import ChineseGenerator
    cg = ChineseGenerator()
    path = cg.generate_and_save(questions_per_topic=chinese_count, filename="chinese_questions.json")
    with open(path, "r", encoding="utf-8") as f:
        import json
        count = len(json.load(f))
    total += count
    print(f"   ✅ 语文: {count} 题 ({time.time() - t0:.1f}s)")

    # 英语
    print("\n🔤 [3/3] 英语题库生成中...")
    t0 = time.time()
    from generators.english_generator import EnglishGenerator
    eg = EnglishGenerator()
    path = eg.generate_and_save(questions_per_topic=english_count, filename="english_questions.json")
    with open(path, "r", encoding="utf-8") as f:
        import json
        count = len(json.load(f))
    total += count
    print(f"   ✅ 英语: {count} 题 ({time.time() - t0:.1f}s)")

    print(f"\n📊 生成总计: {total} 题")
    return total


def run_import(dry_run: bool = False):
    """运行导入"""
    print("\n" + "=" * 60)
    print("📥 阶段二：数据库导入")
    print("=" * 60)
    import asyncio
    from importer import import_all, dry_run as dry_run_import
    if dry_run:
        asyncio.run(dry_run_import())
    else:
        asyncio.run(import_all())


def main():
    parser = argparse.ArgumentParser(description="LearnFlow 题库构建")
    parser.add_argument("--generate-only", action="store_true", help="仅生成 JSON")
    parser.add_argument("--import-only", action="store_true", help="仅导入已有 JSON")
    parser.add_argument("--dry-run", action="store_true", help="预演模式")
    parser.add_argument("--small", action="store_true", help="小批量 (~5000题)")
    parser.add_argument("--medium", action="store_true", help="中等量 (~20000题)")
    parser.add_argument("--large", action="store_true", help="大批量 (~50000题)")
    args = parser.parse_args()

    # 确定规模参数
    if args.large:
        math_c, cn_c, en_c = 500, 300, 300
        label = "LARGE (~50K题)"
    elif args.medium:
        math_c, cn_c, en_c = 200, 150, 150
        label = "MEDIUM (~20K题)"
    elif args.small:
        math_c, cn_c, en_c = 50, 40, 40
        label = "SMALL (~5K题)"
    else:
        math_c, cn_c, en_c = 200, 120, 120
        label = "DEFAULT (~20K题)"

    print(f"\n{'='*60}")
    print(f"  LearnFlow 题库构建工具")
    print(f"  模式: {label}")
    print(f"{'='*60}\n")

    if args.import_only:
        run_import(dry_run=args.dry_run)
    elif args.generate_only:
        run_generators(math_c, cn_c, en_c)
    else:
        # 全流程
        run_generators(math_c, cn_c, en_c)
        run_import(dry_run=args.dry_run)

    print("\n🎉 全部完成！")


if __name__ == "__main__":
    main()
