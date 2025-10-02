# api/routers/v1/metrics.py
from __future__ import annotations

import csv
from datetime import datetime
from io import StringIO
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.db import get_db
from api.models.user import User as UserORM
from api.models.task import Task as TaskORM
from api.models.metric import Metric as MetricORM
from api.routers.v1.user import get_current_user
from api.models.schemas import MetricPoint, RunSummary

router = APIRouter(prefix="/metrics", tags=["Metrics"])


# ---------- Schemas ----------
class MetricIngestItem(BaseModel):
    task_id: UUID
    ts: datetime = Field(default_factory=datetime.utcnow)
    latency_ms: Optional[int] = None
    http_status: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    quality: Optional[float] = None
    error: Optional[str] = None


class MetricIngestRequest(BaseModel):
    items: List[MetricIngestItem]


class MetricListResponse(BaseModel):
    items: List[MetricPoint]
    total: int


# ---------- Helpers ----------
def _ensure_owner_or_admin(task: TaskORM, user: UserORM):
    if user.is_admin:
        return
    if task.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")


def _to_point(m: MetricORM) -> MetricPoint:
    return MetricPoint(
        ts=m.ts,
        latency_ms=m.latency_ms,
        http_status=m.http_status,
        prompt_tokens=m.prompt_tokens,
        completion_tokens=m.completion_tokens,
        cost_usd=m.cost_usd,
        quality=m.quality,
        error=m.error,
    )


def _percentile(sorted_vals: List[float], p: float) -> Optional[float]:
    if not sorted_vals:
        return None
    k = (len(sorted_vals) - 1) * p
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return float(sorted_vals[f])
    d0 = sorted_vals[f] * (c - k)
    d1 = sorted_vals[c] * (k - f)
    return float(d0 + d1)


# ---------- Endpoints ----------
@router.post("/ingest", status_code=202, summary="Ingest metrics from workers (batch)")
def ingest_metrics(
    payload: MetricIngestRequest,
    db: Session = Depends(get_db),
    current: UserORM = Depends(get_current_user),
):
    task_ids = {str(i.task_id) for i in payload.items}
    tasks = db.query(TaskORM).filter(TaskORM.id.in_(task_ids)).all()
    task_map = {t.id: t for t in tasks}
    for tid in task_ids:
        t = task_map.get(tid)
        if not t:
            raise HTTPException(status_code=404, detail=f"Task {tid} not found")
        _ensure_owner_or_admin(t, current)

    objs = [
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
        for i in payload.items
    ]
    db.add_all(objs)
    db.commit()
    return {"accepted": len(objs)}


@router.get("/runs/{task_id}", response_model=MetricListResponse, summary="List raw metrics for a run")
def list_metrics(
    task_id: UUID,
    db: Session = Depends(get_db),
    current: UserORM = Depends(get_current_user),
    page: int = Query(1, ge=1),
    per_page: int = Query(200, ge=1, le=5000),
    ts_ge: Optional[datetime] = Query(None),
    ts_le: Optional[datetime] = Query(None),
):
    task = db.query(TaskORM).get(str(task_id))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    _ensure_owner_or_admin(task, current)

    q = db.query(MetricORM).filter(MetricORM.task_id == str(task_id))
    if ts_ge:
        q = q.filter(MetricORM.ts >= ts_ge)
    if ts_le:
        q = q.filter(MetricORM.ts <= ts_le)

    total = q.count()
    rows = (
        q.order_by(MetricORM.ts.asc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return MetricListResponse(items=[_to_point(m) for m in rows], total=total)


@router.get("/runs/{task_id}/summary", response_model=RunSummary, summary="Aggregate summary for a run")
def run_summary(
    task_id: UUID,
    db: Session = Depends(get_db),
    current: UserORM = Depends(get_current_user),
    ts_ge: Optional[datetime] = Query(None),
    ts_le: Optional[datetime] = Query(None),
):
    task = db.query(TaskORM).get(str(task_id))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    _ensure_owner_or_admin(task, current)

    q = db.query(MetricORM).filter(MetricORM.task_id == str(task_id))
    if ts_ge:
        q = q.filter(MetricORM.ts >= ts_ge)
    if ts_le:
        q = q.filter(MetricORM.ts <= ts_le)

    rows: List[MetricORM] = q.order_by(MetricORM.ts.asc()).all()
    lat = [m.latency_ms for m in rows if m.latency_ms is not None]
    errs = [m for m in rows if m.error]
    costs = [m.cost_usd for m in rows if m.cost_usd is not None]
    quals = [m.quality for m in rows if m.quality is not None]

    lat_sorted = sorted(lat)
    p50 = int(_percentile(lat_sorted, 0.50)) if lat_sorted else None
    p90 = int(_percentile(lat_sorted, 0.90)) if lat_sorted else None
    p99 = int(_percentile(lat_sorted, 0.99)) if lat_sorted else None

    rps = None
    if rows:
        duration = (rows[-1].ts - rows[0].ts).total_seconds() or 1.0
        rps = round(len(rows) / duration, 3)

    error_rate = round(len(errs) / len(rows), 4) if rows else None
    cost_sum = round(sum(costs), 6) if costs else None
    quality_avg = round(sum(quals) / len(quals), 6) if quals else None

    return RunSummary(
        task_id=UUID(str(task_id)),
        p50_ms=p50,
        p90_ms=p90,
        p99_ms=p99,
        rps=rps,
        error_rate=error_rate,
        cost_usd=cost_sum,
        quality=quality_avg,
    )


@router.get("/runs/{task_id}/export.csv", summary="Export raw metrics as CSV")
def export_csv(
    task_id: UUID,
    db: Session = Depends(get_db),
    current: UserORM = Depends(get_current_user),
):
    task = db.query(TaskORM).get(str(task_id))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    _ensure_owner_or_admin(task, current)

    rows = (
        db.query(MetricORM)
        .filter(MetricORM.task_id == str(task_id))
        .order_by(MetricORM.ts.asc())
        .all()
    )

    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "ts", "latency_ms", "http_status", "prompt_tokens",
        "completion_tokens", "cost_usd", "quality", "error"
    ])
    for m in rows:
        writer.writerow([
            m.ts.isoformat() if m.ts else "",
            m.latency_ms or "",
            m.http_status or "",
            m.prompt_tokens or "",
            m.completion_tokens or "",
            m.cost_usd or "",
            m.quality or "",
            m.error or "",
        ])
    buf.seek(0)
    filename = f"metrics_{task_id}.csv"
    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
