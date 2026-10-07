"""Authenticated, persisted research sessions; live studies require recorded approval.

This implements an apparatus, not IRB approval, validated calibration or human results.
"""
import csv
import io
import re
import secrets
import hashlib
from datetime import timedelta
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.auth import get_current_user
from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.task import Task
from app.models.research import ResearchStudy, ResearchItem, ResearchParticipant, ResearchAllocation, ResearchSession, ResearchTrial
from app.services.research_study import PHASES, allocated_targets, expected_success, participant_for, allocation_for, owned_session, session_progress, utc, now
from app.services.learning_orchestrator import LearningOrchestrator

router = APIRouter(prefix='/api/v1/research', tags=['研究会话'])


async def research_admin(user: User = Depends(get_current_user)):
    if user.role != UserRole.ADMIN:
        raise HTTPException(403, '需要研究管理员权限')
    return user


class StudyCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    protocol_version: str = Field(min_length=1, max_length=80)
    protocol_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    consent_version: str = Field(min_length=1, max_length=80)
    consent_text: str = Field(min_length=20, max_length=20000)
    mode: Literal['dry_run', 'live'] = 'dry_run'
    topics: list[str] = Field(min_length=4, max_length=4)
    phase_counts: dict[str, int] = Field(default_factory=lambda: {'pretest':10,'practice':40,'posttest':10,'delayed':10})
    practice_seconds: int = Field(default=600, ge=60, le=3600)
    delay_days: int = Field(default=7, ge=7, le=30)

    @model_validator(mode='after')
    def valid_protocol(self):
        if len(set(self.topics)) != 4 or any(not t.strip() or len(t)>100 for t in self.topics):
            raise ValueError('需要四个互异主题')
        if set(self.phase_counts) != set(PHASES) or any(type(v) is not int or v<1 or v>200 for v in self.phase_counts.values()):
            raise ValueError('四阶段各需1至200题')
        return self


class ItemInput(BaseModel):
    task_id: str
    topic: str
    phase: Literal['pretest','practice','posttest','delayed']
    difficulty_elo: float = Field(ge=0, le=4000, allow_inf_nan=False)
    expert_reviewed: bool = False
    calibration_source: str | None = Field(default=None, max_length=200)


class Activate(BaseModel):
    approval_reference: str | None = Field(default=None, max_length=200)
    approval_confirmed: bool = False


class ConsentInput(BaseModel):
    consent_version: str
    accepted: bool
    adult_confirmed: bool


class SessionStart(BaseModel):
    topic: str
    phase: Literal['pretest','practice','posttest','delayed']


class TrialAnswer(BaseModel):
    answer: str = Field(min_length=1, max_length=80)
    response_ms: int = Field(ge=0, le=3600000)


def study_public(study):
    return {'id':study.id,'title':study.title,'protocol_version':study.protocol_version,
            'protocol_hash':study.protocol_hash,'consent_version':study.consent_version,
            'consent_text':study.consent_text,'mode':study.mode,'status':study.status,
            'topics':study.topics,'phases':list(PHASES),'delay_days':study.delay_days}


@router.post('/studies')
async def create_study(req:StudyCreate, admin:User=Depends(research_admin), db:AsyncSession=Depends(get_db)):
    study=ResearchStudy(**req.model_dump(),targets=[.65,.75,.85,.95],allocation_seed=secrets.token_hex(32))
    db.add(study);await db.flush()
    return study_public(study)


@router.get('/studies/{study_id}')
async def get_study(study_id:str, user:User=Depends(get_current_user), db:AsyncSession=Depends(get_db)):
    study=await db.get(ResearchStudy,study_id)
    if study is None:raise HTTPException(404,'研究不存在')
    return study_public(study)


