# api/routers/v1/adapters.py
from __future__ import annotations

import time
from typing import Dict, Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, AnyHttpUrl, Field

from api.routers.v1.user import get_current_user
from api.models.user import User as UserORM

router = APIRouter(prefix="/adapters", tags=["Adapters"])


# ---------- Schemas ----------
class AdapterProbeRequest(BaseModel):
    url: AnyHttpUrl = Field(..., description="Target URL to probe, e.g. https://host:port/health or /v1/chat/completions")
    method: Literal["GET", "POST", "HEAD"] = "GET"
    headers: Optional[Dict[str, str]] = None
    json: Optional[Dict] = Field(default=None, description="JSON body for POST")
    timeout_sec: float = Field(default=5.0, gt=0, le=60, description="Request timeout")


class AdapterProbeResponse(BaseModel):
    ok: bool
    status: Optional[int] = None
    latency_ms: Optional[int] = None
    resp_bytes: Optional[int] = None
    error: Optional[str] = None


# ---------- Endpoints ----------
@router.get("", summary="List registered adapters (placeholder)")
def list_adapters(current: UserORM = Depends(get_current_user)) -> Dict:
    # 你可后续接 DB 表（adapters）返回实际数据
    return {"items": [], "note": "Adapter registry not implemented yet"}


@router.post("/probe", response_model=AdapterProbeResponse, summary="Probe an adapter endpoint")
async def probe_adapter(
    payload: AdapterProbeRequest,
    current: UserORM = Depends(get_current_user),
) -> AdapterProbeResponse:
    try:
        import httpx  # 延迟导入，避免未安装时报模块级错误
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"httpx not installed: {e}. Install with `pip install httpx`.",
        )

    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(follow_redirects=True, verify=False, timeout=payload.timeout_sec) as client:
            if payload.method == "GET":
                resp = await client.get(str(payload.url), headers=payload.headers)
            elif payload.method == "POST":
                resp = await client.post(str(payload.url), headers=payload.headers, json=payload.json)
            elif payload.method == "HEAD":
                resp = await client.head(str(payload.url), headers=payload.headers)
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported method {payload.method}")

        dt_ms = int((time.perf_counter() - t0) * 1000)
        return AdapterProbeResponse(
            ok=resp.is_success,
            status=resp.status_code,
            latency_ms=dt_ms,
            resp_bytes=len(resp.content or b""),
            error=None if resp.is_success else resp.text[:512],
        )
    except httpx.TimeoutException:
        dt_ms = int((time.perf_counter() - t0) * 1000)
        return AdapterProbeResponse(ok=False, status=None, latency_ms=dt_ms, resp_bytes=0, error="timeout")
    except httpx.RequestError as e:
        dt_ms = int((time.perf_counter() - t0) * 1000)
        return AdapterProbeResponse(ok=False, status=None, latency_ms=dt_ms, resp_bytes=0, error=str(e))
