"""Run browser acceptance on owned local servers and a disposable SQLite DB."""
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import socket
import subprocess
import tempfile
import sqlite3
from datetime import datetime, timedelta, UTC
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]

def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]

def ready(url, process):
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f'Service exited with {process.returncode}; inspect saved service logs')
        try:
            with urlopen(url, timeout=2) as response:
                if response.status == 200: return
        except Exception:
            time.sleep(.25)
    raise TimeoutError(f'Local service did not become ready: {url}')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', default=shutil.which('python3'))
    parser.add_argument('--node', default=shutil.which('node'))
    parser.add_argument('--chrome', help='Existing Chromium/Chrome executable; otherwise use Playwright installed browser')
    parser.add_argument('--node-path', help='Node modules directory containing playwright')
    parser.add_argument('--output', required=True)
    parser.add_argument('--scenario', choices=['content_learning','reviews'], default='content_learning')
    args = parser.parse_args()
    if not args.python or not args.node: parser.error('Python and Node executables are required')
    out = Path(args.output).resolve(); out.mkdir(parents=True, exist_ok=True)
    backend_port, frontend_port = free_port(), free_port()
    while frontend_port == backend_port: frontend_port = free_port()
    password = secrets.token_urlsafe(24)
    processes = []
    with tempfile.TemporaryDirectory(prefix='learnflow-acceptance-') as temporary:
        env = {**os.environ, 'DATABASE_URL':f'sqlite+aiosqlite:///{temporary}/runtime.sqlite', 'ENVIRONMENT':'development', 'DEBUG':'false', 'DEMO_DATA_ENABLED':'true', 'JWT_SECRET_KEY':secrets.token_hex(32), 'ALLOWED_ORIGINS':json.dumps([f'http://127.0.0.1:{frontend_port}']), 'PORT':str(backend_port)}
        for role in ['ADMIN','TEACHER','STUDENT','PARENT']: env[f'SEED_{role}_PASSWORD'] = password
        ui = f'http://127.0.0.1:{frontend_port}'; api = f'http://127.0.0.1:{backend_port}/api/v1'
        with (out/'backend.log').open('w') as backend_log, (out/'frontend.log').open('w') as frontend_log:
            try:
                backend = subprocess.Popen([args.python,'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(backend_port)],cwd=ROOT/'learnflow-backend',env=env,stdout=backend_log,stderr=subprocess.STDOUT,start_new_session=True); processes.append(backend)
                frontend_env = {**os.environ,'VITE_API_BASE':api}
                frontend = subprocess.Popen([args.node,'node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',str(frontend_port),'--strictPort'],cwd=ROOT/'learnflow-frontend',env=frontend_env,stdout=frontend_log,stderr=subprocess.STDOUT,start_new_session=True); processes.append(frontend)
                ready(api.removesuffix('/api/v1')+'/docs',backend); ready(ui,frontend)
                if args.scenario == 'reviews':
                    # Only the freshly owned temporary DB receives technical fixtures.
                    with sqlite3.connect(Path(temporary)/'runtime.sqlite') as connection:
                        student_id = connection.execute("SELECT id FROM users WHERE email=?", ('student@learnflow.com',)).fetchone()[0]
                        stamp = datetime.now(UTC).replace(tzinfo=None)
                        connection.execute("INSERT INTO tasks (id,title,content,topic,difficulty,correct_answer,explanation,source,is_approved,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)", ('acceptance-review-task','Review fixture','求解 $$x+3=10$$。','review-fixture',5,'7','两边减去3，得到 $$x=7$$。','acceptance_fixture',1,stamp.isoformat(sep=' ')))
                        connection.execute("INSERT INTO spaced_reviews (id,user_id,task_id,review_number,scheduled_date,next_interval_days,created_at) VALUES (?,?,?,?,?,?,?)", ('acceptance-review-row',student_id,'acceptance-review-task',1,(stamp-timedelta(days=1)).isoformat(sep=' '),1,stamp.isoformat(sep=' ')))
                test_env = {**os.environ,'ACCEPTANCE_UI_URL':ui,'ACCEPTANCE_API_URL':api,'ACCEPTANCE_FIXTURE_PASSWORD':password,'ACCEPTANCE_OUTPUT':str(out)}
                if args.chrome: test_env['ACCEPTANCE_CHROME'] = args.chrome
                if args.node_path: test_env['NODE_PATH'] = args.node_path
                with (out/'browser.log').open('w') as browser_log:
                    completed = subprocess.run([args.node,str(ROOT/'scripts/acceptance'/f'{args.scenario}.cjs')],cwd=ROOT,env=test_env,stdout=browser_log,stderr=subprocess.STDOUT,timeout=300)
                if completed.returncode: raise RuntimeError(f'Browser acceptance failed; inspect browser.log and {args.scenario}_results.json')
                print(f'Acceptance passed; evidence: {out}')
            finally:
                for process in reversed(processes):
                    if process.poll() is None: os.killpg(process.pid,signal.SIGTERM)
                for process in processes:
                    try: process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid,signal.SIGKILL); process.wait()

if __name__ == '__main__': main()
