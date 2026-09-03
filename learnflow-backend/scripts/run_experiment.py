"""实验运行器 (Experiment Runner) —— 创建实验 + 功效分析预注册 + 阶段推进

用法:
    python scripts/run_experiment.py --spec experiments/my_exp.json
    python scripts/run_experiment.py \
        --name "FOMO 单机制消融" \
        --description "关闭 LF-M44 验证对 retention 的影响" \
        --mechanism-toggles '{"LF-M44": false}' \
        --metric-type continuous --effect-size 0.3 \
        --cluster-size 30 --icc 0.05 --advance-to full

实验数据默认落库到 artifacts/experiments.json (JSONFileExperimentStore)，
满足 §4.2.3「数据落库」与 90 天追踪可复现性要求（生产可换 SQLExperimentStore）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys

# 允许以脚本方式直接运行 (项目根加入 sys.path)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.services.ab_test_framework import (
    ABTestFramework, JSONFileExperimentStore, ExperimentPhase,
)
from app.services.experiment_power import plan_experiment, PowerPlan
from app.services.mechanism_registry import registry_fingerprint


DEFAULT_STORE = os.path.join(ROOT, "artifacts", "experiments.json")


def _parse_toggles(s) -> dict:
    if s is None:
        return {}
    if isinstance(s, dict):
        return s
    if not s:
        return {}
    return json.loads(s)


def run(spec: dict, store_path: str, advance_to: str | None) -> dict:
    fw = ABTestFramework(store=JSONFileExperimentStore(store_path))

    metric_type = spec.get("metric_type", "continuous")
    effect_size = float(spec.get("effect_size", 0.3))
    baseline_rate = float(spec.get("baseline_rate", 0.5))
    alpha = float(spec.get("alpha", 0.05))
    power = float(spec.get("power", 0.80))
    cluster_size = int(spec.get("cluster_size", 30))
    icc = float(spec.get("icc", 0.05))

    plan: PowerPlan = plan_experiment(
        effect_size=effect_size,
        metric_type=metric_type,
        baseline_rate=baseline_rate,
        alpha=alpha, power=power,
        cluster_size=cluster_size, icc=icc,
    )

    exp = fw.create_experiment(
        name=spec["name"],
        description=spec.get("description", ""),
        parameter_name=spec.get("parameter_name", ""),
        control_value=spec.get("control_value"),
        treatment_value=spec.get("treatment_value"),
        mechanism_toggles=_parse_toggles(spec.get("mechanism_toggles", "{}")),
        primary_metric=spec.get("primary_metric", "knowledge_mastery_growth"),
        secondary_metrics=spec.get("secondary_metrics", []),
        alpha_alloc=alpha,
        gate_level=int(spec.get("gate_level", 1)),
        mde=effect_size,
        icc_assumed=icc,
        cluster_randomized=cluster_size > 1,
        registry_fingerprint=registry_fingerprint(),
    )
    fw.set_required_n(exp.id, plan.required_n_per_group, deff=plan.deff)

    if advance_to:
        order = ["shadow", "canary", "ramping", "full"]
        target = order.index(advance_to)
        cur = 0
        # 强制推进到目标（绕过样本量门槛，便于演示/编排）
        while cur < target:
            fw.advance_phase(exp.id, force=True)
            cur += 1

    summary = fw.get_experiment_summary(exp.id)
    return {
        "experiment_id": exp.id,
        "store": store_path,
        "power_plan": plan.to_dict(),
        "experiment": exp.to_dict(),
        "summary": summary,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="LearnFlow 实验运行器")
    ap.add_argument("--spec", help="实验规格 JSON 文件路径")
    ap.add_argument("--store", default=DEFAULT_STORE, help="落库 JSON 路径")
    ap.add_argument("--name", help="实验名称（无 --spec 时必填）")
    ap.add_argument("--description", default="")
    ap.add_argument("--mechanism-toggles", default="{}", help='JSON, 如 \'{"LF-M44": false}\'')
    ap.add_argument("--metric-type", default="continuous", choices=["continuous", "binary"])
    ap.add_argument("--effect-size", type=float, default=0.3)
    ap.add_argument("--baseline-rate", type=float, default=0.5)
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--power", type=float, default=0.80)
    ap.add_argument("--cluster-size", type=int, default=30)
    ap.add_argument("--icc", type=float, default=0.05)
    ap.add_argument("--advance-to", default=None,
                    choices=["shadow", "canary", "ramping", "full"])
    args = ap.parse_args()

    if args.spec:
        with open(args.spec, "r", encoding="utf-8") as f:
            spec = json.load(f)
    else:
        if not args.name:
            ap.error("需提供 --spec 或 --name")
        spec = {
            "name": args.name,
            "description": args.description,
            "mechanism_toggles": args.mechanism_toggles,
            "metric_type": args.metric_type,
            "effect_size": args.effect_size,
            "baseline_rate": args.baseline_rate,
            "alpha": args.alpha,
            "power": args.power,
            "cluster_size": args.cluster_size,
            "icc": args.icc,
        }

    result = run(spec, args.store, args.advance_to)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
