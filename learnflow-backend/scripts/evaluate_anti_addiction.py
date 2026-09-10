#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
evaluate_anti_addiction.py
================================================================================
LearnFlow 学习成瘾化研究 —— 抗成瘾层「计算式评估 / in-silico ablation」

目的（对应论文「系统贡献」章节）
----------------------------------------------------------------------
量化验证两层抗成瘾设计对 LAI（学习成瘾指数, 0-100 越高越健康）的边际提升：
  (1) LF-M54 班级宠物（真实连接替代, Hari C1）—— 通过 connection_quality 缓冲
      动机维度与功能维度；
  (2) 机制仲裁器「LAI 风险自适应降权」（文献补位）—— 高成瘾风险时丢弃高成瘾化
      拉回型 nudge（LF-M44 FOMO / LF-M33 Hook …），衰减 dark-pattern 暴露。

实验设计
----------------------------------------------------------------------
  · 默认：合成队列 N=600 名 K-12 学生（固定随机种子，完全可复现）。
  · 配对反事实（同一队列在三条件下评估，消除个体差异，公平比较）：
      C0 基线        —— 纯参与最大化，无抗成瘾层（arbitrator lai_risk=None）
      C1 班级宠物    —— 仅开启真实连接替代（connection_quality 抬升至 >0.7 阈值）
      C2 全抗成瘾层  —— C1 + 仲裁器按 LAI 风险降权，衰减可变比率/激励敏化/Hook 暴露
  · 仲裁器消融：固定候选 Effect 集，对比 lai_risk=None vs high 的下发差异。

真实脱敏学习日志接入（①）
----------------------------------------------------------------------
本脚本支持用**真实学习日志 CSV** 替代合成队列跑同一套评估，满足「用真实数据复算」
的论文需求：
  --log  PATH        读取真实脱敏学习事件 CSV（表头见 EVENT_HEADER）
  --sample           生成一份「合成脱敏样本日志」(sample_desensitized_log.csv) 后跑通
  --n N / --seed S   合成队列规模 / 种子（默认路径）
  --out  DIR         产物目录（默认 artifacts/evaluation[...]）

事件级 CSV 表头（每行 = 一次学习会话 / 一个行为事件）：
  student_id, grade, session_start, duration_min, is_night, correct, total,
  reward_received, leaderboard_view, intrinsic_choice, peer_interaction,
  sleep_late, overran, variable_reward, reward_craving, trigger_open, belonging
脚本按 student_id 聚合为每位学生的 LAI 特征向量，再进入与合成队列完全相同的
评估管线。真实字段映射与聚合逻辑见 ingest_learning_log()。

声明（重要）
----------------------------------------------------------------------
本评估为「计算式 / 设计验证」(in-silico)，**非田野实验**；用于证明引擎设计按预期
方向移动指标，作为系统型论文（对标 CHI/UIST 系统贡献的 ablation 范式）的机制验证
证据。合成/样本路径的参数分布来自对真实 K-12 游戏化学习产品的合理设定，可供审稿人
复现（种子、分布、公式均写死在本文件）。真实日志路径以 raw 数据为准。

产出（artifacts/evaluation[/_from_log]）
  result.json                  机器可读全量结果
  pap.json                    预分析计划（假设/设计/种子/主结局）
  tables/main_results.csv/.md  场景 × 指标
  tables/risk_distribution.csv 风险等级分布
  figures/lai_by_scenario.svg       各场景平均 LAI 柱状图
  figures/risk_distribution.svg     各场景风险等级堆叠柱状图
  figures/arbitrator_cooling.svg    仲裁器降权前后候选→下发对比
================================================================================
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import statistics
from collections import Counter

from app.services.learning_addiction_index import LearningAddictionIndex, LAIRiskTier
from app.services.class_pet_service import ClassPetService
from app.services.mechanism_arbitrator import MechanismArbitrator, lai_risk_from_overall, BudgetPolicy
from app.services.mechanism_registry import Effect, EffectType, MechanismContext

# —— 复现锚点 ——
SEED = 20260906
N = 600
OUT_DIR = r"E:/learnflow/artifacts/evaluation"
CLASS_COHESION = 78.0          # 班级宠物园聚合出的班级凝聚力（0-100）
CLASS_ACTIVE_RATIO = 0.75      # 班级活跃参与率

