# api/routers/v1/auth.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from core.db import get_db
from api.models.user import User as UserORM
from api.models.schemas import Token
from api.routers.v1.user import (
    verify_password,        # 复用 user.py 中的密码校验
    create_access_token,    # 复用 user.py 中的 JWT 生成
    get_current_user,       # 复用鉴权依赖
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=Token, summary="Login and get JWT")
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(UserORM).filter(UserORM.username == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is disabled")
    return Token(access_token=create_access_token(user.id))


@router.post("/refresh", response_model=Token, summary="Refresh JWT")
def refresh(current: UserORM = Depends(get_current_user)):
    return Token(access_token=create_access_token(current.id))
