"""Persisted review lifecycle with the real grader and scheduler, no participants."""
from datetime import datetime, timedelta, UTC
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.database import Base, get_db
from app.api.auth import get_current_user
from app.api.student import router
from app.api.teacher import router as teacher_router, k12_router
from app.models.user import User, UserRole
from app.models.task import Task, Attempt, SpacedReview
from app.services.learning_orchestrator import LearningOrchestrator
import app.models

@pytest_asyncio.fixture
async def review_app():
    engine=create_async_engine('sqlite+aiosqlite:///:memory:')
    async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
    factory=async_sessionmaker(engine,expire_on_commit=False)
    users=[User(id=x,email=f'{x}@example.test',name=x,hashed_password='fixture',role=UserRole.STUDENT) for x in ['reviewer','other']]
    async with factory() as db:
        db.add_all(users);db.add(Task(id='item',content='Solve x+3=10',topic='algebra',difficulty=5,correct_answer='7',is_approved=True))
        db.add(SpacedReview(id='due',user_id='reviewer',task_id='item',scheduled_date=datetime.now(UTC)-timedelta(days=1),review_number=1,next_interval_days=1));await db.commit()
    selected={'user':users[0]};app=FastAPI();app.include_router(router);app.include_router(teacher_router);app.include_router(k12_router)
    async def current():return selected['user']
    async def database():
        async with factory() as db:
            try:yield db;await db.commit()
            except Exception:await db.rollback();raise
    app.dependency_overrides[get_current_user]=current;app.dependency_overrides[get_db]=database
    async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as c:yield c,selected,users,factory
    await engine.dispose()

async def test_review_is_graded_completed_and_not_submitted_twice(review_app):
    c,selected,users,factory=review_app
    listing=(await c.get('/api/v1/student/due-reviews')).json();assert listing['total_due']==1
    assert 'correct_answer' not in listing['due_reviews'][0]
    selected['user']=users[1];assert (await c.post('/api/v1/student/reviews/due/answer',json={'answer':'7'})).status_code==404
    selected['user']=users[0]
    assert (await c.post('/api/v1/student/reviews/due/answer',json={'correct':True})).status_code==422
    r=await c.post('/api/v1/student/reviews/due/answer',json={'answer':'x = 7','time_spent':2});assert r.status_code==200,r.text
    assert r.json()['is_correct'] is True
    assert (await c.post('/api/v1/student/reviews/due/answer',json={'answer':'7'})).status_code==409
    assert (await c.get('/api/v1/student/due-reviews')).json()['total_due']==0
    async with factory() as db:
        old=await db.get(SpacedReview,'due');assert old.completed_date is not None and old.result is True
        assert (await db.execute(select(func.count(Attempt.id)))).scalar_one()==1
        pending=(await db.execute(select(SpacedReview).where(SpacedReview.completed_date.is_(None)))).scalars().all()
        assert len(pending)==1 and pending[0].scheduled_date>datetime.now(UTC).replace(tzinfo=None)

async def test_future_review_and_unapproved_item_are_not_answerable(review_app):
    c,_,_,factory=review_app
    async with factory() as db:
        row=await db.get(SpacedReview,'due');row.scheduled_date=datetime.now(UTC)+timedelta(days=1);await db.commit()
    assert (await c.post('/api/v1/student/reviews/due/answer',json={'answer':'7'})).status_code==409
    async with factory() as db:
        row=await db.get(SpacedReview,'due');row.scheduled_date=datetime.now(UTC)-timedelta(days=1)
        task=await db.get(Task,'item');task.is_approved=False;await db.commit()
    assert (await c.get('/api/v1/student/due-reviews')).json()['total_due']==0
    assert (await c.post('/api/v1/student/reviews/due/answer',json={'answer':'7'})).status_code==409

async def test_tied_timestamps_are_not_skipped_by_cursor(review_app):
    c,_,_,factory=review_app
    async with factory() as db:
        row=await db.get(SpacedReview,'due');stamp=row.scheduled_date
        for i in range(3):db.add(SpacedReview(id=f'tie-{i}',user_id='reviewer',task_id='item',scheduled_date=stamp))
        await db.commit()
    ids=[];cursor=None
    while True:
        params={'limit':1}
        if cursor:params['cursor']=cursor
        r=await c.get('/api/v1/student/due-reviews',params=params);assert r.status_code==200
        data=r.json();assert data['total_due']==4;ids.extend(x['id'] for x in data['due_reviews']);cursor=data['next_cursor']
        if cursor is None:break
    assert sorted(ids)==['due','tie-0','tie-1','tie-2']
    assert (await c.get('/api/v1/student/due-reviews',params={'cursor':'invalid'})).status_code==400

async def test_practice_reschedules_one_pending_item(review_app):
    _,_,_,factory=review_app
    async with factory() as db:
        await LearningOrchestrator._schedule_review('reviewer','item',True,db)
        await LearningOrchestrator._schedule_review('reviewer','item',False,db);await db.commit()
        rows=(await db.execute(select(SpacedReview))).scalars().all();assert len(rows)==1 and rows[0].completed_date is None