# —— 真实学习日志事件表头（①）——每行一个学习会话/行为事件 ——
EVENT_HEADER = [
    "student_id", "grade", "session_start", "duration_min", "is_night",
    "correct", "total", "reward_received", "leaderboard_view",
    "intrinsic_choice", "peer_interaction", "sleep_late", "overran",
    "variable_reward", "reward_craving", "trigger_open", "belonging",
]


def clip(x, lo, hi):
    return max(lo, min(hi, x))


# ───────────────────────── 1. 合成队列 ─────────────────────────
def sample_student(rng: random.Random) -> dict:
    """抽取一名学生的行为 + 文献补位参数（基线，无抗成瘾层干预）。"""
    age = rng.choices(["primary", "secondary", "senior"], weights=[0.35, 0.45, 0.20])[0]
    return dict(
        age_group=age,
        daily_minutes=clip(rng.gauss(105, 45), 30, 260),
        session_minutes=clip(rng.gauss(42, 18), 10, 110),
        night_ratio=clip(rng.gauss(0.12, 0.08), 0.0, 0.45),
        content_attention_ratio=clip(rng.gauss(0.72, 0.18), 0.30, 1.00),
        leaderboard_views=max(0, int(rng.gauss(6, 4))),
        planned_stop_failures=max(0, int(rng.gauss(1.2, 1.4))),
        intrinsic_motivation_ratio=clip(rng.gauss(0.58, 0.18), 0.05, 0.95),
        external_reward_dependency=clip(rng.gauss(0.40, 0.18), 0.0, 0.95),
        time_perception_bias=clip(rng.gauss(0.18, 0.15), 0.0, 0.60),
        sleep_impact=clip(rng.gauss(0.28, 0.18), 0.0, 0.80),
        social_impact=clip(rng.gauss(0.22, 0.16), 0.0, 0.70),
        connection_quality=clip(rng.gauss(0.45, 0.16), 0.10, 0.85),
        variable_ratio_exposure=clip(rng.gauss(0.35, 0.20), 0.0, 0.90),
        incentive_sensitization=clip(rng.gauss(0.28, 0.18), 0.0, 0.85),
        hook_internal_trigger_dependency=clip(rng.gauss(0.26, 0.17), 0.0, 0.85),
    )


# ───────────────────────── 1b. 真实日志接入（①）─────────────────────────
def _grade_to_age(grade: str) -> str:
    g = (grade or "").strip()
    if "小" in g or g in {"1", "2", "3", "4", "5", "6"}:
        return "primary"
    if "初" in g or g in {"7", "8", "9"}:
        return "secondary"
    if "高" in g or g in {"10", "11", "12"}:
        return "senior"
    return "secondary"


def ingest_learning_log(path: str) -> list:
    """读取真实脱敏学习事件 CSV，按 student_id 聚合成与 sample_student 同构的
    特征向量列表。每行字段含义见 EVENT_HEADER。"""
    by_stu = {}
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sid = row["student_id"]
            by_stu.setdefault(sid, []).append(row)

    students = []
    for sid, rows in by_stu.items():
        n = len(rows)
        total_min = sum(float(r["duration_min"]) for r in rows)
        dur_list = [float(r["duration_min"]) for r in rows]
        night = sum(int(r["is_night"]) for r in rows) / n
        acc = []
        for r in rows:
            t = int(r["total"]) if int(r["total"]) > 0 else 0
            acc.append((int(r["correct"]) / t) if t > 0 else 0.7)
        attn = sum(acc) / n
        leaderboard_views = sum(int(r["leaderboard_view"]) for r in rows)
        overran = sum(int(r["overran"]) for r in rows)
        intrinsic = sum(int(r["intrinsic_choice"]) for r in rows) / n
        reward = sum(int(r["reward_received"]) for r in rows) / n
        peer = sum(int(r["peer_interaction"]) for r in rows) / n
        sleep = sum(int(r["sleep_late"]) for r in rows) / n
        vr = sum(int(r["variable_reward"]) for r in rows) / n
        craving = sum(int(r["reward_craving"]) for r in rows) / n
        trig = sum(int(r["trigger_open"]) for r in rows) / n
        belonging = sum(float(r["belonging"]) for r in rows) / n
        students.append(dict(
            age_group=_grade_to_age(rows[0].get("grade", "")),
            daily_minutes=clip(total_min, 30, 260),
            session_minutes=clip(sum(dur_list) / n, 10, 110),
            night_ratio=clip(night, 0.0, 0.45),
            content_attention_ratio=clip(attn, 0.30, 1.00),
            leaderboard_views=leaderboard_views,
            planned_stop_failures=overran,
            intrinsic_motivation_ratio=clip(intrinsic, 0.05, 0.95),
            external_reward_dependency=clip(reward, 0.0, 0.95),
            time_perception_bias=clip(overran / n * 0.3 + 0.1, 0.0, 0.60),
            sleep_impact=clip(sleep, 0.0, 0.80),
            social_impact=clip(peer, 0.0, 0.70),
            connection_quality=clip(belonging * 0.6 + peer * 0.4, 0.10, 0.90),
            variable_ratio_exposure=clip(vr, 0.0, 0.90),
            incentive_sensitization=clip(craving, 0.0, 0.85),
            hook_internal_trigger_dependency=clip(trig, 0.0, 0.85),
        ))
    return students


