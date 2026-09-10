"""LearnFlow —— AI驱动的游戏化学习平台
FastAPI 主应用入口
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

# 配置日志（输出到 stdout，CloudBase 会收集）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


# 延迟注册路由（避免启动时循环导入）
async def _register_routers(app: FastAPI) -> None:
    """注册所有 API 路由"""
    try:
        from app.api import auth, student, teacher, parent, admin, gamification, k12, class_pet, analytics
        routers = [
            auth.router, student.router, teacher.router, parent.router,
            admin.router, gamification.router, k12.router,
            teacher.k12_router, parent.k12_router, class_pet.router,
            analytics.router,
        ]
        for router in routers:
            app.include_router(router)
        logger.info(f"✅ 已注册所有路由，共 {len(app.routes)} 个")
    except Exception as e:
        logger.error(f"❌ 注册路由失败: {e}")
        raise


async def _ensure_demo_users() -> None:
    """确保演示账号存在，并统一 onboarding"""
    from app.core.security import hash_password
    from app.models.user import User, UserRole
    from app.core.database import _get_sessionmaker
    from app.services.onboarding_service import OnboardingService
    from sqlalchemy import select

    demo_passwords = {
        "student": settings.SEED_STUDENT_PASSWORD,
        "teacher": settings.SEED_TEACHER_PASSWORD,
        "parent": settings.SEED_PARENT_PASSWORD,
        "admin": settings.SEED_ADMIN_PASSWORD,
    }
    if not all(demo_passwords.values()):
        logger.warning("演示账号未创建：请先配置所有 SEED_*_PASSWORD 环境变量")
        return

    demo_users = [
        ("student@learnflow.com", demo_passwords["student"], "Demo Student", UserRole.STUDENT),
        ("teacher@learnflow.com", demo_passwords["teacher"], "Demo Teacher", UserRole.TEACHER),
        ("parent@learnflow.com", demo_passwords["parent"], "Demo Parent", UserRole.PARENT),
        ("admin@learnflow.com", demo_passwords["admin"], "Demo Admin", UserRole.ADMIN),
    ]

    parent_bindings = {
        "student@learnflow.com": "parent_student@learnflow.com",
        "teacher@learnflow.com": "parent_teacher@learnflow.com",
        "parent@learnflow.com": "parent_parent@learnflow.com",
        "admin@learnflow.com": "parent_admin@learnflow.com",
    }

    sessionmaker = _get_sessionmaker()
    async with sessionmaker() as db:
        created_or_existing: dict = {}

        # 第一步：创建或获取 4 个演示角色账号
        for email, password, name, role in demo_users:
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            if user is None:
                user = User(
                    email=email,
                    hashed_password=hash_password(password),
                    name=name,
                    role=role,
                    is_active=True,
                )
                if role == UserRole.STUDENT:
                    user.grade = "五年级"
                db.add(user)
                await db.flush()
                await db.refresh(user)
                logger.info(f"✅ 创建演示账号: {name} ({email})")
            else:
                logger.info(f"⏭️ 跳过已存在的演示账号: {email}")
            created_or_existing[email] = user

        # 第二步：创建对应的 4 个默认家长账号并绑定
        for child_email, parent_email in parent_bindings.items():
            child_user = created_or_existing[child_email]
            result = await db.execute(select(User).where(User.email == parent_email))
            parent_user = result.scalar_one_or_none()
            if parent_user is None:
                parent_name = f"{child_user.name}的家长"
                parent_user = User(
                    email=parent_email,
                hashed_password=hash_password(demo_passwords["parent"]),
                    name=parent_name,
                    role=UserRole.PARENT,
                    is_active=True,
                )
                db.add(parent_user)
                await db.flush()
                await db.refresh(parent_user)
                logger.info(f"✅ 创建默认家长: {parent_email}")
            else:
                logger.info(f"⏭️ 跳过已存在的家长账号: {parent_email}")

            # 绑定亲子关系（仅当学生未绑定或绑定不是当前家长时）
            if child_user.role == UserRole.STUDENT and child_user.parent_id != parent_user.id:
                child_user.parent_id = parent_user.id
                await db.flush()
                logger.info(f"🔗 绑定 {child_email} → 家长 {parent_email}")
            elif child_user.role != UserRole.STUDENT:
                # 教师/管理员也生成一个关联家长，但 parent_id 只给学生
                # 这里记录关系：在 parent 表中，通过 OnboardingService 的演示绑定逻辑
                pass

        # 第三步：统一 onboarding（默认宠物、技能画像、consents、演示绑定）
        for user in created_or_existing.values():
            await OnboardingService.onboard(user, db)

        # 补充示例题目与默认反馈文案，使「答题 / 反馈」链路开箱即用
        # （单一数据源见 app/services/seed_data.py，与 seed.py 共用，避免双份种子漂移）
        from app.services.seed_data import ensure_sample_tasks, ensure_feedback_scripts
        await ensure_sample_tasks(db)
        await ensure_feedback_scripts(db)

        await db.commit()
    logger.info("✅ 演示账号种子数据完成")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    import os
    port = os.getenv("PORT", "8000")
    logger.info("🚀 LearnFlow 后端启动中...")
    logger.info(f"🌍 环境: {settings.ENVIRONMENT}")
    logger.info(f"📍 监听端口: {port}")
    logger.info(f"📖 API 文档: http://0.0.0.0:{port}/docs")

    # 先注册路由（这会触发模型导入，确保 Base.metadata 包含所有表）
    await _register_routers(app)

    # 导入所有模型（确保 Base.metadata 包含所有表）
    import app.models  # noqa: F401

    # 初始化数据库
    try:
        from app.core.database import init_db
        await init_db()
        logger.info("✅ 数据库初始化完成")
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败（应用将继续运行）: {e}")

    # 演示数据只能由显式开关启动，避免生产环境出现默认账号。
    if settings.DEMO_DATA_ENABLED:
        try:
            await _ensure_demo_users()
            logger.info("✅ 演示账号种子数据完成")
        except Exception as e:
            logger.error(f"❌ 创建演示账号失败: {e}")
    else:
        logger.info("ℹ️ 演示账号创建已关闭（DEMO_DATA_ENABLED=false）")

    yield

    # 关闭事件
    logger.info("🛑 LearnFlow 后端正在关闭...")
    try:
        from app.core.database import close_db
        await close_db()
        logger.info("✅ 数据库连接已关闭")
    except Exception as e:
        logger.error(f"❌ 关闭数据库时出错: {e}")


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="让学习本身成为内在奖励 —— 通过心流与放松引导提升长期投入",
    lifespan=lifespan,
)

# CORS 配置
allowed_origins = settings.ALLOWED_ORIGINS
logger.info(f"🌐 CORS 允许的来源: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 健康检查（最重要！CloudBase 用它检测应用是否启动成功）
@app.get("/health")
async def health():
    logger.info("✅ 健康检查被调用")
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }


# 根路径
@app.get("/")
async def root():
    logger.info("📍 根路径被访问")
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
        "message": "🎓 让学习成为享受"
    }
