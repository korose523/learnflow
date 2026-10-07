"""End-to-end apparatus checks with a temporary database, no real participants."""
import csv
import io
from datetime import timedelta
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.database import Base, get_db
from app.api.auth import get_current_user
from app.api.research import router
from app.models.user import User, UserRole
from app.models.task import Task, Attempt
from app.models.research import ResearchParticipant, ResearchAllocation, ResearchSession, ResearchTrial
from app.services.research_study import allocated_targets, expected_success, now
import app.models  # register all FK targets


@pytest_asyncio.fixture
async def apparatus():
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        users = [User(id=x, email=f'{x}@example.test', name=x, hashed_password='not-a-real-password', role=role) for x, role in [('admin',UserRole.ADMIN),('student',UserRole.STUDENT),('other',UserRole.STUDENT)]]
        db.add_all(users)
        for topic in ['a','b','c','d']:
            for phase in ['pretest','practice','posttest','delayed']:
                db.add(Task(id=f'{topic}-{phase}',content='Solve x + 3 = 10.',topic=topic,difficulty=3,correct_answer='7'))
        await db.commit()
    app = FastAPI(); app.include_router(router)
    selected = {'user': users[0]}
    async def current(): return selected['user']
    async def database():
        async with factory() as db:
            try:
                yield db
                await db.commit()
            except Exception:
                await db.rollback(); raise
    app.dependency_overrides[get_current_user] = current
    app.dependency_overrides[get_db] = database
    async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
        yield client,selected,users,factory
    await engine.dispose()


async def setup_study(client, mode='dry_run'):
    response=await client.post('/api/v1/research/studies',json={'title':'Technical dry run','protocol_version':'draft-1','protocol_hash':'a'*64,'consent_version':'draft-1','consent_text':'Technical test only. No human participation or validated clinical evidence.','topics':['a','b','c','d'],'phase_counts':dict.fromkeys(['pretest','practice','posttest','delayed'],1),'mode':mode})
    assert response.status_code==200,response.text
    study=response.json()['id']
    items=[{'task_id':f'{topic}-{phase}','topic':topic,'phase':phase,'difficulty_elo':1500} for topic in ['a','b','c','d'] for phase in ['pretest','practice','posttest','delayed']]
    response=await client.post(f'/api/v1/research/studies/{study}/items',json=items)
    assert response.status_code==200,response.text
    return study


