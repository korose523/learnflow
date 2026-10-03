#!/bin/sh
# run_local_e1a_full.sh —— 全量 212 题 E1-A 协议保真度验证（自启自停 Ollama）
#
# 为什么必须写成单个脚本：
#   本机（Windows / Git Bash）下，工具调用结束时其进程组会被回收，
#   因此 `ollama serve &` 与后续 Python 跑批必须**在同一次调用内**完成，
#   否则 serve 会在调用结束瞬间被杀，跑批拿到 HTTP 000 / 502。
#
# 本脚本：start serve -> 健康检查 -> 跑 E1-A 全量 -> kill serve（trap 保证异常也回收）
#
# 用法：sh run_local_e1a_full.sh

set -u
cd /e/learnflow/results/m3 || exit 1

# 本地回环必须绕过代理，否则被本机 http_proxy 拦成 502/000
export no_proxy=localhost,127.0.0.1
export NO_PROXY=localhost,127.0.0.1
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY 2>/dev/null

OLLAMA="C:/Users/mac/AppData/Local/Programs/Ollama/ollama.exe"
PY="C:/Users/mac/.workbuddy/binaries/python/versions/3.13.12/python.exe"

"$OLLAMA" serve > ollama_serve_full.log 2>&1 &
SERVE_PID=$!
cleanup() { kill "$SERVE_PID" 2>/dev/null; }
trap cleanup EXIT INT TERM

ok=0
i=0
while [ "$i" -lt 90 ]; do
  i=$((i + 1))
  if curl -s --noproxy '*' --max-time 3 http://127.0.0.1:11434/api/tags -o /dev/null 2>/dev/null; then
    ok=1
    echo "[serve] up after ${i}s (pid=${SERVE_PID})"
    break
  fi
  sleep 1
done

if [ "$ok" != "1" ]; then
  echo "[serve] FAILED to become healthy in 90s; aborting"
  echo "[serve] --- tail of ollama_serve_full.log ---"
  tail -n 20 ollama_serve_full.log 2>/dev/null
  exit 1
fi

echo "[serve] /api/tags:"
curl -s --noproxy '*' --max-time 5 http://127.0.0.1:11434/api/tags | head -c 400
echo
echo "[run] starting full E1-A (212 items) ..."
"$PY" local_matrix_e1ab.py \
  --models "qwen36:latest" \
  --conditions E1A \
  --meta-file local_matrix_meta.json
PY_RC=$?
echo "[run] PY_RC=${PY_RC}"
cleanup
trap - EXIT INT TERM
echo "[done] serve stopped; batch finished with rc=${PY_RC}"
exit "$PY_RC"
