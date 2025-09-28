# routers/v1/user.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session
import os

# ==== Project schemas ====
from api.models.schemas import (
    UserSignup,
    UserLogin,
    UserResponse,
    Token,
    TokenPayload,
)

# ==== DB & ORM (根据你的工程实际修改) ====
# 你应当在 core/db.py 提供 get_db，并在 models/user.py 定义 User ORM
# 这里给出最小接口假定，便于即刻使用。
from core.db import get_db               # -> def get_db() -> Generator[Session, None, None]
from api.models.user import User as UserORM  # -> SQLAlchemy model with fields见下方注释

# 期望的 User ORM 字段：
# id: UUID(primary key), username: str(unique), email: str(unique),
# password_hash: str, is_active: bool, is_admin: bool, created_at: datetime

# ==== Security: JWT + Password Hash ====
from jose import jwt, JWTError
from passlib.context import CryptContext 

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/login")

SECRET_KEY = os.getenv("JWT_SECRET", "CHANGE_ME")
ALGORITHM = os.getenv("JWT_ALG", "HS256")
ACCESS_TOKEN_EXPIRE_MIN = int(os.getenv("JWT_EXPIRE_MIN", "60"))

router = APIRouter(prefix="/users", tags=["Users"])


# ========================
# helpers
# ========================

def hash_password(raw: str) -> str:
    return pwd_ctx.hash(raw)

def verify_password(raw: str, hashed: str) -> bool:
    return pwd_ctx.verify(raw, hashed)

def create_access_token(sub: UUID, minutes: int = ACCESS_TOKEN_EXPIRE_MIN) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(sub), "exp": now + timedelta(minutes=minutes)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> UserORM:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = data.get("sub")
        if not sub:
            raise cred_exc
        user: Optional[UserORM] = db.query(UserORM).get(sub)
    except JWTError:
        raise cred_exc
    if user is None or not user.is_active:
        raise cred_exc
    return user


# ========================
# routes
# ========================

@router.post("/signup", response_model=UserResponse, status_code=201)
def signup(payload: UserSignup, db: Session = Depends(get_db)):
    # 唯一性校验
    if db.query(UserORM).filter(UserORM.username == payload.username).first():
        raise HTTPException(status_code=409, detail="Username already exists")
    if db.query(UserORM).filter(UserORM.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already exists")

    user = UserORM(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password.get_secret_value() if hasattr(payload.password, "get_secret_value") else payload.password),
        is_active=True,
        is_admin=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse(id=user.id, username=user.username, email=user.email, created_at=user.created_at)  # type: ignore[arg-type]


@router.post("/login", response_model=Token)
def login(
    form: OAuth2PasswordRequestForm = Depends(),  # 支持标准 OAuth2 表单
    db: Session = Depends(get_db),
):
    user: Optional[UserORM] = db.query(UserORM).filter(UserORM.username == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is disabled")
    return Token(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserResponse)
def me(current: UserORM = Depends(get_current_user)):
    return UserResponse(id=current.id, username=current.username, email=current.email, created_at=current.created_at)  # type: ignore[arg-type]


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None


@router.patch("/me", response_model=UserResponse)
def update_me(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current: UserORM = Depends(get_current_user),
):
    if payload.username and payload.username != current.username:
        if db.query(UserORM).filter(UserORM.username == payload.username).first():
            raise HTTPException(status_code=409, detail="Username already exists")
        current.username = payload.username
    if payload.email and payload.email != current.email:
        if db.query(UserORM).filter(UserORM.email == payload.email).first():
            raise HTTPException(status_code=409, detail="Email already exists")
        current.email = payload.email
    if payload.password:
        current.password_hash = hash_password(payload.password)

    db.add(current)
    db.commit()
    db.refresh(current)
    return UserResponse(id=current.id, username=current.username, email=current.email, created_at=current.created_at)  # type: ignore[arg-type]


@router.get("", response_model=List[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current: UserORM = Depends(get_current_user),
):
    if not current.is_admin:
        raise HTTPException(status_code=403, detail="Admins only")
    users = db.query(UserORM).order_by(UserORM.created_at.desc()).all()
    return [UserResponse(id=u.id, username=u.username, email=u.email, created_at=u.created_at) for u in users]  # type: ignore[arg-type]


from fastapi import APIRouter, HTTPException
from api.models.schemas import UserSignup, UserLogin, UserResponse

router = APIRouter()

fake_users_db = {}

@router.post("/signup", response_model=UserResponse)
def signup(user: UserSignup):
    if user.username in fake_users_db:
        raise HTTPException(status_code=400, detail="User already exists.")
    fake_users_db[user.username] = user
    return UserResponse(username=user.username, email=user.email)

@router.post("/login")
def login(user: UserLogin):
    if user.username not in fake_users_db:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": "fake-jwt-token", "username": user.username}