@pytest.mark.asyncio
async def test_full_persisted_flow_withdrawal_and_masking(apparatus):
    c,selected,users,factory=apparatus
    study=await setup_study(c)
    assert (await c.post(f'/api/v1/research/studies/{study}/activate',json={})).status_code==200
    selected['user']=users[1]
    consent={'consent_version':'draft-1','accepted':True,'adult_confirmed':True}
    assert (await c.post(f'/api/v1/research/studies/{study}/consent',json={**consent,'adult_confirmed':False})).status_code==422
    participant=(await c.post(f'/api/v1/research/studies/{study}/consent',json=consent)).json()['research_id']
    assert (await c.post(f'/api/v1/research/studies/{study}/consent',json=consent)).json()['research_id']==participant
    assert (await c.post(f'/api/v1/research/studies/{study}/sessions',json={'topic':'a','phase':'posttest'})).status_code==409
    for phase in ['pretest','practice','posttest']:
        session=(await c.post(f'/api/v1/research/studies/{study}/sessions',json={'topic':'a','phase':phase})).json()['session_id']
        trial=(await c.get(f'/api/v1/research/sessions/{session}/next')).json()
        assert trial['trial_id']==(await c.get(f'/api/v1/research/sessions/{session}/next')).json()['trial_id']
        assert 'correct_answer' not in trial['task'] and 'target_success' not in trial
        selected['user']=users[2]
        assert (await c.get(f'/api/v1/research/sessions/{session}/next')).status_code==403
        selected['user']=users[1]
        url=f"/api/v1/research/trials/{trial['trial_id']}/answer"
        assert (await c.post(url,json={'correct':True,'response_ms':50})).status_code==422
        assert (await c.post(url,json={'answer':'A l i c e','response_ms':50})).status_code==422
        result=(await c.post(url,json={'answer':'x = 7','response_ms':1000})).json()
        assert result['is_correct'] is (True if phase=='practice' else None)
        assert (await c.post(url,json={'answer':'x = 7','response_ms':1000})).json()['replayed']
        assert (await c.post(url,json={'answer':'8','response_ms':1000})).status_code==409
        assert (await c.get(f'/api/v1/research/sessions/{session}/next')).json()['complete']
    assert (await c.post(f'/api/v1/research/studies/{study}/sessions',json={'topic':'a','phase':'delayed'})).status_code==409
    async with factory() as db:
        previous=(await db.execute(select(ResearchSession).where(ResearchSession.participant_id==participant,ResearchSession.phase=='posttest'))).scalar_one()
        previous.completed_at=now()-timedelta(days=8);await db.commit()
    assert (await c.post(f'/api/v1/research/studies/{study}/sessions',json={'topic':'a','phase':'delayed'})).status_code==200
    assert (await c.get(f'/api/v1/research/studies/{study}/export.csv')).status_code==403
    selected['user']=users[0]
    export=await c.get(f'/api/v1/research/studies/{study}/export.csv')
    rows=list(csv.DictReader(io.StringIO(export.text)))
    assert len(rows)==3 and all(r['mode']=='dry_run' for r in rows)
    assert not {'user_id','email','name','parent_id'} & set(rows[0])
    async with factory() as db:
        assert (await db.execute(select(func.count(Attempt.id)))).scalar_one()==0
        assert (await db.execute(select(func.count(ResearchTrial.id)))).scalar_one()==3
        assert (await db.execute(select(func.count(ResearchAllocation.id)))).scalar_one()==4
    selected['user']=users[1]
    assert (await c.post(f'/api/v1/research/studies/{study}/withdraw')).json()['withdrawn']
    assert (await c.get(f'/api/v1/research/sessions/{session}/next')).status_code==403
    selected['user']=users[0]
    assert len(list(csv.DictReader(io.StringIO((await c.get(f'/api/v1/research/studies/{study}/export.csv')).text))))==0


@pytest.mark.asyncio
async def test_live_mode_cannot_activate_draft_bank(apparatus):
    c,_,_,_=apparatus
    study=await setup_study(c,'live')
    r=await c.post(f'/api/v1/research/studies/{study}/activate',json={})
    assert r.status_code==409 and '伦理' in r.json()['detail']
    r=await c.post(f'/api/v1/research/studies/{study}/activate',json={'approval_reference':'TEST-NOT-AN-APPROVAL','approval_confirmed':True})
    assert r.status_code==409 and '300' in r.json()['detail']


@pytest.mark.asyncio
async def test_bank_freeze_and_overlap(apparatus):
    c,selected,users,_=apparatus
    study=await setup_study(c)
    r=await c.post(f'/api/v1/research/studies/{study}/items',json=[{'task_id':'a-pretest','topic':'a','phase':'posttest','difficulty_elo':1500}])
    assert r.status_code==409
    await c.post(f'/api/v1/research/studies/{study}/activate',json={})
    assert (await c.post(f'/api/v1/research/studies/{study}/items',json=[{'task_id':'a-pretest','topic':'a','phase':'pretest','difficulty_elo':1500}])).status_code==409
    selected['user']=users[1]
    assert (await c.post('/api/v1/research/studies',json={})).status_code==403


def test_counterbalancing_and_monotonic_selection():
    targets=[.65,.75,.85,.95]
    for block in range(10):
        rows=[allocated_targets('fixed-seed',block*4+i,4,targets) for i in range(4)]
        assert all(sorted(row)==targets for row in rows)
        assert all(sorted(row[j] for row in rows)==targets for j in range(4))
    assert expected_success(1500,1100)>expected_success(1500,1500)>expected_success(1500,1900)
