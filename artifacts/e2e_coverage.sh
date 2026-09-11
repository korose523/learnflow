#!/usr/bin/env bash
# 干净数据库上的覆盖度递进验证：0.55 → 0.80 → 0.90 → 1.00
# 目的：证明「未测维度不计分、补测后逐级纳入」在真实 HTTP 上成立。
set -u
cd /e/learnflow/learnflow-backend || exit 1
PY=/e/learnflow/learnflow-backend/.venv/Scripts/python.exe
PORT=8031
DB=E:/learnflow/artifacts/e2e_clean.db
OUT=/e/learnflow/artifacts

rm -f /e/learnflow/artifacts/e2e_clean.db
# 从 .env 取种子口令与种子开关，避免在脚本中写明文
SEED_STUDENT_PASSWORD=$($PY -c "import io;print([l.split('=',1)[1].strip() for l in io.open('.env',encoding='utf-8') if l.startswith('SEED_STUDENT_PASSWORD')][0])")

DATABASE_URL="sqlite+aiosqlite:///$DB" \
DEMO_DATA_ENABLED=true \
SEED_STUDENT_PASSWORD="$SEED_STUDENT_PASSWORD" \
SEED_TEACHER_PASSWORD="x-Teacher-Placeholder-1" \
SEED_PARENT_PASSWORD="x-Parent-Placeholder-1" \
SEED_ADMIN_PASSWORD="x-Admin-Placeholder-1" \
CODEBUDDY_SAFE_DELETE_ENABLED=0 \
$PY -m uvicorn app.main:app --host 127.0.0.1 --port $PORT --log-level warning > "$OUT/e2e_clean.log" 2>&1 &
BE=$!
c=""
for i in $(seq 1 60); do
  c=$(curl -s -o /dev/null -w '%{http_code}' --noproxy '*' "http://127.0.0.1:$PORT/health" || true)
  [ "$c" = "200" ] && break
  sleep 1
done
echo "backend_ready=$c on fresh db=$DB"

B="http://127.0.0.1:$PORT/api/v1"
TOK() { $PY -c "import sys,json;print(json.load(sys.stdin).get('access_token',''))"; }
ST=$(curl -s --noproxy '*' -X POST "$B/auth/login/json" -H 'Content-Type: application/json' \
     -d "{\"email\":\"student@learnflow.com\",\"password\":\"$SEED_STUDENT_PASSWORD\"}" | TOK)
echo "student_token_len=${#ST}"
H="Authorization: Bearer $ST"

cov() {
  curl -s --noproxy '*' "$B/instruments/me/coverage" -H "$H" \
  | $PY -c "import sys,json;d=json.load(sys.stdin);print('    measured=',d['measured']);print('    weight_basis=',d['weight_basis'],' complete=',d['complete'],' missing=',[m['code'] for m in d['missing_instruments']])"
}
dash() {
  curl -s --noproxy '*' "$B/student/gamification/lai/dashboard" -H "$H" \
  | $PY -c "import sys,json;d=json.load(sys.stdin);c=d.get('coverage',{});print('    overall=',d['overall_score'],'tier=',d['risk_tier'],'| coverage.weight_basis=',c.get('weight_basis'),'| unmeasured=',c.get('unmeasured'));print('    measured flags:',{k:v['measured'] for k,v in d['dimensions'].items()})"
}
submit() {
  curl -s --noproxy '*' -X POST "$B/instruments/$1/responses" -H "$H" \
    -H 'Content-Type: application/json' -d "$2" \
  | $PY -c "import sys,json;d=json.load(sys.stdin);print('    submit $1 -> saved=',d.get('saved'),'lai_input=',d.get('lai_input'),'lai_value=',d.get('lai_value'))"
}

echo
echo "=== STEP 0：零自陈数据（期望 weight_basis = 0.55）==="
cov; dash

echo
echo "=== STEP 1：提交 SRL-STOP（期望 control 纳入 → 0.80）==="
submit SRL-STOP '{"answers":[1,0,1]}'; cov; dash

echo
echo "=== STEP 2：提交 SLEEP-IMPACT（仅睡眠，function 仍应未测）==="
submit SLEEP-IMPACT '{"answers":[2,2,2,2]}'; cov

echo
echo "=== STEP 3：提交 SOCIAL-IMPACT（睡眠+社交齐备 → function 纳入 → 0.90）==="
submit SOCIAL-IMPACT '{"answers":[2,2,2,2]}'; cov; dash

echo
echo "=== STEP 4：提交 TIME-BIAS（cognition 纳入 → 1.00 完整）==="
submit TIME-BIAS '{"answers":[2,2,2]}'; cov; dash

echo
echo "=== STEP 5：高损害作答应压低 overall 并触发更差 tier ==="
submit SRL-STOP '{"answers":[5,5,5]}'
submit SLEEP-IMPACT '{"answers":[5,5,5,5]}'
submit SOCIAL-IMPACT '{"answers":[5,5,5,5]}'
submit TIME-BIAS '{"answers":[5,5,5]}'
dash

kill $BE 2>/dev/null
rm -f /e/learnflow/artifacts/e2e_clean.db
echo
echo "DONE"