@router.post('/studies/{study_id}/items')
async def add_items(study_id:str, req:list[ItemInput], admin:User=Depends(research_admin), db:AsyncSession=Depends(get_db)):
    study=await db.get(ResearchStudy,study_id)
    if study is None:raise HTTPException(404,'研究不存在')
    if study.status!='draft':raise HTTPException(409,'开放后题库冻结，不可变更')
    if not req or len(req)>1000:raise HTTPException(422,'每批1至1000题')
    existing=(await db.execute(select(ResearchItem).where(ResearchItem.study_id==study_id))).scalars().all()
    ids={i.task_id for i in existing}
    for item in req:
        if item.topic not in study.topics:raise HTTPException(422,'主题不在协议中')
        if item.task_id in ids:raise HTTPException(409,'同题不能跨阶段重复使用')
        task=await db.get(Task,item.task_id)
        if task is None:raise HTTPException(404,'题目不存在')
        if task.topic!=item.topic:raise HTTPException(422,'题目主题不一致')
        ids.add(item.task_id)
        db.add(ResearchItem(study_id=study_id,**item.model_dump()))
    await db.flush()
    return {'added':len(req),'distinct_items':len(ids)}


@router.post('/studies/{study_id}/activate')
async def activate_study(study_id:str, req:Activate, admin:User=Depends(research_admin), db:AsyncSession=Depends(get_db)):
    study=await db.get(ResearchStudy,study_id)
    if study is None:raise HTTPException(404,'研究不存在')
    if study.status!='draft':raise HTTPException(409,'研究已开放')
    items=(await db.execute(select(ResearchItem).where(ResearchItem.study_id==study_id))).scalars().all()
    for topic in study.topics:
        for phase in PHASES:
            pool=[i for i in items if i.topic==topic and i.phase==phase]
            if len(pool)<study.phase_counts[phase]:raise HTTPException(409,f'{topic}/{phase} 题池不足')
    if study.mode=='live':
        from app.core.database import using_fallback_database
        if using_fallback_database():raise HTTPException(409,'数据库已回退，不能开放正式研究')
        if not req.approval_confirmed or not (req.approval_reference or '').strip():
            raise HTTPException(409,'正式研究需要记录真实伦理批准编号与管理员确认')
        if len(items)<300 or any(not i.expert_reviewed or not (i.calibration_source or '').strip() for i in items):
            raise HTTPException(409,'正式题库需至少300题，全部经专家核对并有校准来源')
        study.approval_reference=req.approval_reference.strip()
    study.status='active';await db.flush()
    return study_public(study)


@router.post('/studies/{study_id}/consent')
async def consent(study_id:str, req:ConsentInput, user:User=Depends(get_current_user), db:AsyncSession=Depends(get_db)):
    if user.role!=UserRole.STUDENT:raise HTTPException(403,'仅学生账户可以参与')
    ordinal=(await db.execute(update(ResearchStudy).where(ResearchStudy.id==study_id).values(allocation_cursor=ResearchStudy.allocation_cursor+1).returning(ResearchStudy.allocation_cursor))).scalar_one_or_none()
    study=await db.get(ResearchStudy,study_id,populate_existing=True)
    if study is None:raise HTTPException(404,'研究不存在')
    if study.status!='active':raise HTTPException(409,'研究尚未开放')
    if not req.accepted or not req.adult_confirmed or req.consent_version!=study.consent_version:
        raise HTTPException(422,'需要当前版本同意及成年确认；不支持K12招募')
    participant=(await db.execute(select(ResearchParticipant).where(ResearchParticipant.study_id==study_id,ResearchParticipant.user_id==user.id))).scalar_one_or_none()
    if participant:
        if participant.withdrawn_at:raise HTTPException(409,'已撤回，不能自动重新纳入')
        study.allocation_cursor-=1
        return {'research_id':participant.id,'mode':study.mode}
    ordinal-=1
    participant=ResearchParticipant(study_id=study_id,user_id=user.id,ordinal=ordinal,consent_version=study.consent_version)
    db.add(participant);await db.flush()
    targets=allocated_targets(study.allocation_seed,ordinal,len(study.topics),study.targets)
    for topic,target in zip(study.topics,targets):db.add(ResearchAllocation(participant_id=participant.id,topic=topic,target_success=target))
    await db.flush()
    return {'research_id':participant.id,'mode':study.mode}


