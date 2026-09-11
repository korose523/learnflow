#!/usr/bin/env bash
# LearnFlow 真实 HTTP 端到端验证：自陈测量层 + LAI 覆盖度 + 口令轮换
set -u
PY=/e/learnflow/learnflow-backend/.venv/Scripts/python.exe
cd /e/learnflow/learnflow-backend || exit 1
PORT=8021
OUT=/e/learnflow/artifacts

CODEBUDDY_SAFE_DELETE_ENABLED=0 $PY -m uvicorn app.main:app --host 127.0.0.1 --port $PORT \
  --log-level warning > $OUT/e2e_api_v2.log 2>&1 &
BE=$!
c=""
for i in $(seq 1 60); do
  c=$(curl -s -o /dev/null -w '%{http_code}' --noproxy '*' "http://127.0.0.1:$PORT/health" || true)
  [ "$c" = "200" ] && break
  sleep 1
done
echo "backend_ready=$c (port $PORT)"

# 从 .env 读取轮换后的种子口令（避免在脚本里写明文）
SEED_STUDENT_PASSWORD=$($PY -c "import io;print([l.split('=',1)[1].strip() for l in io.open('.env',encoding='utf-8') if l.startswith('SEED_STUDENT_PASSWORD')][0])")
SEED_PARENT_PASSWORD=$($PY -c "import io;print([l.split('=',1)[1].strip() for l in io.open('.env',encoding='utf-8') if l.startswith('SEED_PARENT_PASSWORD')][0])")

B="http://127.0.0.1:$PORT/api/v1"
TOK() { $PY -c "import sys,json;print(json.load(sys.stdin).get('access_token',''))"; }
login() {
  curl -s --noproxy '*' -X POST "$B/auth/login/json" -H 'Content-Type: application/json' \
    -d "{\"email\":\"$1\",\"password\":\"$2\"}"
}
J() { $PY -c "$1"; }

echo "--- [1] 新口令登录 student ---"
ST=$(login student@learnflow.com "$SEED_STUDENT_PASSWORD" | TOK); echo "student_token_len=${#ST}"
echo "--- [2] 已退役口令必须失败（证明轮换生效）---"
# 注意：'Student123!' 是**已退役**的旧演示口令，保留在此仅为负向断言——
# 它必须返回空 token。该值已不在任何配置中生效，不构成可用凭据。
OLD=$(login student@learnflow.com 'Student123!' | TOK); echo "old_password_token_len=${#OLD} (期望 0)"
echo "--- [3] 新口令登录 parent ---"
PT=$(login parent_student@learnflow.com "$SEED_PARENT_PASSWORD" | TOK); echo "parent_token_len=${#PT}"

echo "--- [4] GET /instruments ---"
curl -s --noproxy '*' "$B/instruments" -H "Authorization: Bearer $ST" \
 | J "import sys,json;d=json.load(sys.stdin);print('count=',d['count'],'codes=',[i['code'] for i in d['instruments']])"
echo "--- [5] GET /instruments/catalog 指纹 ---"
curl -s --noproxy '*' "$B/instruments/catalog" -H "Authorization: Bearer $ST" \
 | J "import sys,json;print('fingerprint=',json.load(sys.stdin)['fingerprint'])"
echo "--- [6] coverage 提交前 ---"
curl -s --noproxy '*' "$B/instruments/me/coverage" -H "Authorization: Bearer $ST" \
 | J "import sys,json;d=json.load(sys.stdin);print('measured=',d['measured'],'unmeasured=',d['unmeasured'],'weight_basis=',d['weight_basis'],'complete=',d['complete'])"
echo "--- [7] LAI dashboard 提交前 ---"
curl -s --noproxy '*' "$B/student/gamification/lai/dashboard" -H "Authorization: Bearer $ST" \
 | J "import sys,json;d=json.load(sys.stdin);print('overall=',d['overall_score'],'tier=',d['risk_tier']);print('coverage=',d.get('coverage'));print('measurement.weight_basis=',d.get('measurement',{}).get('weight_basis'));print('control.measured=',d['dimensions']['control']['measured'],'function.measured=',d['dimensions']['function']['measured'])"

