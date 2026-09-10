"""演示用示例题目与默认反馈文案 —— 单一数据源。

同时被两条路径复用，避免「双份种子」漂移：
- ``seed.py`` 的 ``--force`` 全量重置；
- ``app/main.py`` 启动时若 ``DEMO_DATA_ENABLED=true`` 自动置备，使项目开箱即用。

注意：家长绑定统一采用 ``parent_{student_local}@learnflow.com`` 方案，
与 ``app/models/user.py::User.is_demo_parent_bound`` 的判定保持一致。
"""
from sqlalchemy import select, func

from app.models.task import Task
from app.models.consent import FeedbackScript


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


async def ensure_sample_tasks(db) -> int:
    """若库中尚无题目则批量写入示例题目，返回新建数量。"""
    existing = (await db.execute(select(func.count(Task.id)))).scalar() or 0
    if existing:
        return 0
    for t in SAMPLE_TASKS:
        db.add(Task(
            topic=t["topic"],
            difficulty=t["difficulty"],
            content=t["content"],
            correct_answer=t["correct_answer"],
            explanation=t["explanation"],
            is_approved=True,
        ))
    await db.commit()
    return len(SAMPLE_TASKS)


async def ensure_feedback_scripts(db) -> int:
    """若库中尚无反馈文案则批量写入默认文案，返回新建数量。"""
    existing = (await db.execute(select(func.count(FeedbackScript.id)))).scalar() or 0
    if existing:
        return 0
    for s in DEFAULT_SCRIPTS:
        db.add(FeedbackScript(
            category=s["category"],
            text=s["text"],
            review_status="approved",
        ))
    await db.commit()
    return len(DEFAULT_SCRIPTS)
