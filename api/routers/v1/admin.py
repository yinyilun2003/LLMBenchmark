# api/routers/v1/admin.py
from __future__ import annotations

from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.db import get_db, ping as db_ping
from api.models.user import User as UserORM
from api.routers.v1.user import get_current_user

router = APIRouter(prefix="/admin", tags=["Admin"])


# --------- Schemas ---------
class AdminUser(BaseModel):
    id: UUID
    username: str
    email: str
    is_active: bool
    is_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminUsersResponse(BaseModel):
    items: List[AdminUser]


# --------- Helpers ---------
def require_admin(current: UserORM = Depends(get_current_user)) -> UserORM:
    if not current.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admins only")
    return current


# --------- Endpoints ---------
@router.get("/users", response_model=AdminUsersResponse, summary="List all users")
def list_all_users(
    _: UserORM = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rows = db.query(UserORM).order_by(UserORM.created_at.desc()).all()
    return AdminUsersResponse(items=rows)


@router.post("/users/{user_id}/disable", response_model=AdminUser, summary="Disable a user")
def disable_user(
    user_id: UUID,
    _: UserORM = Depends(require_admin),
    db: Session = Depends(get_db),
):
    u = db.query(UserORM).get(str(user_id))
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    u.is_active = False
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@router.post("/users/{user_id}/enable", response_model=AdminUser, summary="Enable a user")
def enable_user(
    user_id: UUID,
    _: UserORM = Depends(require_admin),
    db: Session = Depends(get_db),
):
    u = db.query(UserORM).get(str(user_id))
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    u.is_active = True
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@router.get("/health", summary="Admin health checks")
def admin_health(_: UserORM = Depends(require_admin)):
    return {"db": db_ping()}
