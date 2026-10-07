"""Explicit local setup CLI. Never creates or activates a live study.

Run from backend with the selected DATABASE_URL and a pre-existing admin id:
python ../experiments/research/create_dry_run.py --admin-id <id>
This command writes Task and research tables ONLY when explicitly invoked.
"""
import argparse
import asyncio
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'learnflow-backend'))

async def main(admin_id):
    from app.core.database import AsyncSessionLocal, init_db, using_fallback_database
    import app.models
    from app.models.user import User,UserRole
    from app.models.task import Task
    from app.models.research import ResearchStudy,ResearchItem
    bank=json.loads((ROOT/'experiments/research/math_bank_draft_v1.json').read_text())
    protocol=(ROOT/'docs/人类实验_推荐Protocol与IRB初稿.md').read_bytes()
    await init_db()
    if using_fallback_database():raise RuntimeError('Configured database unavailable; refusing setup in fallback database.')
    async with AsyncSessionLocal() as db:
        admin=await db.get(User,admin_id)
        if not admin or admin.role!=UserRole.ADMIN:raise ValueError('Pre-existing administrator required')
        import secrets
        study=ResearchStudy(title='LearnFlow 技术演练（无真实研究结果）',protocol_version='recommended-draft-20261007',
            protocol_hash=hashlib.sha256(protocol).hexdigest(),consent_version='technical-rehearsal-v1',
            consent_text='这是系统开发人员的技术演练，不是正式人体研究。使用演示账户与虚拟回答，不输入个人资料。本演练不证明伦理批准或学习效果。可随时退出，撤回后记录从默认导出中排除。',
            mode='dry_run',status='active',topics=bank['topics'],targets=[.65,.75,.85,.95],
            phase_counts={'pretest':10,'practice':40,'posttest':10,'delayed':10},practice_seconds=600,delay_days=7,allocation_seed=secrets.token_hex(32))
        db.add(study);await db.flush()
        for item in bank['items']:
            task=await db.get(Task,item['task_id'])
            if task is None:
                db.add(Task(id=item['task_id'],content=item['content'],topic=item['topic'],difficulty=item['nominal_level'],
                    correct_answer=item['correct_answer'],source=item['source'],is_approved=False,created_by=admin.id))
                await db.flush()
            db.add(ResearchItem(study_id=study.id,task_id=item['task_id'],topic=item['topic'],phase=item['phase'],difficulty_elo=item['difficulty_elo'],expert_reviewed=False))
        await db.commit()
        print(f'DRY RUN ONLY: /research/{study.id}')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--admin-id',required=True)
    asyncio.run(main(parser.parse_args().admin_id))