echo "--- [8] POST 提交 SRL-STOP ---"
curl -s --noproxy '*' -X POST "$B/instruments/SRL-STOP/responses" -H "Authorization: Bearer $ST" \
 -H 'Content-Type: application/json' -d '{"answers":[3,2,4]}' \
 | J "import sys,json;d=json.load(sys.stdin);print('saved=',d['saved'],'lai_input=',d['lai_input'],'lai_value=',d['lai_value']);print('coverage.measured=',d['coverage']['measured'],'weight_basis=',d['coverage']['weight_basis'])"
echo "--- [9] coverage 提交后 ---"
curl -s --noproxy '*' "$B/instruments/me/coverage" -H "Authorization: Bearer $ST" \
 | J "import sys,json;d=json.load(sys.stdin);print('measured=',d['measured'],'weight_basis=',d['weight_basis']);print('lai_inputs=',d['lai_inputs'])"
echo "--- [10] LAI dashboard 提交后（control 参与计分）---"
curl -s --noproxy '*' "$B/student/gamification/lai/dashboard" -H "Authorization: Bearer $ST" \
 | J "import sys,json;d=json.load(sys.stdin);print('overall=',d['overall_score'],'tier=',d['risk_tier']);print('control.measured=',d['dimensions']['control']['measured'],'control.weighted=',d['dimensions']['control']['weighted_score']);print('measurement.weight_basis=',d.get('measurement',{}).get('weight_basis'))"

echo "--- [11] 提交 sleep+social → function 转 measured ---"
curl -s --noproxy '*' -X POST "$B/instruments/SLEEP-IMPACT/responses" -H "Authorization: Bearer $ST" \
 -H 'Content-Type: application/json' -d '{"answers":[5,5,4,5]}' > /dev/null
curl -s --noproxy '*' -X POST "$B/instruments/SOCIAL-IMPACT/responses" -H "Authorization: Bearer $ST" \
 -H 'Content-Type: application/json' -d '{"answers":[4,5,4,5]}' > /dev/null
curl -s --noproxy '*' "$B/instruments/me/coverage" -H "Authorization: Bearer $ST" \
 | J "import sys,json;d=json.load(sys.stdin);print('measured=',d['measured'],'weight_basis=',d['weight_basis'])"
echo "--- [12] LAI dashboard 终态（高睡眠/社交损害应压低 overall）---"
curl -s --noproxy '*' "$B/student/gamification/lai/dashboard" -H "Authorization: Bearer $ST" \
 | J "import sys,json;d=json.load(sys.stdin);print('overall=',d['overall_score'],'tier=',d['risk_tier']);si=d['dimensions']['function']['sub_indicators'];print('sleep_impact=',si.get('sleep_impact'));print('social_impact=',si.get('social_impact'))"

echo "--- [13] 错误路径 ---"
echo "  越界 answers -> $(curl -s -o /dev/null -w '%{http_code}' --noproxy '*' -X POST "$B/instruments/SRL-STOP/responses" -H "Authorization: Bearer $ST" -H 'Content-Type: application/json' -d '{"answers":[9,1,1]}') (期望 400)"
echo "  未知量表     -> $(curl -s -o /dev/null -w '%{http_code}' --noproxy '*' -X POST "$B/instruments/NOPE/responses" -H "Authorization: Bearer $ST" -H 'Content-Type: application/json' -d '{"answers":[1]}') (期望 404)"
echo "  未知维度     -> $(curl -s -o /dev/null -w '%{http_code}' --noproxy '*' "$B/instruments?dimension=nope" -H "Authorization: Bearer $ST") (期望 400)"
echo "  未授权       -> $(curl -s -o /dev/null -w '%{http_code}' --noproxy '*' "$B/instruments/me/coverage") (期望 401)"
echo "--- [14] 既有端点回归 ---"
echo "  leaderboard -> $(curl -s -o /dev/null -w '%{http_code}' --noproxy '*' "$B/student/gamification/leaderboard" -H "Authorization: Bearer $ST") (期望 200)"
echo "  children    -> $(curl -s -o /dev/null -w '%{http_code}' --noproxy '*' "$B/parent/children" -H "Authorization: Bearer $PT") (期望 200)"

kill $BE 2>/dev/null
echo "DONE"
