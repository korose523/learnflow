import asyncio
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User
from sqlalchemy import select

PASSWORDS = {
    "admin@learnflow.com": "Admin123!",
    "teacher@learnflow.com": "Teacher123!",
    "student@learnflow.com": "Student123!",
    "parent@learnflow.com": "Parent123!",
    "parent_student@learnflow.com": "Parent123!",
    "parent_admin@learnflow.com": "Parent123!",
}

async def main():
    async with AsyncSessionLocal() as db:
        for email, pw in PASSWORDS.items():
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            if user:
                user.hashed_password = hash_password(pw)
                print(f"✅ 重置 {email} 密码")
            else:
                print(f"⚠️ 未找到 {email}")
        await db.commit()

if __name__ == "__main__":
    asyncio.run(main())
