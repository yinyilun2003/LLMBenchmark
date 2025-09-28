# api/routers/v1/reports.py
from __future__ import annotations

from datetime import datetime
from io import StringIO
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.db import get_db
from api.models.user import User as UserORM
from api.models.task import Task as TaskORM
from api.models.metric import Metric as MetricORM
from api.routers.v1.user import get_current_user
from api.models.schemas import RunSummary

router = APIRouter(prefix="/reports", tags=["Reports"])


# ---------- helpers ----------
def _ensure_owner_or_admin(task: TaskORM, user: UserORM):
    if user.is_admin:
        return
    if task.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")


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


def _run_summary(task_id: str, rows: List[MetricORM]) -> RunSummary:
    lat = [m.latency_ms for m in rows if m.latency_ms is not None]
    costs = [m.cost_usd for m in rows if m.cost_usd is not None]
    quals = [m.quality for m in rows if m.quality is not None]
    errs = [m for m in rows if m.error]
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
        task_id=UUID(task_id),
        p50_ms=p50,
        p90_ms=p90,
        p99_ms=p99,
        rps=rps,
        error_rate=error_rate,
        cost_usd=cost_sum,
        quality=quality_avg,
    )


# ---------- schemas ----------
class CompareItem(BaseModel):
    task_id: UUID
    model: str
    route: str
    dataset: str
    p50_ms: Optional[int] = None
    p90_ms: Optional[int] = None
    p99_ms: Optional[int] = None
    rps: Optional[float] = None
    error_rate: Optional[float] = None
    cost_usd: Optional[float] = None
    quality: Optional[float] = None


class CompareResponse(BaseModel):
    items: List[CompareItem]


# ---------- endpoints ----------
@router.get("/runs/{task_id}", response_model=RunSummary, summary="Summary for a single run")
def report_run(
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
    rows = q.order_by(MetricORM.ts.asc()).all()

    return _run_summary(str(task_id), rows)


@router.get("/compare", response_model=CompareResponse, summary="Compare multiple runs")
def report_compare(
    task_ids: List[UUID] = Query(..., description="Repeat ?task_ids=<id> for each run"),
    db: Session = Depends(get_db),
    current: UserORM = Depends(get_current_user),
):
    # load tasks and check ACL
    ids = [str(x) for x in task_ids]
    tasks = db.query(TaskORM).filter(TaskORM.id.in_(ids)).all()
    if len(tasks) != len(ids):
        missing = set(ids) - {t.id for t in tasks}
        raise HTTPException(status_code=404, detail=f"Missing tasks: {sorted(missing)}")
    for t in tasks:
        _ensure_owner_or_admin(t, current)

    # fetch metrics per task
    items: List[CompareItem] = []
    for t in tasks:
        rows = (
            db.query(MetricORM)
            .filter(MetricORM.task_id == t.id)
            .order_by(MetricORM.ts.asc())
            .all()
        )
        s = _run_summary(t.id, rows)
        items.append(
            CompareItem(
                task_id=UUID(t.id),
                model=t.model,
                route=t.route,
                dataset=t.dataset,
                p50_ms=s.p50_ms,
                p90_ms=s.p90_ms,
                p99_ms=s.p99_ms,
                rps=s.rps,
                error_rate=s.error_rate,
                cost_usd=s.cost_usd,
                quality=s.quality,
            )
        )
    return CompareResponse(items=items)


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
    buf.write("ts,latency_ms,http_status,prompt_tokens,completion_tokens,cost_usd,quality,error\n")
    for m in rows:
        buf.write(
            f"{m.ts.isoformat()},{m.latency_ms or ''},{m.http_status or ''},"
            f"{m.prompt_tokens or ''},{m.completion_tokens or ''},"
            f"{m.cost_usd or ''},{m.quality or ''},\"{(m.error or '').replace('\"','''')}\"\n"
        )
    buf.seek(0)
    filename = f"metrics_{task_id}.csv"
    return StreamingResponse(
        buf,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
