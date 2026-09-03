import asyncio
import traceback
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.services.learning_orchestrator import LearningOrchestrator

async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == "student@learnflow.com"))
        user = result.scalar_one()
        try:
            task = await LearningOrchestrator.build_next_task(user, None, db)
            print("SUCCESS")
            print(task)
        except Exception as e:
            print("ERROR", e)
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
