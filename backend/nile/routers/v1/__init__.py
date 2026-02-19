"""API v1 router aggregation."""

from fastapi import APIRouter

from nile.routers.v1.benchmarks import router as benchmarks_router
from nile.routers.v1.contracts import router as contracts_router
from nile.routers.v1.health import router as health_router
from nile.routers.v1.kpis import router as kpis_router
from nile.routers.v1.scans import router as scans_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router, tags=["health"])
api_router.include_router(contracts_router, prefix="/contracts", tags=["contracts"])
api_router.include_router(scans_router, prefix="/scans", tags=["scans"])
api_router.include_router(kpis_router, prefix="/kpis", tags=["kpis"])
api_router.include_router(benchmarks_router, prefix="/benchmarks", tags=["benchmarks"])