@router.post('/studies/{study_id}/withdraw')
async def withdraw(study_id:str,user:User=Depends(get_current_user),db:AsyncSession=Depends(get_db)):
    _,participant=await participant_for(db,study_id,user.id)
    participant.withdrawn_at=now();await db.flush()
    return {'withdrawn':True,'excluded_from_default_export':True}


@router.post('/studies/{study_id}/sessions')
async def start_session(study_id:str,req:SessionStart,user:User=Depends(get_current_user),db:AsyncSession=Depends(get_db)):
    study,participant=await participant_for(db,study_id,user.id)
    await allocation_for(db,participant.id,req.topic)
    existing=(await db.execute(select(ResearchSession).where(ResearchSession.participant_id==participant.id,ResearchSession.topic==req.topic,ResearchSession.phase==req.phase))).scalar_one_or_none()
    if existing:return {'session_id':existing.id,'completed':existing.completed_at is not None,'phase':existing.phase}
    index=PHASES.index(req.phase)
    if index:
        previous=(await db.execute(select(ResearchSession).where(ResearchSession.participant_id==participant.id,ResearchSession.topic==req.topic,ResearchSession.phase==PHASES[index-1]))).scalar_one_or_none()
        if not previous or not previous.completed_at:raise HTTPException(409,'必须先完成前一阶段')
        if req.phase=='delayed' and now()<utc(previous.completed_at)+timedelta(days=study.delay_days):
            raise HTTPException(409,'尚未到延迟测验日期')
    session=ResearchSession(participant_id=participant.id,topic=req.topic,phase=req.phase)
    db.add(session);await db.flush()
    return {'session_id':session.id,'completed':False,'phase':session.phase}


@router.get('/sessions/{session_id}/next')
async def next_trial(session_id:str,user:User=Depends(get_current_user),db:AsyncSession=Depends(get_db)):
    study,participant,session=await owned_session(db,session_id,user.id)
    trials,answered=await session_progress(db,session)
    if session.completed_at:return {'complete':True,'phase':session.phase}
    pending=next((t for t in trials if t.submitted_at is None),None)
    elapsed=(now()-utc(session.started_at)).total_seconds()
    if pending is None and (len(answered)>=study.phase_counts[session.phase] or (session.phase=='practice' and elapsed>=study.practice_seconds)):
        session.completed_at=now();await db.flush()
        return {'complete':True,'phase':session.phase,'answered':len(answered)}
    allocation=await allocation_for(db,participant.id,session.topic)
    if pending is None:
        items=(await db.execute(select(ResearchItem).where(ResearchItem.study_id==study.id,ResearchItem.topic==session.topic,ResearchItem.phase==session.phase))).scalars().all()
        seen={t.task_id for t in trials};items=[i for i in items if i.task_id not in seen]
        if not items:raise HTTPException(409,'题池已用尽；不能复用测试或练习题')
        if session.phase=='practice':
            item=min(items,key=lambda i:(abs(expected_success(allocation.ability_elo,i.difficulty_elo)-allocation.target_success),i.task_id))
        else:
            item=min(items,key=lambda i:hashlib.sha256(f'{participant.id}:{session.phase}:{i.task_id}'.encode()).hexdigest())
        pending=ResearchTrial(session_id=session.id,task_id=item.task_id,sequence=len(trials),predicted_success=expected_success(allocation.ability_elo,item.difficulty_elo),ability_before=allocation.ability_elo,item_difficulty_elo=item.difficulty_elo)
        db.add(pending);await db.flush()
    task=await db.get(Task,pending.task_id)
    return {'complete':False,'trial_id':pending.id,'phase':session.phase,'progress':len(answered),
            'total':study.phase_counts[session.phase],'task':{'id':task.id,'content':task.content,'topic':task.topic},
            'mode':study.mode}


