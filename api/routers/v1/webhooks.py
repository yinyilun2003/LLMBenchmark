# api/routers/v1/webhooks.py
from __future__ import annotations

import hmac
import os
from hashlib import sha256
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.db import get_db
from api.models.task import Task as TaskORM
from api.models.metric import Metric as MetricORM

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

# 可选：共享签名密钥（worker -> API）
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")  # 未设置则不校验签名


def _verify_signature(raw_body: bytes, signature: Optional[str]) -> None:
    if not WEBHOOK_SECRET:
        return
    if not signature:
        raise HTTPException(status_code=401, detail="Missing signature")
    mac = hmac.new(WEBHOOK_SECRET.encode(), raw_body, sha256).hexdigest()
    if not hmac.compare_digest(mac, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")


# -------- Schemas --------
class WorkerStatus(BaseModel):
    task_id: UUID
    status: str = Field(..., description="queued|running|succeeded|failed|canceled")
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class MetricItem(BaseModel):
    task_id: UUID
    ts: datetime = Field(default_factory=datetime.utcnow)
    latency_ms: Optional[int] = None
    http_status: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    quality: Optional[float] = None
    error: Optional[str] = None


class MetricBatch(BaseModel):
    items: List[MetricItem]


# -------- Endpoints --------
@router.get("/ping", summary="Webhook liveness probe")
async def ping():
    return {"ok": True}


@router.post("/worker/status", summary="Worker sends task status update")
async def worker_status(
    req: Request,
    payload: WorkerStatus,
    db: Session = Depends(get_db),
    x_signature: Optional[str] = Header(None, alias="X-Signature"),
):
    raw = await req.body()
    _verify_signature(raw, x_signature)

    t: TaskORM | None = db.query(TaskORM).get(str(payload.task_id))
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")

    t.status = payload.status
    if payload.started_at is not None:
        t.started_at = payload.started_at
    if payload.finished_at is not None:
        t.finished_at = payload.finished_at
    if payload.error is not None:
        t.error = payload.error

    db.add(t)
    db.commit()
    db.refresh(t)
    return {"ok": True, "task_id": t.id, "status": t.status}


@router.post("/worker/metrics", summary="Worker sends batch metrics")
async def worker_metrics(
    req: Request,
    batch: MetricBatch,
    db: Session = Depends(get_db),
    x_signature: Optional[str] = Header(None, alias="X-Signature"),
):
    raw = await req.body()
    _verify_signature(raw, x_signature)

    ids = {str(i.task_id) for i in batch.items}
    existing = db.query(TaskORM).filter(TaskORM.id.in_(ids)).all()
    if len(existing) != len(ids):
        missing = ids - {t.id for t in existing}
        raise HTTPException(status_code=404, detail=f"Missing tasks: {sorted(missing)}")

    rows = [
        MetricORM(
            task_id=str(i.task_id),
            ts=i.ts,
            latency_ms=i.latency_ms,
            http_status=i.http_status,
            prompt_tokens=i.prompt_tokens,
            completion_tokens=i.completion_tokens,
            cost_usd=i.cost_usd,
            quality=i.quality,
            error=i.error,
        )
        for i in batch.items
    ]
    db.add_all(rows)
    db.commit()
    return {"ok": True, "accepted": len(rows)}