def generate_sample_learning_log(path: str, n_students: int = 120, seed: int = SEED) -> str:
    """生成一份「合成脱敏样本日志」用于跑通真实日志管线。

    ⚠️ 这是**合成占位数据**，仅用于演示「真实日志接入」通路可运行；
       真实研究请替换为学校导出的脱敏学习事件 CSV（表头见 EVENT_HEADER）。
    """
    rng = random.Random(seed)
    grades = [("primary", "五年级"), ("secondary", "初二"), ("senior", "高一")]
    rows = []
    for i in range(n_students):
        _, g_label = rng.choice(grades)
        k = rng.randint(6, 10)
        for _ in range(k):
            dur = clip(rng.gauss(20, 8), 5, 40)
            night = 1 if rng.random() < clip(rng.gauss(0.12, 0.08), 0, 0.45) else 0
            total = rng.randint(5, 20)
            correct = int(total * clip(rng.gauss(0.72, 0.18), 0.3, 1.0))
            reward = 1 if rng.random() < clip(rng.gauss(0.40, 0.18), 0, 0.95) else 0
            lb = 1 if rng.random() < 0.30 else 0
            intr = 1 if rng.random() < clip(rng.gauss(0.58, 0.18), 0.05, 0.95) else 0
            peer = 1 if rng.random() < clip(rng.gauss(0.45, 0.16), 0, 0.85) else 0
            sleep = 1 if rng.random() < clip(rng.gauss(0.28, 0.18), 0, 0.8) else 0
            overran = 1 if rng.random() < clip(rng.gauss(0.17, 0.15), 0, 0.6) else 0
            vr = 1 if rng.random() < clip(rng.gauss(0.35, 0.20), 0, 0.9) else 0
            craving = 1 if rng.random() < clip(rng.gauss(0.28, 0.18), 0, 0.85) else 0
            trig = 1 if rng.random() < clip(rng.gauss(0.26, 0.17), 0, 0.85) else 0
            belong = clip(rng.gauss(0.45, 0.16), 0.1, 0.85)
            rows.append([
                f"STU{i:04d}", g_label,
                f"2026-03-{rng.randint(1, 28):02d}T{rng.randint(8, 23):02d}:00",
                round(dur, 1), night, correct, total, reward, lb, intr,
                peer, sleep, overran, vr, craving, trig, round(belong, 2),
            ])
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(EVENT_HEADER)
        w.writerows(rows)
    return path


def _assess(s: dict, **overrides) -> object:
    kw = dict(
        daily_minutes=s["daily_minutes"],
        session_minutes=s["session_minutes"],
        night_ratio=s["night_ratio"],
        content_attention_ratio=s["content_attention_ratio"],
        leaderboard_views=s["leaderboard_views"],
        planned_stop_failures=s["planned_stop_failures"],
        intrinsic_motivation_ratio=s["intrinsic_motivation_ratio"],
        external_reward_dependency=s["external_reward_dependency"],
        time_perception_bias=s["time_perception_bias"],
        sleep_impact=s["sleep_impact"],
        social_impact=s["social_impact"],
        connection_quality=s["connection_quality"],
        variable_ratio_exposure=s["variable_ratio_exposure"],
        incentive_sensitization=s["incentive_sensitization"],
        hook_internal_trigger_dependency=s["hook_internal_trigger_dependency"],
        age_group=s["age_group"],
    )
    kw.update(overrides)
    return LearningAddictionIndex.assess(**kw)


