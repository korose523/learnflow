#!/bin/sh
# run_local_matrix_finalize.sh —— 收尾：resume 全部已有记录 + 同轮重试失败条目 + 聚合 + 导出矩阵 CSV
#
# 为什么单独一个脚本（而不是改 run_local_e1a_full.sh）：
#   bash 是**增量读取**脚本文件的，正在运行的脚本被改写可能破坏其后续执行。
#   故收尾流程另立新文件。
#
# 与 run_local_e1a_full.sh 相同的原因需要自启自停 Ollama：
#   本机在工具调用结束时回收进程组，serve 与跑批必须在同一次调用内完成。
#
# 用法：sh run_local_matrix_finalize.sh [额外参数...]
#   例：sh run_local_matrix_finalize.sh --conditions E1A

set -u
cd /e/learnflow/results/m3 || exit 1

export no_proxy=localhost,127.0.0.1
export NO_PROXY=localhost,127.0.0.1
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY 2>/dev/null

OLLAMA="C:/Users/mac/AppData/Local/Programs/Ollama/ollama.exe"
PY="C:/Users/mac/.workbuddy/binaries/python/versions/3.13.12/python.exe"

"$OLLAMA" serve > ollama_serve_finalize.log 2>&1 &
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
  tail -n 20 ollama_serve_finalize.log 2>/dev/null
  exit 1
fi

echo "[run] finalize: resume + retry + aggregate + dump-matrix"
"$PY" local_matrix_e1ab.py \
  --models "qwen36:latest" \
  --conditions E1A \
  --meta-file local_matrix_meta.json \
  --retry-rounds 2 \
  --dump-matrix \
  "$@"
PY_RC=$?
echo "[run] PY_RC=${PY_RC}"

cleanup
trap - EXIT INT TERM
echo "[done] serve stopped; finalize finished with rc=${PY_RC}"
exit "$PY_RC"
