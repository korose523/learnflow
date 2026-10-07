"""Persisted teacher/admin review decisions through real API routes."""
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.database import Base, get_db
from app.api.auth import get_current_user
from app.api.teacher import router as teacher_router
from app.api.admin import router as admin_router
from app.models.user import User, UserRole
import app.models

@pytest_asyncio.fixture
async def review_app():
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    users = [User(id=r, email=f'{r}@example.test', name=r, hashed_password='fixture', role=UserRole(r)) for r in ['teacher','admin','student']]
    async with factory() as db: db.add_all(users); await db.commit()
    selected = {'user': users[0]}
    app = FastAPI(); app.include_router(teacher_router); app.include_router(admin_router)
    async def current(): return selected['user']
    async def database():
        async with factory() as db:
            try: yield db; await db.commit()
            except Exception: await db.rollback(); raise
    app.dependency_overrides[get_current_user] = current
    app.dependency_overrides[get_db] = database
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as c: yield c, selected, users
    await engine.dispose()

def payload(**changes):
    return {'title':'Fixture','content':'x + 3 = 10','topic':'algebra','correct_answer':'7','explanation':'Subtract 3',**changes}

async def test_rejection_leaves_queue_and_persists_reason(review_app):
    c, selected, users = review_app
    r = await c.post('/api/v1/teacher/tasks', json=payload()); assert r.status_code == 200
    task = r.json()['id']; selected['user'] = users[1]
    pending = (await c.get('/api/v1/admin/pending-tasks')).json(); assert pending['total'] == 1
    assert pending['tasks'][0]['correct_answer'] == '7' and pending['tasks'][0]['explanation'] == 'Subtract 3'
    assert (await c.post('/api/v1/admin/review-task',json={'task_id':task,'approved':False,'review_notes':'Revise wording'})).status_code == 200
    assert (await c.get('/api/v1/admin/pending-tasks')).json()['total'] == 0
    selected['user'] = users[0]; record = (await c.get('/api/v1/teacher/tasks')).json()[0]
    assert record['is_approved'] is False and record['review_status'] == 'rejected' and record['review_notes'] == 'Revise wording'
    selected['user'] = users[2]
    assert (await c.get('/api/v1/admin/pending-tasks')).status_code == 403
    assert (await c.post('/api/v1/admin/review-task',json={'task_id':task,'approved':True})).status_code == 403

async def test_approval_and_full_review_content(review_app):
    c, selected, users = review_app; content = 'Long fixture ' * 30
    task = (await c.post('/api/v1/teacher/tasks',json=payload(content=content))).json()['id']; selected['user'] = users[1]
    assert (await c.get('/api/v1/admin/pending-tasks')).json()['tasks'][0]['content'] == content.strip()
    assert (await c.post('/api/v1/admin/review-task',json={'task_id':task,'approved':True})).status_code == 200
    assert (await c.get('/api/v1/admin/pending-tasks')).json()['total'] == 0
    selected['user'] = users[0]; record = (await c.get('/api/v1/teacher/tasks')).json()[0]
    assert record['is_approved'] is True and record['review_status'] == 'approved'

@pytest.mark.parametrize('change',[{'difficulty':0},{'difficulty':11},{'content':'  '},{'correct_answer':' '},{'topic':' '},{'time_estimate':0}])
async def test_invalid_tasks_cannot_enter_review_queue(review_app,change):
    c, _, _ = review_app
    assert (await c.post('/api/v1/teacher/tasks',json=payload(**change))).status_code == 422

async def test_topic_fallback_never_selects_unreviewed_or_other_topic():
    from app.models.task import Task
    from app.services.learning_orchestrator import LearningOrchestrator
    engine = create_async_engine('sqlite+aiosqlite:///:memory:')
    async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine,expire_on_commit=False)
    async with factory() as db:
        db.add_all([Task(id='approved-far',content='fixture',topic='wanted',difficulty=1,correct_answer='7',is_approved=True),Task(id='pending-near',content='fixture',topic='wanted',difficulty=8,correct_answer='7',is_approved=False),Task(id='other-near',content='fixture',topic='other',difficulty=8,correct_answer='7',is_approved=True)])
        await db.commit()
        assert (await LearningOrchestrator._select_approved_task(db,8,'wanted')).id == 'approved-far'
        assert await LearningOrchestrator._select_approved_task(db,8,'missing') is None
        assert (await LearningOrchestrator._select_approved_task(db,8,None)).id == 'other-near'
    await engine.dispose()

@pytest.mark.parametrize('failure,status,detail',[('empty',404,'No approved fixture'),('internal',500,'题目服务暂时不可用，请稍后重试')])
async def test_empty_pool_and_internal_failure_have_distinct_status(review_app,monkeypatch,failure,status,detail):
    from fastapi import HTTPException
    from app.api.student import router as student_router
    from app.services.learning_orchestrator import LearningOrchestrator
    from unittest.mock import AsyncMock
    c, selected, users = review_app
    c._transport.app.include_router(student_router)
    selected['user'] = users[2]
    exception = HTTPException(status_code=404,detail='No approved fixture') if failure=='empty' else RuntimeError('internal fixture detail must not leak')
    monkeypatch.setattr(LearningOrchestrator,'build_next_task',AsyncMock(side_effect=exception))
    response = await c.get('/api/v1/student/next-task')
    assert response.status_code == status and response.json()['detail'] == detail
