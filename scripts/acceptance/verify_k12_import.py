from pathlib import Path
import os,tempfile,asyncio,importlib.util,hashlib,json,argparse
root=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description='Verify numeric bank import in a disposable database')
parser.add_argument('--output',required=True)
out=Path(parser.parse_args().output).resolve();out.mkdir(parents=True,exist_ok=True)
async def run():
    with tempfile.TemporaryDirectory(prefix='learnflow-k12-import-') as temporary:
        os.environ.update(DATABASE_URL=f'sqlite+aiosqlite:///{temporary}/import.sqlite',ENVIRONMENT='development',DEMO_DATA_ENABLED='false',DEBUG='false')
        spec=importlib.util.spec_from_file_location('k12_import',root/'scripts/k12/import_numeric_tasks.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        import app.models
        from app.core.database import init_db,AsyncSessionLocal,_get_engine
        from app.models.user import User,UserRole
        from app.models.task import Task
        from sqlalchemy import select,func
        await init_db()
        async with AsyncSessionLocal() as db:
            db.add(User(id='fixture-admin',email='fixture@example.test',name='Fixture',role=UserRole.ADMIN,hashed_password='not-a-real-password'));await db.commit()
        items=module.compatible();await module.apply(items,'fixture-admin')
        async with AsyncSessionLocal() as db:
            count=(await db.execute(select(func.count(Task.id)))).scalar_one()
            approved=(await db.execute(select(func.count(Task.id)).where(Task.is_approved==True))).scalar_one()
        assert count==len(items)>0 and approved==0
        await module.apply(items,'fixture-admin')
        async with AsyncSessionLocal() as db:
            final=(await db.execute(select(func.count(Task.id)))).scalar_one()
        assert final==count
        await _get_engine().dispose()
        (out/'k12_import_results.json').write_text(json.dumps({'compatible_items':len(items),'imported':count,'approved':approved,'count_after_second_import':final,'database':'temporary_disposed','script_sha256':hashlib.sha256((root/'scripts/k12/import_numeric_tasks.py').read_bytes()).hexdigest(),'bank_sha256':hashlib.sha256(module.BANK.read_bytes()).hexdigest(),'scope':'numeric_no_image_format_subset_not_expert_reviewed_or_IRT_calibrated'},indent=2))
asyncio.run(run())
