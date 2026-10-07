"""Preview/import numeric XES tasks. Database writes require --apply explicitly.

Use a separate local development database. This does not create a live study,
mark expert review, or claim calibrated IRT difficulty.
"""
import argparse,asyncio,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'learnflow-backend'))
BANK=ROOT/'results/k12/xes_question_bank.json'


def compatible():
    return [item for item in json.loads(BANK.read_text())['items'] if item['numeric_app_compatible']]


async def apply(items,admin_id):
    import app.models
    from app.core.database import AsyncSessionLocal,init_db,using_fallback_database
    from app.models.user import User,UserRole
    from app.models.task import Task
    await init_db()
    if using_fallback_database():raise RuntimeError('Refusing silent fallback database')
    async with AsyncSessionLocal() as db:
        user=await db.get(User,admin_id)
        if user is None or user.role!=UserRole.ADMIN:raise ValueError('Pre-existing administrator required')
        added=0
        for item in items:
            if await db.get(Task,item['task_id']) is not None:continue
            route=item['kc_routes'][0] if item['kc_routes'] else 'XES公开数学题'
            topic=route.split('----')[-1][:100]
            p=item['train_smoothed_success']
            level=3 if p is None else min(5,max(1,int((1-p)*5)+1))
            db.add(Task(id=item['task_id'],title=f"XES3G5M #{item['source_item_id']}",content=item['content'],topic=topic,
                difficulty=level,correct_answer=item['normalized_numeric_answer'],source='XES3G5M_MIT',
                is_approved=False,created_by=user.id))
            await db.flush();added+=1
        await db.commit();print(json.dumps({'added':added,'expert_reviewed':False,'difficulty':'coarse_observed_rate_bin_not_IRT'}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--apply',action='store_true');p.add_argument('--admin-id')
    a=p.parse_args();items=compatible()
    if a.apply:
        if not a.admin_id:p.error('--apply requires --admin-id')
        asyncio.run(apply(items,a.admin_id))
    else:print(json.dumps({'mode':'PREVIEW_NO_DATABASE_WRITES','compatible_items':len(items),'source':'XES3G5M','license':'MIT','expert_reviewed':False},ensure_ascii=False,indent=2))
