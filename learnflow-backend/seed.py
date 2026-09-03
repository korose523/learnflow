"""数据库种子数据：演示账号 + 默认反馈文案 + 示例题目"""
import argparse
import asyncio
import os
import secrets
from app.core.database import AsyncSessionLocal, init_db
from app.models.user import User, UserRole
from app.models.pet import PetProfile, PetBreed
from app.models.task import Task
from app.models.consent import FeedbackScript
from app.core.security import hash_password
from sqlalchemy import select, func, delete


# 种子用户密码：优先从环境变量读取，否则生成随机密码
SEED_ADMIN_PW = os.getenv("SEED_ADMIN_PASSWORD", secrets.token_urlsafe(12))
SEED_TEACHER_PW = os.getenv("SEED_TEACHER_PASSWORD", secrets.token_urlsafe(12))
SEED_STUDENT_PW = os.getenv("SEED_STUDENT_PASSWORD", secrets.token_urlsafe(12))
SEED_PARENT_PW = os.getenv("SEED_PARENT_PASSWORD", secrets.token_urlsafe(12))

PW_SOURCE = "环境变量" if any(
    os.getenv(k) for k in [
        "SEED_ADMIN_PASSWORD", "SEED_TEACHER_PASSWORD",
        "SEED_STUDENT_PASSWORD", "SEED_PARENT_PASSWORD",
    ]
) else "随机生成（请记录或使用环境变量重新设置）"

SAMPLE_TASKS = [
    {"topic": "一元一次方程", "difficulty": 3, "content": "解方程：2x + 5 = 13", "correct_answer": "4", "explanation": "移项：2x = 13 - 5 = 8，两边除以2：x = 4"},
    {"topic": "一元一次方程", "difficulty": 5, "content": "解方程：3(x - 2) = 2x + 1", "correct_answer": "7", "explanation": "展开：3x - 6 = 2x + 1，移项：x = 7"},
    {"topic": "一元一次方程", "difficulty": 7, "content": "小明买了3支笔和2个本子共花了19元，已知每支笔3元，求每个本子多少元？", "correct_answer": "5", "explanation": "设本子x元：3×3 + 2x = 19，9 + 2x = 19，x = 5"},
    {"topic": "分数运算", "difficulty": 4, "content": "计算：1/2 + 1/3 = ?", "correct_answer": "5/6", "explanation": "通分：3/6 + 2/6 = 5/6"},
    {"topic": "分数运算", "difficulty": 6, "content": "计算：(2/3) ÷ (4/5) = ?", "correct_answer": "5/6", "explanation": "除以分数等于乘以倒数：2/3 × 5/4 = 10/12 = 5/6"},
    {"topic": "几何", "difficulty": 4, "content": "一个三角形的三个角分别是30°、60°和多少度？", "correct_answer": "90", "explanation": "三角形内角和为180°，180 - 30 - 60 = 90°"},
    {"topic": "几何", "difficulty": 6, "content": "一个圆的半径是5cm，它的面积是多少平方厘米？（π取3.14）", "correct_answer": "78.5", "explanation": "面积 = πr² = 3.14 × 25 = 78.5 cm²"},
    {"topic": "百分比", "difficulty": 5, "content": "商店打八折出售一件衣服，打折后价格为160元，原价是多少？", "correct_answer": "200", "explanation": "设原价x：0.8x = 160，x = 200"},
]

DEFAULT_SCRIPTS = [
    {"category": "correct", "text": "✨ 思路很清晰！你正在强化{concept}的神经回路。"},
    {"category": "correct", "text": "🎯 答对了！这证明你对{concept}的理解又深了一层。"},
    {"category": "correct", "text": "💡 很好！这正是{concept}的核心思维。"},
    {"category": "incorrect", "text": "🔍 不错的尝试！差一步，你的大脑现在正在学习如何避免这个错误。"},
    {"category": "incorrect", "text": "💪 这正是学习发生的时刻——从错误中成长。来看一下关键步骤？"},
    {"category": "incorrect", "text": "🌱 错误是最诚实的老师。你的大脑正在重新组织关于{concept}的知识。"},
    {"category": "encouragement", "text": "你已经面对了多个困难——这在锻炼你的坚持力。"},
    {"category": "encouragement", "text": "每一次错误都在帮你找到进步的方向。"},
    {"category": "flow", "text": "🎵 你现在正在心流通道中——难度刚好，状态正好。"},
    {"category": "flow", "text": "⚡ 完美的挑战节奏！大脑在高速学习。"},
    {"category": "anticipation", "text": "下一题会让你接近{concept}的新理解水平。准备好了吗？"},
    {"category": "anticipation", "text": "你已经做过类似的题目并成功了，这次也能。"},
    {"category": "rest", "text": "感觉累了很正常。你的大脑现在在做最深层的整合工作。"},
    {"category": "rest", "text": "短暂的放松能帮助你更好地吸收知识。试试30秒深呼吸？"},
    {"category": "identity", "text": "你正在变成一个更全面的学习者。"},
    {"category": "identity", "text": "每一个小挑战都让你更强——这就是自我实现的样子。"},
    {"category": "relaxation", "text": "花30秒，跟着呼吸放松。深呼吸，有节奏地吸气…呼气…"},
    {"category": "relaxation", "text": "闭上眼睛，感受呼吸。吸气时想象知识流入，呼气时放下紧张。"},
]


