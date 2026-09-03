"""埋点回放脚本 (Telemetry Replay) —— 把离线埋点回放到实验中生成摘要

用法:
    python scripts/replay_telemetry.py --experiment-id exp_xxx \\
        --telemetry data/telemetry_sample.jsonl --store artifacts/experiments.json

telemetry JSONL 每行: {"user_id": "u1", "metrics": {"exam_score": 78, "risk_score": 40}}

回放即调用 ``ABTestFramework.record_result``（按确定性哈希自动分组），
随后打印 ``get_experiment_summary``（含 Cohen's d 效应量与健康一票否决判定）。
用于复现论文实验结果、对审稿人开放原始统计链路。
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.services.ab_test_framework import ABTestFramework, JSONFileExperimentStore


def main() -> int:
    ap = argparse.ArgumentParser(description="LearnFlow 埋点回放")
    ap.add_argument("--experiment-id", required=True)
    ap.add_argument("--telemetry", required=True, help="JSONL 埋点文件路径")
    ap.add_argument("--store", required=True, help="实验落库 JSON 路径")
    args = ap.parse_args()

    fw = ABTestFramework(store=JSONFileExperimentStore(args.store))
    exp = fw.get_experiment(args.experiment_id)
    if exp is None:
        print(f"实验不存在: {args.experiment_id}", file=sys.stderr)
        return 1

    n = 0
    with open(args.telemetry, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            user_id = rec["user_id"]
            metrics = rec.get("metrics", {})
            fw.record_result(args.experiment_id, user_id, metrics)
            n += 1

    summary = fw.get_experiment_summary(args.experiment_id)
    out = {
        "replayed_records": n,
        "experiment_id": args.experiment_id,
        "summary": summary,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