# ───────────────────────── 2. 三条件评估 ─────────────────────────
def evaluate_conditions(students: list) -> dict:
    cq_class = ClassPetService.connection_quality_feedback(CLASS_COHESION, CLASS_ACTIVE_RATIO)
    cond = {"C0_baseline": [], "C1_classpet": [], "C2_full": []}

    for s in students:
        a0 = _assess(s)
        cond["C0_baseline"].append(a0)

        # C1: 仅真实连接替代（抬升 connection_quality 至班级宠物回灌值）
        a1 = _assess(s, connection_quality=max(s["connection_quality"], cq_class))
        cond["C1_classpet"].append(a1)

        # C2: C1 + 仲裁器降权 → 衰减 dark-pattern 暴露（按个体 C0 风险比例）
        risk0 = lai_risk_from_overall(a0.overall_score)
        att = 1.0 - 0.5 * clip(risk0, 0.0, 1.0)
        a2 = _assess(
            s,
            connection_quality=max(s["connection_quality"], cq_class),
            variable_ratio_exposure=s["variable_ratio_exposure"] * att,
            incentive_sensitization=s["incentive_sensitization"] * att,
            hook_internal_trigger_dependency=s["hook_internal_trigger_dependency"] * att,
        )
        cond["C2_full"].append(a2)

    return {"cq_class": round(cq_class, 3), "conditions": cond}


def summarize(cond: dict) -> dict:
    overall = [a.overall_score for a in cond]
    dims = {d: [a.dimensions[d].raw_score * 100 for a in cond] for d in
            ["time", "motivation", "control", "cognition", "function"]}
    tiers = Counter(a.risk_tier.name for a in cond)
    return {
        "n": len(cond),
        "mean_lai": round(statistics.mean(overall), 2),
        "median_lai": round(statistics.median(overall), 2),
        "sd_lai": round(statistics.pstdev(overall), 2),
        "dim_means": {d: round(statistics.mean(v), 1) for d, v in dims.items()},
        "tier_counts": {
            "L1_NORMAL": tiers.get("L1_NORMAL", 0),
            "L2_WATCH": tiers.get("L2_WATCH", 0),
            "L3_DEEP": tiers.get("L3_DEEP", 0),
            "L4_PATHOLOGICAL": tiers.get("L4_PATHOLOGICAL", 0),
        },
        "pct_reduce_gamification": round(100 * sum(1 for a in cond if a.should_reduce_gamification) / len(cond), 1),
        "pct_notify_guardian": round(100 * sum(1 for a in cond if a.should_notify_guardian) / len(cond), 1),
    }


# ───────────────────────── 3. 仲裁器消融 ─────────────────────────
def arbitrator_ablation() -> dict:
    """固定候选 Effect 集，对比 lai_risk=None vs high 的下发差异。"""
    specs = [
        ("LF-M44", EffectType.NUDGE, 70),        # FOMO (B4/A4)  addiction_risk 0.9
        ("LF-M33", EffectType.REMINDER, 60),     # Hook (B4)      addiction_risk 0.7
        ("LF-M08", EffectType.NOTIFICATION, 50), # 稀缺性 dark pattern 0.5
        ("LF-M07", EffectType.REWARD, 40),       # 集换收藏 (A8)  0.4
        ("LF-M35", EffectType.PROMPT, 45),       # 情境线索 (B4)  0.4
    ]
    effects = [Effect(mid, et, {}, priority=pr) for mid, et, pr in specs]
    # 消融中放松干预预算（max_per_session 提到 10），以**隔离**「LAI 风险自适应降权」
    # 这一层本身——否则 max_per_session=3 的预算上限会先于降权层截断候选，混淆效果。
    arb = MechanismArbitrator(policy=BudgetPolicy(max_per_session=10, max_per_day=20, max_cost_per_session=20.0))

    none = arb.arbitrate(MechanismContext(user_id="eval", session_id="s1"),
                         [Effect(mid, et, {}, priority=pr) for mid, et, pr in specs],
                         lai_risk=None)
    high = arb.arbitrate(MechanismContext(user_id="eval", session_id="s2"),
                         effects, lai_risk=0.7)

    delivered_none = {e.mechanism_id for e in none}
    delivered_high = {e.mechanism_id for e in high}
    return {
        "candidates": [mid for mid, _, _ in specs],
        "delivered_lai_none": sorted(delivered_none),
        "delivered_lai_high": sorted(delivered_high),
        "dropped_by_risk": sorted(delivered_none - delivered_high),
        "count_none": len(delivered_none),
        "count_high": len(delivered_high),
    }