@router.post('/trials/{trial_id}/answer')
async def answer_trial(trial_id:str,req:TrialAnswer,user:User=Depends(get_current_user),db:AsyncSession=Depends(get_db)):
    trial=await db.get(ResearchTrial,trial_id,with_for_update=True)
    if trial is None:raise HTTPException(404,'题次不存在')
    study,participant,session=await owned_session(db,trial.session_id,user.id)
    await db.refresh(trial)
    if trial.submitted_at:
        if __import__('unicodedata').normalize('NFKC',req.answer).strip()!=trial.answer:raise HTTPException(409,'此题已提交，不能更改首答')
        return {'recorded':True,'is_correct':trial.is_correct if session.phase=='practice' else None,'replayed':True}
    if session.completed_at:raise HTTPException(409,'会话已结束')
    task=await db.get(Task,trial.task_id)
    # This first apparatus supports bounded numeric mathematics answers only;
    # names, contact details and arbitrary expressions are not exported as answers.
    import unicodedata
    value=unicodedata.normalize('NFKC',req.answer).strip()
    if not re.fullmatch(r'(?:[a-zA-Z]\s*=\s*)?[+\-−]?(?:\d+(?:[.,]\d+)?|[.,]\d+)(?:\s*/\s*[+\-−]?\d+(?:[.,]\d+)?)?',value):
        raise HTTPException(422,'请填写数值、分数或单变量等式答案')
    trial.answer=value;trial.submitted_at=now()
    trial.is_correct=LearningOrchestrator._compare_answer(req.answer,task.correct_answer)
    trial.response_ms=req.response_ms
    trial.server_elapsed_ms=max(0,round((utc(trial.submitted_at)-utc(trial.issued_at)).total_seconds()*1000))
    allocation=await allocation_for(db,participant.id,session.topic)
    if session.phase in ('pretest','practice'):
        allocation.ability_elo=max(0.,min(4000.,allocation.ability_elo+32.*(int(trial.is_correct)-trial.predicted_success)))
    await db.flush()
    return {'recorded':True,'is_correct':trial.is_correct if session.phase=='practice' else None,'replayed':False}


@router.get('/studies/{study_id}/export.csv')
async def export_study(study_id:str,admin:User=Depends(research_admin),db:AsyncSession=Depends(get_db)):
    study=await db.get(ResearchStudy,study_id)
    if study is None:raise HTTPException(404,'研究不存在')
    records=(await db.execute(select(ResearchTrial,ResearchSession,ResearchParticipant,ResearchAllocation).join(ResearchSession,ResearchTrial.session_id==ResearchSession.id).join(ResearchParticipant,ResearchSession.participant_id==ResearchParticipant.id).join(ResearchAllocation,(ResearchAllocation.participant_id==ResearchParticipant.id)&(ResearchAllocation.topic==ResearchSession.topic)).where(ResearchParticipant.study_id==study_id,ResearchParticipant.withdrawn_at.is_(None),ResearchTrial.submitted_at.is_not(None)).order_by(ResearchParticipant.id,ResearchTrial.submitted_at))).all()
    fields=['study_id','protocol_version','protocol_hash','mode','research_id','topic','phase','target_success','trial_id','task_id','answer','is_correct','response_ms','server_elapsed_ms','predicted_success','ability_before','item_difficulty_elo','issued_at','submitted_at','consent_version','consented_at']
    output=io.StringIO();writer=csv.DictWriter(output,fieldnames=fields,lineterminator='\n');writer.writeheader()
    for trial,session,p,a in records:
        row={'study_id':study.id,'protocol_version':study.protocol_version,'protocol_hash':study.protocol_hash,'mode':study.mode,'research_id':p.id,'topic':session.topic,'phase':session.phase,'target_success':a.target_success,'trial_id':trial.id,'task_id':trial.task_id,'answer':trial.answer,'is_correct':int(trial.is_correct),'response_ms':trial.response_ms,'server_elapsed_ms':trial.server_elapsed_ms,'predicted_success':trial.predicted_success,'ability_before':trial.ability_before,'item_difficulty_elo':trial.item_difficulty_elo,'issued_at':utc(trial.issued_at).isoformat(),'submitted_at':utc(trial.submitted_at).isoformat(),'consent_version':p.consent_version,'consented_at':utc(p.consented_at).isoformat()}
        # Spreadsheet formula protection without deleting mathematical answers.
        writer.writerow({k:('\''+v if isinstance(v,str) and v.startswith(('=','+','-','@')) else v) for k,v in row.items()})
    return Response(output.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="research_trials.csv"'})