async def test_all_practice_routes_enforce_current_task_approval(review_app):
    c,_,_,factory=review_app
    async with factory() as db:
        task=await db.get(Task,'item');task.is_approved=False;await db.commit()
    for route in ['submit-answer','attempt']:
        response=await c.post(f'/api/v1/student/{route}',json={'task_id':'item','answer':'7'})
        assert response.status_code==409,response.text
        assert (await c.post(f'/api/v1/student/{route}',json={'task_id':'missing','answer':'7'})).status_code==404
    async with factory() as db:
        assert (await db.execute(select(func.count(Attempt.id)))).scalar_one()==0
        rows=(await db.execute(select(SpacedReview))).scalars().all()
        assert len(rows)==1 and rows[0].completed_date is None
        task=await db.get(Task,'item');task.is_approved=True;await db.commit()
    for route in ['submit-answer','attempt']:
        response=await c.post(f'/api/v1/student/{route}',json={'task_id':'item','answer':'7'})
        assert response.status_code==200,response.text
        assert response.json()['is_correct'] is True
    async with factory() as db:
        assert (await db.execute(select(func.count(Attempt.id)))).scalar_one()==2

async def test_recovery_requires_own_latest_wrong_answer_and_has_no_repeat_rewards(review_app):
    from app.models.pet import PetProfile
    c,selected,users,factory=review_app
    endpoint='/api/v1/student/recovery-choice'
    assert (await c.post(endpoint,json={'task_id':'item','choice':'invented'})).status_code==422
    assert (await c.post(endpoint,json={'task_id':'item','choice':'watch_tutorial'})).status_code==409
    async with factory() as db:
        db.add(PetProfile(user_id='reviewer',name='fixture'))
        task=await db.get(Task,'item');task.explanation='Subtract 3';await db.commit()
    assert (await c.post('/api/v1/student/submit-answer',json={'task_id':'item','answer':'8'})).status_code==200
    async with factory() as db:
        pet=(await db.execute(select(PetProfile))).scalar_one()
        before=(pet.understanding,pet.persistence,pet.creativity,pet.collaboration,pet.level,pet.mood)
    for choice in ['watch_tutorial','watch_tutorial','retry','skip']:
        r=await c.post(endpoint,json={'task_id':'item','choice':choice});assert r.status_code==200,r.text
        if choice=='watch_tutorial':assert r.json()['tutorial']=='Subtract 3'
    async with factory() as db:
        pet=(await db.execute(select(PetProfile))).scalar_one()
        assert before==(pet.understanding,pet.persistence,pet.creativity,pet.collaboration,pet.level,pet.mood)
        assert (await db.execute(select(func.count(Attempt.id)))).scalar_one()==1
        task=await db.get(Task,'item');task.is_approved=False;await db.commit()
    assert (await c.post(endpoint,json={'task_id':'item','choice':'watch_tutorial'})).status_code==409
    async with factory() as db:
        task=await db.get(Task,'item');task.is_approved=True;await db.commit()
    selected['user']=users[1]
    assert (await c.post(endpoint,json={'task_id':'item','choice':'watch_tutorial'})).status_code==409
    selected['user']=users[0]
    assert (await c.post('/api/v1/student/submit-answer',json={'task_id':'item','answer':'7'})).status_code==200
    assert (await c.post(endpoint,json={'task_id':'item','choice':'watch_tutorial'})).status_code==409

async def test_teacher_assignment_ownership_validation_and_repeated_update(review_app):
    from app.models.curriculum import Class, GradeLevel, Subject, CurriculumNode, Assignment
    c,selected,users,factory=review_app
    users[0].role=UserRole.TEACHER
    async with factory() as db:
        db.add_all([GradeLevel(id='g',code='G3',label='G3'),Subject(id='s',code='math',name='Math')]);await db.flush()
        db.add_all([Class(id='own',name='Own',grade_id='g',teacher_id=users[0].id),Class(id='foreign',name='Foreign',grade_id='g',teacher_id=users[1].id),CurriculumNode(id='n',title='Addition',subject_id='s',grade_id='g')]);await db.commit()
    data=(await c.get('/api/v1/teacher/classroom')).json()
    assert [x['id'] for x in data['classes']]==['own']
    for route in ['assignments','class-mastery']:
        assert (await c.get(f'/api/v1/teacher/{route}',params={'class_id':'foreign'})).status_code==404
    assert (await c.post('/api/v1/teacher/assignments',json={'class_id':'foreign','node_ids':['n']})).status_code==404
    assert (await c.post('/api/v1/teacher/assignments',json={'class_id':'own','node_ids':[]})).status_code==422
    assert (await c.post('/api/v1/teacher/assignments',json={'class_id':'own','node_ids':['n','missing']})).status_code==400
    async with factory() as db:assert (await db.execute(select(func.count(Assignment.id)))).scalar_one()==0
    payload={'class_id':'own','node_ids':['n','n'],'due_at':'2026-12-01T10:00:00+00:00'}
    first=await c.post('/api/v1/teacher/assignments',json=payload);assert first.status_code==200,first.text
    assert first.json()['created']==1
    payload['due_at']='2026-12-02T10:00:00+00:00'
    again=await c.post('/api/v1/teacher/assignments',json=payload);assert again.status_code==200,again.text
    assert first.json()['assignment_id']==again.json()['assignment_id']
    assert again.json()['created']==0 and again.json()['updated']==1
    listing=(await c.get('/api/v1/teacher/assignments',params={'class_id':'own'})).json()['assignments']
    assert len(listing)==1 and listing[0]['due_at'].startswith('2026-12-02')

