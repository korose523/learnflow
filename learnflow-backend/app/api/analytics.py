"""实时分析 API —— 事件摄入 / 实时风险 / 班级风险 / 早期预警。

实时分析层对外的 HTTP 入口。特征存储与风险模型为模块级单例
(生产应注入或替换为带 TTL 的 Redis/独立推理服务)。端点无 DB 依赖,
直接消费内存特征存储, 因此可被联调测试在不依赖 MySQL 的情况下完整验证。
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.feature_store import FeatureStore, FEATURE_KEYS
from app.services.ml_risk_model import TemporalRiskModel

feature_store = FeatureStore()
risk_model = TemporalRiskModel()

# 加载训练产物, 使线上风险评分与论文表 3 (AUROC 0.966) 一致。
# 缺失时回退到未训练（随机权重）模型, 保证接口始终可用。
_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "artifacts", "ai_layer", "model.json",
)
try:
    if os.path.exists(_MODEL_PATH):
        risk_model = TemporalRiskModel.load(_MODEL_PATH)
        print(f"[analytics] 已加载训练模型: {_MODEL_PATH}")
    else:
        print(f"[analytics] 未找到训练模型 {_MODEL_PATH}, 使用未训练模型 (请先运行 scripts/train_eval_ai_layer.py)")
except Exception as exc:  # 加载失败不应阻断接口启动
    print(f"[analytics] 加载训练模型失败, 回退未训练模型: {exc}")

router = APIRouter(prefix="/api/v1/analytics", tags=["实时分析"])


class IngestBody(BaseModel):
    events: List[Dict] = []


class EventBody(BaseModel):
    event: Dict = {}


@router.post("/ingest")
async def ingest(body: IngestBody):
    for e in body.events:
        feature_store.ingest(e)
    return {"ok": True, "ingested": len(body.events)}


@router.post("/student/{user_id}/event")
async def student_event(user_id: str, body: EventBody):
    ev = dict(body.event)
    ev["user_id"] = user_id
    risk = risk_model.online_update(ev)
    return {"user_id": user_id, "ml_risk": round(risk, 4),
            "risk_tier": risk_model.risk_tier(risk)}


@router.get("/student/{user_id}/risk")
async def student_risk(user_id: str):
    ml_risk = risk_model.predict(user_id)
    tier = risk_model.risk_tier(ml_risk)
    feats = feature_store.feature_vector(user_id)
    factors = sorted(
        [(FEATURE_KEYS[i], round(feats[i], 3)) for i in range(len(feats))],
        key=lambda kv: -kv[1],
    )[:3]
    return {"user_id": user_id, "ml_risk": round(ml_risk, 4),
            "risk_tier": tier, "top_factors": factors}


@router.get("/class/{class_id}/risk")
async def class_risk(class_id: str, user_ids: Optional[List[str]] = None):
    uids = user_ids or feature_store.users()
    risks = [(u, risk_model.predict(u)) for u in uids]
    if not risks:
        return {"class_id": class_id, "mean_risk": 0.0, "students": 0,
                "distribution": {str(t): 0 for t in range(4)}}
    mean = sum(r for _, r in risks) / len(risks)
    dist = {str(t): 0 for t in range(4)}
    for _, r in risks:
        dist[str(risk_model.risk_tier(r))] += 1
    return {"class_id": class_id, "mean_risk": round(mean, 4),
            "students": len(risks), "distribution": dist}


@router.get("/class/{class_id}/early-warning")
async def early_warning(class_id: str, threshold: float = 0.5,
                        user_ids: Optional[List[str]] = None):
    uids = user_ids or feature_store.users()
    warnings = []
    for u in uids:
        r = risk_model.predict(u)
        if r >= threshold:
            feats = feature_store.feature_vector(u)
            factors = sorted(
                [(FEATURE_KEYS[i], round(feats[i], 3)) for i in range(len(feats))],
                key=lambda kv: -kv[1],
            )[:2]
            warnings.append({"user_id": u, "risk": round(r, 4), "factors": factors})
    warnings.sort(key=lambda w: -w["risk"])
    return {"class_id": class_id, "threshold": threshold,
            "count": len(warnings), "warnings": warnings}
