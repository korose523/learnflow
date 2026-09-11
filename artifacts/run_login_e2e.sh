#!/usr/bin/env bash
# 单次调用内：起后端(8000) + 前端(5173) → 跑 playwright 验证 → 收尾
set -u
export PATH="/c/Users/mac/.workbuddy/binaries/node/versions/22.22.2-3:$PATH"
export no_proxy="localhost,127.0.0.1" NO_PROXY="localhost,127.0.0.1"
export CODEBUDDY_SAFE_DELETE_ENABLED=0
export NODE_PATH="/c/Users/mac/.workbuddy/binaries/node/workspace/node_modules"
PY=/e/learnflow/learnflow-backend/.venv/Scripts/python.exe

cd /e/learnflow/learnflow-backend || exit 1
DEMO_DATA_ENABLED=true $PY -m uvicorn app.main:app --host 127.0.0.1 --port 8000 \
  --log-level warning > /e/learnflow/artifacts/_be.log 2>&1 &
BE=$!
cd /e/learnflow/learnflow-frontend || exit 1
npm run dev > /e/learnflow/artifacts/_fe.log 2>&1 &
FE=$!

for i in $(seq 1 70); do
  c1=$(curl -s -o /dev/null -w '%{http_code}' --noproxy '*' http://127.0.0.1:8000/health || true)
  c2=$(curl -s -o /dev/null -w '%{http_code}' --noproxy '*' http://localhost:5173/ || true)
  [ "$c1" = "200" ] && [ "$c2" = "200" ] && break
  sleep 1
done
echo "backend=$c1 frontend=$c2"

cd /c/Users/mac/.workbuddy/binaries/node/workspace || exit 1
node verify_login.mjs 2>&1 | tail -30

kill $BE $FE 2>/dev/null
rm -f /e/learnflow/artifacts/_be.log /e/learnflow/artifacts/_fe.log
echo "CLEANUP_DONE"
