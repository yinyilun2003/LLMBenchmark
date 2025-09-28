# routers/v1/__init__.py
from __future__ import annotations

from fastapi import FastAPI

# 子路由模块
from . import (
    health,
    auth,
    user,
    task,
    runs,
    metrics,
    reports,
    datasets,
    adapters,
    webhooks,
    admin,
    log,
)

# 便于 main 挂载
ALL_ROUTERS = [
    health,
    auth,
    user,
    task,
    runs,
    metrics,
    reports,
    datasets,
    adapters,
    webhooks,
    admin,
    log,
]

__all__ = [
    "health",
    "auth",
    "user",
    "task",
    "runs",
    "metrics",
    "reports",
    "datasets",
    "adapters",
    "webhooks",
    "admin",
    "log",
    "mount_all",
    "ALL_ROUTERS",
]


def mount_all(app: FastAPI, prefix: str = "/api/v1") -> None:
    for r in ALL_ROUTERS:
        app.include_router(r.router, prefix=prefix)