# ───────────────────────── 4. SVG 图表（纯手写，无外部依赖）─────────────────────────
def _svg_bar(values, labels, title, ylabel, fname, ymax=None, color="#3FA66A"):
    w, h = 560, 340
    ml, mr, mt, mb = 60, 20, 50, 50
    pw, ph = w - ml - mr, h - mt - mb
    if ymax is None:
        ymax = max(values) * 1.15
    n = len(values)
    bw = pw / (n * 1.6)
    gap = bw * 0.6
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" font-family="Segoe UI, sans-serif">']
    parts.append(f'<text x="{w/2}" y="26" text-anchor="middle" font-size="16" font-weight="700" fill="#1f2937">{title}</text>')
    parts.append(f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{mt+ph}" stroke="#9ca3af"/>')
    parts.append(f'<line x1="{ml}" y1="{mt+ph}" x2="{ml+pw}" y2="{mt+ph}" stroke="#9ca3af"/>')
    for i in range(0, 5):
        yv = ymax * i / 4
        yy = mt + ph - ph * (yv / ymax)
        parts.append(f'<text x="{ml-8}" y="{yy+4}" text-anchor="end" font-size="11" fill="#6b7280">{yv:.0f}</text>')
        parts.append(f'<line x1="{ml}" y1="{yy}" x2="{ml+pw}" y2="{yy}" stroke="#eef2f7"/>')
    for i, (v, lab) in enumerate(zip(values, labels)):
        x = ml + gap + i * (bw + gap)
        bh = ph * (v / ymax)
        yy = mt + ph - bh
        parts.append(f'<rect x="{x:.1f}" y="{yy:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="4" fill="{color}"/>')
        parts.append(f'<text x="{x+bw/2:.1f}" y="{yy-6:.1f}" text-anchor="middle" font-size="12" font-weight="700" fill="#1f2937">{v:.1f}</text>')
        parts.append(f'<text x="{x+bw/2:.1f}" y="{mt+ph+18:.1f}" text-anchor="middle" font-size="11" fill="#374151">{lab}</text>')
    parts.append(f'<text x="{ml-44}" y="{mt-14}" font-size="11" fill="#6b7280">{ylabel}</text>')
    parts.append('</svg>')
    _write(fname, "\n".join(parts))


def _svg_stacked(groups, seg_labels, seg_colors, title, fname):
    w, h = 600, 360
    ml, mr, mt, mb = 60, 20, 50, 60
    pw, ph = w - ml - mr, h - mt - mb
    totals = [sum(v) for v in groups]
    ymax = max(totals) * 1.1
    bw = pw / (len(groups) * 1.8)
    gap = bw * 0.8
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" font-family="Segoe UI, sans-serif">']
    parts.append(f'<text x="{w/2}" y="26" text-anchor="middle" font-size="16" font-weight="700" fill="#1f2937">{title}</text>')
    parts.append(f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{mt+ph}" stroke="#9ca3af"/>')
    parts.append(f'<line x1="{ml}" y1="{mt+ph}" x2="{ml+pw}" y2="{mt+ph}" stroke="#9ca3af"/>')
    for i in range(0, 5):
        yv = ymax * i / 4
        yy = mt + ph - ph * (yv / ymax)
        parts.append(f'<text x="{ml-8}" y="{yy+4}" text-anchor="end" font-size="11" fill="#6b7280">{yv:.0f}</text>')
        parts.append(f'<line x1="{ml}" y1="{yy}" x2="{ml+pw}" y2="{yy}" stroke="#eef2f7"/>')
    for i, (segs, glab) in enumerate(zip(groups, seg_labels)):
        x = ml + gap + i * (bw + gap)
        y = mt + ph
        for j, val in enumerate(segs):
            bh = ph * (val / ymax)
            y -= bh
            if bh > 0.5:
                parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{bh:.1f}" fill="{seg_colors[j]}"/>')
        parts.append(f'<text x="{x+bw/2:.1f}" y="{mt+ph+18:.1f}" text-anchor="middle" font-size="11" fill="#374151">{glab}</text>')
        parts.append(f'<text x="{x+bw/2:.1f}" y="{mt+ph+34:.1f}" text-anchor="middle" font-size="11" font-weight="700" fill="#1f2937">n={totals[i]}</text>')
    lx = ml
    ly = mt - 14
    for j, name in enumerate(["L1 正常", "L2 关注", "L3 深度", "L4 病理"]):
        parts.append(f'<rect x="{lx}" y="{ly-9}" width="11" height="11" fill="{seg_colors[j]}"/>')
        parts.append(f'<text x="{lx+15}" y="{ly}" font-size="10" fill="#374151">{name}</text>')
        lx += 95
    parts.append('</svg>')
    _write(fname, "\n".join(parts))


def _svg_grouped(cands, none_set, high_set, title, fname):
    w, h = 620, 340
    ml, mr, mt, mb = 60, 20, 50, 70
    pw, ph = w - ml - mr, h - mt - mb
    n = len(cands)
    bw = pw / (n * 2.4)
    gap = bw * 0.5
    ymax = 1.0
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" font-family="Segoe UI, sans-serif">']
    parts.append(f'<text x="{w/2}" y="26" text-anchor="middle" font-size="15" font-weight="700" fill="#1f2937">{title}</text>')
    parts.append(f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{mt+ph}" stroke="#9ca3af"/>')
    parts.append(f'<line x1="{ml}" y1="{mt+ph}" x2="{ml+pw}" y2="{mt+ph}" stroke="#9ca3af"/>')
    for i, mid in enumerate(cands):
        x0 = ml + gap + i * (bw * 2 + gap)
        yN = mt + ph - ph * (1.0 if mid in none_set else 0.0)
        parts.append(f'<rect x="{x0:.1f}" y="{yN:.1f}" width="{bw:.1f}" height="{ph - (yN-mt):.1f}" rx="3" fill="#3FA66A"/>')
        yH = mt + ph - ph * (1.0 if mid in high_set else 0.0)
        parts.append(f'<rect x="{x0+bw+4:.1f}" y="{yH:.1f}" width="{bw:.1f}" height="{ph - (yH-mt):.1f}" rx="3" fill="#E0533D"/>')
        parts.append(f'<text x="{x0+bw+2:.1f}" y="{mt+ph+16:.1f}" text-anchor="middle" font-size="9.5" fill="#374151">{mid}</text>')
        if mid in none_set and mid not in high_set:
            parts.append(f'<text x="{x0+bw+2:.1f}" y="{mt+ph+30:.1f}" text-anchor="middle" font-size="9.5" font-weight="700" fill="#E0533D">降权</text>')
    parts.append(f'<rect x="{ml}" y="{mt-12}" width="11" height="11" fill="#3FA66A"/><text x="{ml+15}" y="{mt-2}" font-size="10" fill="#374151">lai_risk=None</text>')
    parts.append(f'<rect x="{ml+110}" y="{mt-12}" width="11" height="11" fill="#E0533D"/><text x="{ml+125}" y="{mt-2}" font-size="10" fill="#374151">lai_risk=0.7</text>')
    parts.append('</svg>')
    _write(fname, "\n".join(parts))


def _write(fname, text):
    with open(fname, "w", encoding="utf-8") as f:
        f.write(text)


# ───────────────────────── 主流程 ─────────────────────────
def main():
    ap = argparse.ArgumentParser(description="抗成瘾层计算式评估 (in-silico ablation)")
    ap.add_argument("--log", help="真实脱敏学习事件 CSV 路径（覆盖合成队列）")
    ap.add_argument("--sample", action="store_true", help="生成合成脱敏样本日志后跑通")
    ap.add_argument("--n", type=int, default=N, help="合成队列规模（默认路径）")
    ap.add_argument("--seed", type=int, default=SEED, help="随机种子")
    ap.add_argument("--out", help="产物目录（默认 artifacts/evaluation[...]）")
    args = ap.parse_args()

    # —— 数据来源 ——
    if args.sample:
        out_base = args.out or (OUT_DIR + "_from_log")
        sample_path = os.path.join(out_base, "sample_desensitized_log.csv")
        os.makedirs(out_base, exist_ok=True)
        generate_sample_learning_log(sample_path, n_students=120, seed=args.seed)
        students = ingest_learning_log(sample_path)
        source = f"sample_log:{os.path.basename(sample_path)}"
        print(f"[数据] 合成脱敏样本日志: {sample_path}  (学生数={len(students)})")
    elif args.log:
        out_base = args.out or (OUT_DIR + "_from_log")
        students = ingest_learning_log(args.log)
        source = f"real_log:{os.path.basename(args.log)}"
        print(f"[数据] 真实脱敏学习日志: {args.log}  (学生数={len(students)})")
    else:
        out_base = args.out or OUT_DIR
        rng = random.Random(args.seed)
        students = [sample_student(rng) for _ in range(args.n)]
        source = f"synthetic:N={args.n},seed={args.seed}"
        print(f"[数据] 合成队列: N={args.n} seed={args.seed}")

    os.makedirs(out_base, exist_ok=True)
    os.makedirs(os.path.join(out_base, "tables"), exist_ok=True)
    os.makedirs(os.path.join(out_base, "figures"), exist_ok=True)

    eval_res = evaluate_conditions(students)
    cq_class = eval_res["cq_class"]
    summaries = {k: summarize(v) for k, v in eval_res["conditions"].items()}
    ablation = arbitrator_ablation()

    c0 = eval_res["conditions"]["C0_baseline"]
    c2 = eval_res["conditions"]["C2_full"]
    high_risk_idx = [i for i, a in enumerate(c0) if a.risk_tier.value >= 3]
    rescued = sum(1 for i in high_risk_idx if c2[i].risk_tier.value <= 2)
    rescue_rate = round(100 * rescued / len(high_risk_idx), 1) if high_risk_idx else 0.0

    scen_labels = {"C0_baseline": "C0 基线", "C1_classpet": "C1 班级宠物", "C2_full": "C2 全抗成瘾层"}
    metrics = ["mean_lai", "median_lai", "sd_lai", "pct_reduce_gamification", "pct_notify_guardian"]
    metric_labels = {"mean_lai": "平均 LAI", "median_lai": "中位 LAI", "sd_lai": "LAI 标准差",
                     "pct_reduce_gamification": "%应降游戏化", "pct_notify_guardian": "%应通知家长"}

    with open(os.path.join(out_base, "tables", "main_results.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scenario"] + list(metric_labels.values()) + ["L1", "L2", "L3", "L4"])
        for k in ["C0_baseline", "C1_classpet", "C2_full"]:
            s = summaries[k]
            w.writerow([scen_labels[k]] + [s[m] for m in metrics] +
                       [s["tier_counts"]["L1_NORMAL"], s["tier_counts"]["L2_WATCH"],
                        s["tier_counts"]["L3_DEEP"], s["tier_counts"]["L4_PATHOLOGICAL"]])
    with open(os.path.join(out_base, "tables", "main_results.md"), "w", encoding="utf-8") as f:
        f.write("# 表 2　抗成瘾层主结果（in-silico ablation）\n\n")
        f.write(f"> 数据来源：{source}\n\n")
        f.write("| 场景 | 平均LAI | 中位LAI | LAI标准差 | %应降游戏化 | %应通知家长 | L1 | L2 | L3 | L4 |\n")
        f.write("|---|---|---|---|---|---|---|---|---|---|\n")
        for k in ["C0_baseline", "C1_classpet", "C2_full"]:
            s = summaries[k]
            f.write(f"| {scen_labels[k]} | {s['mean_lai']} | {s['median_lai']} | {s['sd_lai']} | "
                    f"{s['pct_reduce_gamification']} | {s['pct_notify_guardian']} | "
                    f"{s['tier_counts']['L1_NORMAL']} | {s['tier_counts']['L2_WATCH']} | "
                    f"{s['tier_counts']['L3_DEEP']} | {s['tier_counts']['L4_PATHOLOGICAL']} |\n")
        f.write(f"\n> 班级宠物回灌连接质量 connection_quality = {cq_class}（cohesion={CLASS_COHESION}, active_ratio={CLASS_ACTIVE_RATIO}）。\n")
        f.write(f"> 高危亚组救援率（C0 为 L3/L4 的学生在 C2 下脱离高危的比例）= **{rescue_rate}%**（{rescued}/{len(high_risk_idx)}）。\n")
        f.write("> 声明：计算式评估，非田野实验；用于系统贡献的机制验证。\n")

    with open(os.path.join(out_base, "tables", "risk_distribution.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "L1_NORMAL", "L2_WATCH", "L3_DEEP", "L4_PATHOLOGICAL"])
        for k in ["C0_baseline", "C1_classpet", "C2_full"]:
            t = summaries[k]["tier_counts"]
            w.writerow([scen_labels[k], t["L1_NORMAL"], t["L2_WATCH"], t["L3_DEEP"], t["L4_PATHOLOGICAL"]])

    _svg_bar(
        [summaries[k]["mean_lai"] for k in ["C0_baseline", "C1_classpet", "C2_full"]],
        ["C0 基线", "C1 班级宠物", "C2 全抗成瘾层"],
        "各场景平均 LAI（越高越健康）", "LAI", os.path.join(out_base, "figures", "lai_by_scenario.svg"),
        ymax=80, color="#3FA66A",
    )
    _svg_stacked(
        [list(summaries[k]["tier_counts"].values()) for k in ["C0_baseline", "C1_classpet", "C2_full"]],
        ["C0 基线", "C1 班级宠物", "C2 全抗成瘾层"],
        ["#3FA66A", "#F2C14E", "#E08A3C", "#E0533D"],
        "各场景 LAI 风险等级分布（堆叠）", os.path.join(out_base, "figures", "risk_distribution.svg"),
    )
    _svg_grouped(
        ablation["candidates"], set(ablation["delivered_lai_none"]), set(ablation["delivered_lai_high"]),
        "仲裁器 LAI 风险自适应降权：候选→下发", os.path.join(out_base, "figures", "arbitrator_cooling.svg"),
    )

    result = {
        "meta": {
            "title": "LearnFlow 抗成瘾层计算式评估 (in-silico ablation)",
            "source": source,
            "seed": args.seed, "N": len(students), "declaration": "计算式/设计验证，非田野实验",
            "class_cohesion": CLASS_COHESION, "class_active_ratio": CLASS_ACTIVE_RATIO,
            "class_pet_connection_quality": cq_class,
        },
        "high_risk_rescue": {
            "c0_high_risk_count": len(high_risk_idx),
            "rescued_count": rescued,
            "rescue_rate_pct": rescue_rate,
        },
        "scenarios": {k: summaries[k] for k in ["C0_baseline", "C1_classpet", "C2_full"]},
        "arbitrator_ablation": ablation,
        "delta": {
            "C1_minus_C0_mean_lai": round(summaries["C1_classpet"]["mean_lai"] - summaries["C0_baseline"]["mean_lai"], 2),
            "C2_minus_C0_mean_lai": round(summaries["C2_full"]["mean_lai"] - summaries["C0_baseline"]["mean_lai"], 2),
            "C2_minus_C1_mean_lai": round(summaries["C2_full"]["mean_lai"] - summaries["C1_classpet"]["mean_lai"], 2),
        },
    }
    with open(os.path.join(out_base, "result.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    pap = {
        "hypothesis": "抗成瘾层（LF-M54 真实连接替代 + 仲裁器风险降权）会显著提升队列平均 LAI（健康度），并降低 L3/L4 风险占比。",
        "design": "配对反事实 in-silico ablation，同队列三条件（C0/C1/C2）",
        "primary_outcome": "mean_lai 差异 (C2 - C0)",
        "seed": args.seed, "engine": "LearningAddictionIndex + MechanismArbitrator",
        "data_source": source,
        "note": "结果完全由本文件 + 引擎代码决定，审稿人可复现。",
    }
    with open(os.path.join(out_base, "pap.json"), "w", encoding="utf-8") as f:
        json.dump(pap, f, ensure_ascii=False, indent=2)

    print("=" * 64)
    print("LearnFlow 抗成瘾层计算式评估 —— 结果摘要")
    print(f"  数据来源: {source}")
    print(f"  队列 N={len(students)}  class_pet connection_quality={cq_class}")
    print("-" * 64)
    for k in ["C0_baseline", "C1_classpet", "C2_full"]:
        s = summaries[k]
        print(f"  {scen_labels[k]:<12} 平均LAI={s['mean_lai']:>6}  风险 L3+L4={s['tier_counts']['L3_DEEP']+s['tier_counts']['L4_PATHOLOGICAL']:>3}  "
              f"%降游戏化={s['pct_reduce_gamification']}")
    print("-" * 64)
    print(f"  边际提升  C1-C0 = +{result['delta']['C1_minus_C0_mean_lai']}   C2-C0 = +{result['delta']['C2_minus_C0_mean_lai']}   C2-C1 = +{result['delta']['C2_minus_C1_mean_lai']}")
    print(f"  高危亚组救援率: {rescue_rate}%  ({rescued}/{len(high_risk_idx)} 名 C0 高危学生在 C2 下脱离高危)")
    print(f"  仲裁器降权: lai_risk=None 下发 {ablation['count_none']} 个 → high 下发 {ablation['count_high']} 个, 丢弃 {ablation['dropped_by_risk']}")
    print("=" * 64)
    print(f"  产物目录: {out_base}")


if __name__ == "__main__":
    main()
