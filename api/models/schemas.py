# schemas.py
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Annotated
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, conint, constr
from datetime import datetime


# ---------------------------
# Auth / User schemas
# ---------------------------

class UserSignup(BaseModel):
    username: Annotated[str, constr(strip_whitespace=True, min_length=3, max_length=50)]
    email: EmailStr
    password: Annotated[str, constr(min_length=8, max_length=128)]  # store hashed in DB, not raw

class UserLogin(BaseModel):
    username: Annotated[str, constr(strip_whitespace=True, min_length=3, max_length=50)]
    password: Annotated[str, constr(min_length=8, max_length=128)]

class UserCreate(UserSignup):
    """Internal use if you separate external signup vs internal creation."""
    pass

class UserResponse(BaseModel):
    id: UUID
    username: str
    email: EmailStr
    created_at: datetime

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: UUID  # user id
    exp: int


# ---------------------------
# Task schemas
# ---------------------------

class TaskStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    canceled = "canceled"

class TaskCreate(BaseModel):
    name: Annotated[str, constr(strip_whitespace=True, min_length=1, max_length=200)]
    model: Annotated[str, constr(strip_whitespace=True, min_length=1, max_length=100)] = Field(
        ..., description="e.g., llama3-8b, qwen3-7b, gemini-2.0"
    )
    route: Annotated[str, constr(strip_whitespace=True, min_length=1, max_length=200)] = Field(
        ..., description="HTTP endpoint or logical route key"
    )
    dataset: Annotated[str, constr(strip_whitespace=True, min_length=1, max_length=200)]
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Adapter-specific parameters, sampling config, headers, etc.",
    )
    concurrency: int = Field(1, ge=1, le=10_000)
    duration_sec: int = Field(60, ge=1, le=86400)
    tags: Optional[List[Annotated[str, constr(strip_whitespace=True, min_length=1, max_length=50)]]] = None

class TaskUpdate(BaseModel):
    """Client-editable fields; status transitions are server-controlled."""
    name: Optional[Annotated[str, constr(strip_whitespace=True, min_length=1, max_length=200)]] = None
    params: Optional[Dict[str, Any]] = None
    concurrency: Optional[Annotated[int, conint(ge=1, le=10_000)]] = None
    duration_sec: Optional[Annotated[int, conint(ge=1, le=86400)]] = None
    tags: Optional[List[Annotated[str, constr(strip_whitespace=True, min_length=1, max_length=50)]]] = None

class TaskResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    model: str
    route: str
    dataset: str
    params: Dict[str, Any]
    concurrency: int
    duration_sec: int
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error: Optional[str] = None  # last error if failed

    class Config:
        orm_mode = True


# ---------------------------
# Run / Metric
# ---------------------------

class RunSummary(BaseModel):
    task_id: UUID
    p50_ms: Optional[int] = None
    p90_ms: Optional[int] = None
    p99_ms: Optional[int] = None
    rps: Optional[float] = None
    error_rate: Optional[float] = None
    cost_usd: Optional[float] = None
    quality: Optional[float] = None

class MetricPoint(BaseModel):
    ts: datetime
    latency_ms: Optional[int] = None
    http_status: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    quality: Optional[float] = None
    error: Optional[str] = None


# ---------------------------
# Pagination + common
# ---------------------------

class PageMeta(BaseModel):
    page: Annotated[int, conint(ge=1)] = 1
    per_page: Annotated[int, conint(ge=1, le=200)] = 20
    total: Annotated[int, conint(ge=0)] = 0

class PaginatedTasks(BaseModel):
    meta: PageMeta
    items: List[TaskResponse]

class ErrorResponse(BaseModel):
    detail: str
