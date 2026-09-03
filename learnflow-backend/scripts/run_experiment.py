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


def run(spec: dict, store_path: str, advance_to: str | None = None,
        off_category: str | None = None, force: bool = False) -> dict:
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

    # GAP-1: 类别级消融预设 —— --off-category 合并「整类机制 = False」
    toggles = _parse_toggles(spec.get("mechanism_toggles", "{}"))
    if off_category:
        toggles.update(fw.toggles_for_category(off_category))

    exp = fw.create_experiment(
        name=spec["name"],
        description=spec.get("description", ""),
        parameter_name=spec.get("parameter_name", ""),
        control_value=spec.get("control_value"),
        treatment_value=spec.get("treatment_value"),
        mechanism_toggles=toggles,
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

    # GAP-7: --advance-to 默认尊重真实样本量门槛 (required_n_per_group)；
    # 仅 --force 时强制推进（绕过门槛，便于演示/编排）。
    if advance_to:
        order = ["shadow", "canary", "ramping", "full"]
        target = order.index(advance_to)
        cur = order.index(exp.phase.value)
        while cur < target:
            prev = exp.phase
            fw.advance_phase(exp.id, force=force)
            exp = fw.get_experiment(exp.id)
            if order.index(exp.phase.value) == cur:
                # 未推进（门槛未达且非强制）：停止，避免死循环
                if not force:
                    print(
                        f"[warn] 阶段推进在 {prev.value} 处被样本量门槛拦截"
                        f"(需 >= required_n_per_group={exp.required_n_per_group})；"
                        f"使用 --force 可强制推进。",
                        file=sys.stderr,
                    )
                break
            cur = order.index(exp.phase.value)

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
    ap.add_argument("--off-category", default=None,
                    help="消融预设：关闭一整类机制 (A–H 或注册表类别名，如 retention)")
    ap.add_argument("--advance-to", default=None,
                    choices=["shadow", "canary", "ramping", "full"])
    ap.add_argument("--force", action="store_true",
                    help="--advance-to 强制推进，忽略真实样本量门槛 (required_n_per_group)")
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

    result = run(spec, args.store, args.advance_to, args.off_category, args.force)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
