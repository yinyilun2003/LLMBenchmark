# api/routers/v1/datasets.py
from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.db import get_db
from api.models.user import User as UserORM
from api.models.dataset import Dataset as DatasetORM, DatasetVersion as DatasetVerORM  # 先实现 ORM 再用
from api.routers.v1.user import get_current_user

router = APIRouter(prefix="/datasets", tags=["Datasets"])


# ----------------- Schemas -----------------
class DatasetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    storage_uri: str = Field(..., description="e.g. s3://bucket/prefix or file:///path")
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class DatasetUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    storage_uri: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class DatasetResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    storage_uri: str
    description: Optional[str] = None
    tags: List[str] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PageMeta(BaseModel):
    page: int
    per_page: int
    total: int


class PaginatedDatasets(BaseModel):
    meta: PageMeta
    items: List[DatasetResponse]


class DatasetVersionCreate(BaseModel):
    version: str = Field(..., description="e.g. v1, 2024-09-01, sha123")
    storage_uri: Optional[str] = None
    notes: Optional[str] = None


class DatasetVersionResponse(BaseModel):
    id: UUID
    dataset_id: UUID
    version: str
    storage_uri: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ----------------- Helpers -----------------
def _ensure_owner_or_admin(ds: DatasetORM, user: UserORM):
    if user.is_admin:
        return
    if ds.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")


# ----------------- Routes -----------------
@router.post("", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
def create_dataset(
    payload: DatasetCreate,
    db: Session = Depends(get_db),
    current: UserORM = Depends(get_current_user),
):
    ds = DatasetORM(
        user_id=str(current.id),
        name=payload.name,
        storage_uri=payload.storage_uri,
        description=payload.description,
        tags=payload.tags or [],
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)
    return ds  # from_attributes=True 支持 ORM 直接返回


@router.get("", response_model=PaginatedDatasets)
def list_datasets(
    db: Session = Depends(get_db),
    current: UserORM = Depends(get_current_user),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=200),
    mine: bool = Query(True, description="仅自己；管理员设为 false 可看全部"),
    name_like: Optional[str] = Query(None),
):
    q = db.query(DatasetORM)
    if mine or not current.is_admin:
        q = q.filter(DatasetORM.user_id == str(current.id))
    if name_like:
        q = q.filter(DatasetORM.name.ilike(f"%{name_like}%"))

    total = q.count()
    rows = (
        q.order_by(DatasetORM.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return PaginatedDatasets(
        meta=PageMeta(page=page, per_page=per_page, total=total),
        items=rows,
    )


@router.get("/{dataset_id}", response_model=DatasetResponse)
def get_dataset(
    dataset_id: UUID,
    db: Session = Depends(get_db),
    current: UserORM = Depends(get_current_user),
):
    ds = db.query(DatasetORM).get(str(dataset_id))
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    _ensure_owner_or_admin(ds, current)
    return ds


@router.patch("/{dataset_id}", response_model=DatasetResponse)
def update_dataset(
    dataset_id: UUID,
    payload: DatasetUpdate,
    db: Session = Depends(get_db),
    current: UserORM = Depends(get_current_user),
):
    ds = db.query(DatasetORM).get(str(dataset_id))
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    _ensure_owner_or_admin(ds, current)

    if payload.name is not None:
        ds.name = payload.name
    if payload.storage_uri is not None:
        ds.storage_uri = payload.storage_uri
    if payload.description is not None:
        ds.description = payload.description
    if payload.tags is not None:
        ds.tags = payload.tags

    db.add(ds)
    db.commit()
    db.refresh(ds)
    return ds


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset(
    dataset_id: UUID,
    db: Session = Depends(get_db),
    current: UserORM = Depends(get_current_user),
):
    ds = db.query(DatasetORM).get(str(dataset_id))
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    _ensure_owner_or_admin(ds, current)
    db.delete(ds)
    db.commit()
    return None


# -------- Versions --------
@router.post("/{dataset_id}/versions", response_model=DatasetVersionResponse, status_code=201)
def create_version(
    dataset_id: UUID,
    payload: DatasetVersionCreate,
    db: Session = Depends(get_db),
    current: UserORM = Depends(get_current_user),
):
    ds = db.query(DatasetORM).get(str(dataset_id))
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    _ensure_owner_or_admin(ds, current)

    ver = DatasetVerORM(
        dataset_id=str(dataset_id),
        version=payload.version,
        storage_uri=payload.storage_uri or ds.storage_uri,
        notes=payload.notes,
    )
    db.add(ver)
    db.commit()
    db.refresh(ver)
    return ver


@router.get("/{dataset_id}/versions", response_model=List[DatasetVersionResponse])
def list_versions(
    dataset_id: UUID,
    db: Session = Depends(get_db),
    current: UserORM = Depends(get_current_user),
):
    ds = db.query(DatasetORM).get(str(dataset_id))
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    _ensure_owner_or_admin(ds, current)

    rows = (
        db.query(DatasetVerORM)
        .filter(DatasetVerORM.dataset_id == str(dataset_id))
        .order_by(DatasetVerORM.created_at.desc())
        .all()
    )
    return rows
