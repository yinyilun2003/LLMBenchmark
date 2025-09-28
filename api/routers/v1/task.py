# routers/v1/task.py
from __future__ import annotations

from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.models.schemas import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskStatus,
    PaginatedTasks,
    PageMeta,
)
from core.db import get_db
from api.models.task import Task as TaskORM
from api.models.user import User as UserORM
from api.routers.v1.user import get_current_user  # 复用鉴权依赖

router = APIRouter(prefix="/tasks", tags=["Tasks"])


# -------- helpers --------
def _to_task_response(t: TaskORM) -> TaskResponse:
    return TaskResponse(
        id=t.id,
        user_id=t.user_id,
        name=t.name,
        model=t.model,
        route=t.route,
        dataset=t.dataset,
        params=t.params or {},
        concurrency=t.concurrency,
        duration_sec=t.duration_sec,
        status=TaskStatus(t.status),
        created_at=t.created_at,
        started_at=t.started_at,
        finished_at=t.finished_at,
        error=t.error,
    )


def _ensure_owner_or_admin(task: TaskORM, user: UserORM):
    if user.is_admin:
        return
    if task.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")


# -------- routes --------
@router.post("", response_model=TaskResponse, status_code=201)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current: UserORM = Depends(get_current_user),
):
    task = TaskORM(
        user_id=current.id,
        name=payload.name,
        model=payload.model,
        route=payload.route,
        dataset=payload.dataset,
        params=payload.params or {},
        concurrency=payload.concurrency,
        duration_sec=payload.duration_sec,
        status=TaskStatus.queued.value,
        tags=payload.tags or [],
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # TODO: 可在此投递到 Kafka: bench.jobs
    return _to_task_response(task)


@router.get("", response_model=PaginatedTasks)
def list_tasks(
    db: Session = Depends(get_db),
    current: UserORM = Depends(get_current_user),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=200),
    status_eq: Optional[TaskStatus] = Query(None, alias="status"),
    model_eq: Optional[str] = Query(None, alias="model"),
    mine: bool = Query(True, description="仅查看自己任务；管理员可设为 false 查看全部"),
):
    q = db.query(TaskORM)
    if mine or not current.is_admin:
        q = q.filter(TaskORM.user_id == current.id)
    if status_eq:
        q = q.filter(TaskORM.status == status_eq.value)
    if model_eq:
        q = q.filter(TaskORM.model == model_eq)

    total = q.count()
    items: List[TaskORM] = (
        q.order_by(TaskORM.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return PaginatedTasks(
        meta=PageMeta(page=page, per_page=per_page, total=total),
        items=[_to_task_response(t) for t in items],
    )


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    current: UserORM = Depends(get_current_user),
):
    task = db.query(TaskORM).get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    _ensure_owner_or_admin(task, current)
    return _to_task_response(task)


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: UUID,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current: UserORM = Depends(get_current_user),
):
    task = db.query(TaskORM).get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    _ensure_owner_or_admin(task, current)

    if payload.name is not None:
        task.name = payload.name
    if payload.params is not None:
        task.params = payload.params
    if payload.concurrency is not None:
        task.concurrency = payload.concurrency
    if payload.duration_sec is not None:
        task.duration_sec = payload.duration_sec
    if payload.tags is not None:
        task.tags = payload.tags

    db.add(task)
    db.commit()
    db.refresh(task)
    return _to_task_response(task)


@router.delete("/{task_id}", status_code=204)
def delete_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    current: UserORM = Depends(get_current_user),
):
    task = db.query(TaskORM).get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    _ensure_owner_or_admin(task, current)
    db.delete(task)
    db.commit()
    return None
