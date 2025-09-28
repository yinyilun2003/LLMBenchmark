# api/routers/v1/runs.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.db import get_db
from api.models.task import Task as TaskORM
from api.models.user import User as UserORM
from api.routers.v1.user import get_current_user

router = APIRouter(prefix="/runs", tags=["Runs"])


# -------- Schemas (local, minimal) --------
class RunStart(BaseModel):
    task_id: UUID


class RunInfo(BaseModel):
    run_id: UUID
    task_id: UUID
    user_id: UUID
    status: str
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error: Optional[str] = None


class PaginatedRuns(BaseModel):
    page: int
    per_page: int
    total: int
    items: List[RunInfo]


# -------- helpers --------
def _ensure_owner_or_admin(task: TaskORM, user: UserORM):
    if user.is_admin:
        return
    if task.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")


def _to_run_info(t: TaskORM) -> RunInfo:
    # 暂以 Task 视为一次“Run”，后续如果你引入独立 Run 表，把此映射替换为真正的 RunORM
    return RunInfo(
        run_id=t.id,
        task_id=t.id,
        user_id=t.user_id,
        status=t.status,
        created_at=t.created_at,
        started_at=t.started_at,
        finished_at=t.finished_at,
        error=t.error,
    )


# -------- routes --------
@router.post("", response_model=RunInfo, status_code=201, summary="Start a run for an existing task")
def start_run(
    payload: RunStart,
    db: Session = Depends(get_db),
    current: UserORM = Depends(get_current_user),
):
    task = db.query(TaskORM).get(payload.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    _ensure_owner_or_admin(task, current)

    # 将任务置为待执行；实际执行由 worker 处理
    task.status = "queued"
    task.started_at = None
    task.finished_at = None
    task.error = None
    db.add(task)
    db.commit()
    db.refresh(task)
    # TODO: 在此处向 Kafka 发送 bench.jobs 消息

    return _to_run_info(task)


@router.get("", response_model=PaginatedRuns, summary="List runs (backed by tasks)")
def list_runs(
    db: Session = Depends(get_db),
    current: UserORM = Depends(get_current_user),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=200),
    status_eq: Optional[str] = Query(None, alias="status"),
    mine: bool = Query(True, description="仅自己; 管理员可设为 false 查看全部"),
):
    q = db.query(TaskORM)
    if mine or not current.is_admin:
        q = q.filter(TaskORM.user_id == current.id)
    if status_eq:
        q = q.filter(TaskORM.status == status_eq)

    total = q.count()
    tasks = (
        q.order_by(TaskORM.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return PaginatedRuns(
        page=page,
        per_page=per_page,
        total=total,
        items=[_to_run_info(t) for t in tasks],
    )


@router.get("/{run_id}", response_model=RunInfo, summary="Get run status")
def get_run(
    run_id: UUID,
    db: Session = Depends(get_db),
    current: UserORM = Depends(get_current_user),
):
    task = db.query(TaskORM).get(run_id)  # run_id == task_id in this minimal version
    if not task:
        raise HTTPException(status_code=404, detail="Run not found")
    _ensure_owner_or_admin(task, current)
    return _to_run_info(task)


@router.post("/{run_id}/cancel", response_model=RunInfo, summary="Cancel a queued/running run")
def cancel_run(
    run_id: UUID,
    db: Session = Depends(get_db),
    current: UserORM = Depends(get_current_user),
):
    task = db.query(TaskORM).get(run_id)
    if not task:
        raise HTTPException(status_code=404, detail="Run not found")
    _ensure_owner_or_admin(task, current)

    if task.status in ("succeeded", "failed", "canceled"):
        raise HTTPException(status_code=409, detail=f"Run already {task.status}")

    task.status = "canceled"
    task.finished_at = datetime.now(timezone.utc)
    db.add(task)
    db.commit()
    db.refresh(task)
    # TODO: 广播取消事件到队列（若 worker 支持取消）
    return _to_run_info(task)