async def test_teacher_classroom_and_mastery_exclude_other_class(review_app):
    from app.models.curriculum import Class, GradeLevel, Subject, CurriculumNode
    c,selected,users,factory=review_app
    teacher=User(id='teacher',email='teacher@example.test',name='teacher',hashed_password='fixture',role=UserRole.TEACHER)
    selected['user']=teacher
    async with factory() as db:
        db.add_all([teacher,GradeLevel(id='g',code='G3',label='G3'),Subject(id='s',code='math',name='Math')]);await db.flush()
        db.add_all([Class(id='own',name='Own',grade_id='g',teacher_id='teacher'),Class(id='foreign',name='Foreign',grade_id='g'),CurriculumNode(id='n',title='Addition',subject_id='s',grade_id='g')]);await db.flush()
        a=await db.get(User,users[0].id);a.class_id='own'
        b=await db.get(User,users[1].id);b.class_id='foreign'
        task=await db.get(Task,'item');task.curriculum_node_id='n'
        db.add_all([Attempt(user_id=a.id,task_id='item',answer='7',is_correct=True),Attempt(user_id=b.id,task_id='item',answer='8',is_correct=False)]);await db.commit()
    dashboard=(await c.get('/api/v1/teacher/classroom')).json()
    assert dashboard['total_students']==1 and dashboard['students'][0]['id']==users[0].id
    heat=(await c.get('/api/v1/teacher/class-mastery',params={'class_id':'own'})).json()
    assert heat['nodes'][0]['mastery']==100.0

async def test_remaining_teacher_routes_scope_reads_and_writes(review_app):
    from app.models.curriculum import Class
    from app.models.consent import Alert, AlertType
    c,selected,users,factory=review_app
    teacher=User(id='teacher',email='teacher@example.test',name='teacher',hashed_password='fixture',role=UserRole.TEACHER)
    selected['user']=teacher
    async with factory() as db:
        db.add(teacher);await db.flush()
        db.add_all([Class(id='own',name='Own',teacher_id='teacher'),Class(id='foreign',name='Foreign')]);await db.flush()
        (await db.get(User,users[0].id)).class_id='own'
        (await db.get(User,users[1].id)).class_id='foreign'
        for uid in [users[0].id,users[1].id]:
            db.add(Alert(id=f'alert-{uid}',user_id=uid,alert_type=AlertType.PERFORMANCE_DROP,title=uid))
            for i in range(5):db.add(Attempt(user_id=uid,task_id='item',answer='8',is_correct=False,difficulty_at_time=5))
        await db.commit()
    for path in ['student','ai/student-analysis']:
        assert (await c.get(f'/api/v1/teacher/{path}/{users[1].id}')).status_code==404
        assert (await c.get(f'/api/v1/teacher/{path}/{users[0].id}')).status_code==200
    for path in ['suggestions','ai/difficulty-suggestions']:
        r=await c.get('/api/v1/teacher/'+path);assert r.status_code==200,r.text
        assert all(x['student_id']==users[0].id for x in r.json()['suggestions'])
        assert len(r.json()['suggestions'])==1
    r=await c.get('/api/v1/teacher/ai/intervention-plan');assert r.status_code==200,r.text
    assert all(x['student_id']==users[0].id for k in ['urgent','monitor','challenge'] for x in r.json()[k])
    analysis=await c.get('/api/v1/teacher/ai/classroom-analysis');assert analysis.status_code==200,analysis.text
    assert analysis.json()['difficulty_distribution']=={'5':5}
    r=await c.get('/api/v1/teacher/alerts');assert [x['student_id'] for x in r.json()]==[users[0].id]
    assert (await c.post(f'/api/v1/teacher/alerts/alert-{users[1].id}/resolve')).status_code==404
    assert (await c.post('/api/v1/teacher/ai/adjust-difficulty',json={'student_id':users[1].id,'new_difficulty':8})).status_code==404
    assert (await c.post('/api/v1/teacher/ai/adjust-difficulty',json={'student_id':users[0].id,'new_difficulty':99})).status_code==422
    async with factory() as db:
        assert not (await db.get(Alert,f'alert-{users[1].id}')).is_resolved
        assert (await db.get(User,users[1].id)).difficulty_bias==0
    assert (await c.post(f'/api/v1/teacher/alerts/alert-{users[0].id}/resolve')).status_code==200
    assert (await c.post('/api/v1/teacher/ai/adjust-difficulty',json={'student_id':users[0].id,'new_difficulty':8})).status_code==200
    async with factory() as db:assert (await db.get(User,users[0].id)).difficulty_bias==3
    teacher.role=UserRole.ADMIN
    assert (await c.get(f'/api/v1/teacher/student/{users[1].id}')).status_code==200
