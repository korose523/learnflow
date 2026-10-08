"""Immutable assignment definitions and explicit version-bound submissions."""
from sqlalchemy import select, func
from test_review_workflow import review_app
from app.models.user import User, UserRole
from app.models.task import Task, Attempt
from app.models.curriculum import Class, Subject, GradeLevel, CurriculumNode, AssignmentVersion, AssignmentVersionResponse


async def test_assignment_version_freezes_definition_and_separates_reassignment(review_app):
    c,selected,users,factory=review_app
    teacher=User(id='version-teacher',email='version-teacher@example.test',name='Teacher',hashed_password='fixture',role=UserRole.TEACHER)
    async with factory() as db:
        db.add_all([teacher,Subject(id='vs',name='Math',code='vm'),GradeLevel(id='vg',code='VG',label='VG')]);await db.flush()
        db.add_all([Class(id='vc',name='Version class',teacher_id=teacher.id,grade_id='vg'),CurriculumNode(id='vn',subject_id='vs',grade_id='vg',title='Version node')]);await db.flush()
        (await db.get(User,users[0].id)).class_id='vc'
        (await db.get(Task,'item')).curriculum_node_id='vn'
        await db.commit()
    selected['user']=teacher
    payload={'class_id':'vc','node_ids':['vn'],'due_at':'2026-12-01T00:00:00+00:00'}
    created=await c.post('/api/v1/teacher/assignments',json=payload)
    assert created.status_code==200,created.text
    aid=created.json()['assignment_id']
    selected['user']=users[0]
    before=(await c.get(f'/api/v1/student/assignments/{aid}/tasks')).json()
    vid=before['version_id'];assert before['task_count']==1 and before['submission_state']=='not_started'
    assert 'correct_answer' not in str(before) and 'explanation' not in str(before)
    async with factory() as db:
        original=await db.get(Task,'item');original.content='Changed live question';original.correct_answer='99';original.explanation='New explanation'
        db.add(Task(id='new-item',content='Newly added task',topic='algebra',difficulty=5,correct_answer='2',is_approved=True,curriculum_node_id='vn'))
        await db.commit()
    frozen=(await c.get(f'/api/v1/student/assignments/{aid}/tasks')).json()
    assert frozen['total']==1 and frozen['tasks'][0]['content']=='Solve x+3=10'
    assert (await c.post(f'/api/v1/student/assignments/{aid}/answer',json={'task_id':'item','answer':'7'})).status_code==409
    answer=await c.post(f'/api/v1/student/assignments/{aid}/answer',json={'task_id':'item','answer':'7','version_id':vid})
    assert answer.status_code==200,answer.text
    assert answer.json()['is_correct'] is True and answer.json()['submission_state']=='submitted'
    listing=(await c.get('/api/v1/student/assignments')).json()['assignments'][0]
    assert listing['task_count']==1 and listing['submitted_count']==1 and listing['submission_state']=='submitted'
    selected['user']=teacher
    results=(await c.get(f'/api/v1/teacher/assignments/{aid}/results')).json()
    assert results['version_number']==1 and results['students'][0]['submission_state']=='submitted'
    assert (await c.post('/api/v1/teacher/assignments',json=payload)).status_code==200
    async with factory() as db:
        assert (await db.execute(select(func.count(AssignmentVersion.id)))).scalar_one()==1
    payload['new_version']=True
    assert (await c.post('/api/v1/teacher/assignments',json=payload)).status_code==200
    history=(await c.get(f'/api/v1/teacher/assignments/{aid}/versions')).json()['versions']
    assert [v['number'] for v in history]==[2,1]
    historical=(await c.get(f'/api/v1/teacher/assignments/{aid}/results',params={'version_id':vid})).json()
    assert historical['version_number']==1 and historical['students'][0]['submitted_count']==1
    assert (await c.get(f'/api/v1/teacher/assignments/{aid}/results?version_id=missing')).status_code==404
    selected['user']=users[0]
    latest=(await c.get(f'/api/v1/student/assignments/{aid}/tasks')).json()
    assert latest['version_number']==2 and latest['task_count']==2 and latest['submitted_count']==0
    assert latest['version_id']!=vid
    assert (await c.post(f'/api/v1/student/assignments/{aid}/answer',json={'task_id':'item','answer':'7','version_id':vid})).status_code==409
    response=await c.post(f'/api/v1/student/assignments/{aid}/answer',json={'task_id':'item','answer':'99','version_id':latest['version_id']})
    assert response.status_code==200,response.text
    assert response.json()['is_correct'] is True and response.json()['submission_state']=='in_progress'
    assert (await c.post(f'/api/v1/student/assignments/{aid}/answer',json={'task_id':'item','answer':'99','version_id':latest['version_id']})).status_code==409
    async with factory() as db:
        (await db.get(Task,'new-item')).is_approved=False;await db.commit()
        assert (await db.execute(select(func.count(AssignmentVersionResponse.id)))).scalar_one()==2
        assert (await db.execute(select(func.count(Attempt.id)))).scalar_one()==2
        versions=(await db.execute(select(AssignmentVersion).order_by(AssignmentVersion.number))).scalars().all()
        assert versions[0].tasks[0]['correct_answer']=='7' and versions[1].sha256!=versions[0].sha256
    blocked=(await c.get(f'/api/v1/student/assignments/{aid}/tasks')).json()
    assert blocked['submission_state']=='blocked' and blocked['blocked_task_count']==1 and blocked['task_count']==2
    assert (await c.post(f'/api/v1/student/assignments/{aid}/answer',json={'task_id':'new-item','answer':'2','version_id':latest['version_id']})).status_code==409
