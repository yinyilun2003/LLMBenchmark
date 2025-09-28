# api/routers/v1/health.py
from fastapi import APIRouter
from core.db import ping

router = APIRouter(tags=["Health"])

@router.get("/healthz", summary="Liveness probe")
def healthz():
    return {"ok": True}

@router.get("/ready", summary="Readiness probe")
def ready():
    return {"ready": ping()}

@router.get("/version", summary="API version")
def version():
    return {"name": "LLM Benchmark API", "version": "1.0"}
