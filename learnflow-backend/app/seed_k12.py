"""K12 示例数据种子（幂等）

插入：
- 学科：数学/语文/英语（含学科色）
- 年级：G1 / G7 / G10（含学段 band）
- 课标知识点：上述年级各若干（含前备依赖 prerequisites）
- 少量示例 Task 关联到课标节点
- 一个示例班级（G7，绑定演示教师），便于教师端点演示

运行：python app/seed_k12.py
幂等：按唯一键 (code / subject+grade+title / node+content) 跳过已存在数据。
"""
import asyncio
import os

from app.core.database import AsyncSessionLocal, init_db
from app.core.security import hash_password
from sqlalchemy import select

from app.models.user import User, UserRole
from app.models.curriculum import Subject, GradeLevel, CurriculumNode, Class, GradeBand
from app.models.task import Task


SUBJECTS = [
    {"code": "math", "name": "数学", "color": "#4F5BD5"},
    {"code": "zh", "name": "语文", "color": "#E0533D"},
    {"code": "en", "name": "英语", "color": "#3FA66A"},
]

GRADES = [
    {"code": "G1", "label": "一年级", "band": GradeBand.PRIMARY.value},
    {"code": "G7", "label": "七年级", "band": GradeBand.JUNIOR.value},
    {"code": "G10", "label": "高一", "band": GradeBand.SENIOR.value},
]

# 每个学科在各年级的知识点（同一学科内按列表顺序，前者是后者的前备依赖）
CURRICULUM = {
    "math": {
        "G1": ["数数 1-20", "10以内加减法", "20以内加减法", "认识图形"],
        "G7": ["有理数", "一元一次方程", "平面几何基础", "二元一次方程组"],
        "G10": ["函数概念", "二次函数", "三角函数", "导数初步"],
    },
    "zh": {
        "G1": ["拼音与识字", "看图写话", "朗读与背诵"],
        "G7": ["记叙文阅读", "文言文入门", "记叙文写作"],
        "G10": ["议论文阅读", "古典诗词鉴赏", "议论文写作"],
    },
    "en": {
        "G1": ["字母与发音", "基础词汇", "简单问候语"],
        "G7": ["时态基础", "阅读理解", "短文写作"],
        "G10": ["长难句分析", "学术写作", "听力理解"],
    },
}

# 少量示例题（关联到知识点标题）：content, correct_answer, explanation, difficulty
SAMPLE_TASKS = {
    "一元一次方程": ("解方程：2x + 5 = 13", "4", "移项：2x = 8，x = 4", 5),
    "20以内加减法": ("13 - 7 = ?", "6", "借位减法：13 - 7 = 6", 3),
    "有理数": ("计算：(-3) + 5 = ?", "2", "异号相加取绝对值较大符号：5-3=2", 4),
    "函数概念": ("函数 f(x)=2x+1，求 f(3)", "7", "代入：2×3+1=7", 6),
    "拼音与识字": ("‘苹果’的拼音是？", "píng guǒ", "píng guǒ", 2),
    "记叙文阅读": ("记叙文的六要素不包括以下哪项？", "修辞手法", "六要素：时间地点人物起因经过结果", 6),
    "字母与发音": ("字母 A 的发音是？", "/eɪ/", "A 发 /eɪ/", 2),
    "时态基础": ("I ___ to school yesterday. (go)", "went", "过去式：go→went", 5),
}


async def seed():
    await init_db()
    async with AsyncSessionLocal() as db:
        # ── 学科 ──
        subj_index = {}
        for s in SUBJECTS:
            existing = (await db.execute(select(Subject).where(Subject.code == s["code"]))).scalar_one_or_none()
            if existing is None:
                existing = Subject(code=s["code"], name=s["name"], color=s["color"])
                db.add(existing)
                await db.flush()
                print(f"✅ 学科: {s['name']} ({s['code']})")
            subj_index[s["code"]] = existing

        # ── 年级 ──
        grade_index = {}
        for g in GRADES:
            existing = (await db.execute(select(GradeLevel).where(GradeLevel.code == g["code"]))).scalar_one_or_none()
            if existing is None:
                existing = GradeLevel(code=g["code"], label=g["label"], band=g["band"])
                db.add(existing)
                await db.flush()
                print(f"✅ 年级: {g['label']} ({g['code']}, {g['band']})")
            grade_index[g["code"]] = existing

        # ── 课标知识点（含前备依赖） ──
        node_index = {}  # (subject_code, grade_code, title) -> node
        for subj_code, by_grade in CURRICULUM.items():
            for grade_code, titles in by_grade.items():
                subj = subj_index[subj_code]
                grade = grade_index[grade_code]
                prev_node_id = None
                for idx, title in enumerate(titles):
                    key = (subj_code, grade_code, title)
                    existing = (await db.execute(
                        select(CurriculumNode).where(
                            CurriculumNode.subject_id == subj.id,
                            CurriculumNode.grade_id == grade.id,
                            CurriculumNode.title == title,
                        )
                    )).scalar_one_or_none()
                    if existing is None:
                        prereqs = [prev_node_id] if prev_node_id else []
                        existing = CurriculumNode(
                            subject_id=subj.id,
                            grade_id=grade.id,
                            chapter=f"第{idx + 1}章",
                            title=title,
                            prerequisites=prereqs,
                        )
                        db.add(existing)
                        await db.flush()
                        print(f"✅ 知识点: [{grade_code}][{subj_code}] {title}")
                    node_index[key] = existing
                    prev_node_id = str(existing.id)

        # ── 示例题关联到节点 ──
        for title, (content, answer, explanation, diff) in SAMPLE_TASKS.items():
            # 找到同名知识点（取第一个匹配）
            node = next((n for (sc, gc, t), n in node_index.items() if t == title), None)
            if node is None:
                continue
            existing = (await db.execute(
                select(Task).where(
                    Task.curriculum_node_id == node.id,
                    Task.content == content,
                )
            )).scalar_one_or_none()
            if existing is None:
                task = Task(
                    title=title,
                    content=content,
                    content_type="text",
                    topic=title,
                    difficulty=diff,
                    correct_answer=answer,
                    explanation=explanation,
                    source="system",
                    is_approved=True,
                    curriculum_node_id=node.id,
                )
                db.add(task)
                await db.flush()
                print(f"✅ 示例题: {title} (难度 {diff})")

        # ── 示例班级（G7，绑定演示教师） ──
        teacher = (await db.execute(
            select(User).where(User.email == "teacher@learnflow.com")
        )).scalar_one_or_none()
        grade7 = grade_index["G7"]
        existing_class = (await db.execute(
            select(Class).where(Class.name == "示例七班")
        )).scalar_one_or_none()
        if existing_class is None and teacher is not None:
            klass = Class(name="示例七班", grade_id=grade7.id, teacher_id=teacher.id)
            db.add(klass)
            await db.flush()
            print("✅ 示例班级: 示例七班 (G7)")

        await db.commit()
    print("🎉 K12 种子数据完成（幂等）")


if __name__ == "__main__":
    asyncio.run(seed())
