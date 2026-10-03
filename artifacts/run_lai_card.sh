#!/usr/bin/env bash
# 单次调用内：起后端(8000) + 前端(5173) → 跑 playwright 验证 → 收尾
set -u
# 仓库根：默认按脚本位置推导（<root>/artifacts/..），可用 LEARNFLOW_ROOT 覆盖
: "${LEARNFLOW_ROOT:=$(cd "$(dirname "$0")/.." && pwd)}"
# 内部工具链目录（含 verify_*.mjs 与 node_modules）：公开仓库不含本机路径，须显式传入
: "${NODE_WORKSPACE:=}"
# 原为硬编码本机 node 路径，已移除；默认走 PATH
: "${NODE_BIN:=node}"
export no_proxy="localhost,127.0.0.1" NO_PROXY="localhost,127.0.0.1"
export CODEBUDDY_SAFE_DELETE_ENABLED=0
[ -n "$NODE_WORKSPACE" ] && export NODE_PATH="$NODE_WORKSPACE/node_modules"
PY="$LEARNFLOW_ROOT/learnflow-backend/.venv/Scripts/python.exe"

cd "$LEARNFLOW_ROOT/learnflow-backend" || exit 1
rm -f "$LEARNFLOW_ROOT/artifacts/_fresh.db"
DATABASE_URL="sqlite+aiosqlite:///$(cd "$LEARNFLOW_ROOT" && pwd -W)/artifacts/_fresh.db" DEMO_DATA_ENABLED=true "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 \
  --log-level warning > "$LEARNFLOW_ROOT/artifacts/_be.log" 2>&1 &
BE=$!
cd "$LEARNFLOW_ROOT/learnflow-frontend" || exit 1
npm run dev > "$LEARNFLOW_ROOT/artifacts/_fe.log" 2>&1 &
FE=$!

for i in $(seq 1 70); do
  c1=$(curl -s -o /dev/null -w '%{http_code}' --noproxy '*' http://127.0.0.1:8000/health || true)
  c2=$(curl -s -o /dev/null -w '%{http_code}' --noproxy '*' http://localhost:5173/ || true)
  [ "$c1" = "200" ] && [ "$c2" = "200" ] && break
  sleep 1
done
echo "backend=$c1 frontend=$c2"

cd "${NODE_WORKSPACE:?请设置 NODE_WORKSPACE 指向含 verify_lai_card.mjs 的内部工具链目录}" || exit 1
"$NODE_BIN" verify_lai_card.mjs 2>&1 | tail -30

kill $BE $FE 2>/dev/null
rm -f "$LEARNFLOW_ROOT/artifacts/_be.log" "$LEARNFLOW_ROOT/artifacts/_fe.log" "$LEARNFLOW_ROOT/artifacts/_fresh.db"
echo "CLEANUP_DONE"
