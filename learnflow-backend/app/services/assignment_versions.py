"""Versioned task definitions; no legacy submissions are silently reclassified."""
import hashlib
import json
from sqlalchemy import select
from app.models.curriculum import AssignmentVersion
from app.models.task import Task


async def latest_versions(db, assignment_ids):
    rows = (await db.execute(select(AssignmentVersion).where(
        AssignmentVersion.assignment_id.in_(assignment_ids)).order_by(AssignmentVersion.number.desc()))).scalars().all()
    result = {}
    for row in rows:
        result.setdefault(row.assignment_id, row)
    return result


def snapshot(task):
    return json.loads(json.dumps({key: getattr(task, key) for key in ('id','content','content_type','topic','difficulty',
        'correct_answer','explanation','hint_levels','time_estimate','curriculum_node_id')}))


def new_version(assignment_id, number, tasks):
    items = [snapshot(task) for task in tasks]
    digest = hashlib.sha256(json.dumps(items,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return AssignmentVersion(assignment_id=assignment_id,number=number,tasks=items,sha256=digest)


def snapshot_task(item):
    # Transient object supplies the immutable grading definition; never add it to DB.
    return Task(**item, is_approved=True)


def progress(version, submitted_ids, approved_ids):
    target = {item['id'] for item in version.tasks}
    submitted = target & set(submitted_ids)
    blocked = target - submitted - set(approved_ids)
    state = ('blocked' if blocked else 'submitted' if target and submitted == target
             else 'in_progress' if submitted else 'not_started')
    return {'version_id':version.id,'version_number':version.number,'task_count':len(target),
            'submitted_count':len(submitted),'blocked_task_count':len(blocked),'submission_state':state}
