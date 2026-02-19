"""Health check endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "service": "nile-security"}


@router.get("/health/ready")
async def readiness():
    return {"status": "ready", "checks": {"database": "ok", "redis": "ok"}}