async def seed(force: bool = False):
    await init_db()

    async with AsyncSessionLocal() as db:
        # 检查是否已有用户
        user_count = (await db.execute(select(func.count(User.id)))).scalar() or 0
        if user_count > 0 and not force:
            print(f"数据库已有 {user_count} 个用户，跳过账号种子。")
            print("如需重新创建，请添加 --force 参数。")
        else:
            if force and user_count > 0:
                print(f"⚠️ --force 已启用，删除 {user_count} 个旧用户...")
                # 先删除依赖数据（宠物、尝试、复习等）
                from app.models.consent import ConsentRecord, Alert
                from app.models.task import Attempt, SpacedReview, StudentSkillProfile
                await db.execute(delete(Attempt))
                await db.execute(delete(SpacedReview))
                await db.execute(delete(StudentSkillProfile))
                await db.execute(delete(PetProfile))
                await db.execute(delete(ConsentRecord))
                await db.execute(delete(Alert))
                await db.execute(delete(User))
                await db.flush()

            # 创建管理员
            admin = User(
                email="admin@learnflow.com",
                hashed_password=hash_password(SEED_ADMIN_PW),
                name="系统管理员",
                role=UserRole.ADMIN,
            )
            db.add(admin)

            # 创建教师
            teacher = User(
                email="teacher@learnflow.com",
                hashed_password=hash_password(SEED_TEACHER_PW),
                name="张老师",
                role=UserRole.TEACHER,
            )
            db.add(teacher)

            # 创建学生
            student = User(
                email="student@learnflow.com",
                hashed_password=hash_password(SEED_STUDENT_PW),
                name="小明",
                role=UserRole.STUDENT,
                grade="五年级",
            )
            db.add(student)

            # 创建家长（通过关联绑定）
            parent = User(
                email="parent@learnflow.com",
                hashed_password=hash_password(SEED_PARENT_PW),
                name="小明爸爸",
                role=UserRole.PARENT,
            )
            db.add(parent)

            await db.flush()

            # 绑定亲子关系
            student.parent_id = parent.id

            # 创建宠物
            pet = PetProfile(
                user_id=student.id,
                name="小豆",
                breed=PetBreed.CAT,
                level=1,
                understanding=50.0,
                persistence=50.0,
                creativity=50.0,
                collaboration=50.0,
            )
            db.add(pet)

            await db.commit()
            print("演示账号创建完成！")
            print(f"  管理员: admin@learnflow.com")
            print(f"  教师:   teacher@learnflow.com")
            print(f"  学生:   student@learnflow.com")
            print(f"  家长:   parent@learnflow.com")
            print(f"  密码来源: {PW_SOURCE}")

        # 补充示例题目（仅当不存在时）
        existing_task_count = (await db.execute(select(func.count(Task.id)))).scalar() or 0
        if existing_task_count == 0:
            for t in SAMPLE_TASKS:
                task = Task(
                    topic=t["topic"],
                    difficulty=t["difficulty"],
                    content=t["content"],
                    correct_answer=t["correct_answer"],
                    explanation=t["explanation"],
                    is_approved=True,
                )
                db.add(task)
            await db.commit()
            print(f"示例题目创建完成：{len(SAMPLE_TASKS)} 道")
        else:
            print(f"已有 {existing_task_count} 道题目，跳过示例题目")

        # 补充默认反馈文案（仅当不存在时）
        existing_script_count = (await db.execute(select(func.count(FeedbackScript.id)))).scalar() or 0
        if existing_script_count == 0:
            for s in DEFAULT_SCRIPTS:
                script = FeedbackScript(
                    category=s["category"],
                    text=s["text"],
                    review_status="approved",
                )
                db.add(script)
            await db.commit()
            print(f"默认反馈文案创建完成：{len(DEFAULT_SCRIPTS)} 条")
        else:
            print(f"已有 {existing_script_count} 条反馈文案，跳过")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LearnFlow 数据库种子脚本")
    parser.add_argument("--force", action="store_true", help="强制重新创建演示账号（会清空旧用户及关联数据）")
    args = parser.parse_args()
    asyncio.run(seed(force=args.force))
