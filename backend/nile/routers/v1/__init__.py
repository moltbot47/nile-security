"""API v1 router aggregation."""

from fastapi import APIRouter

from nile.routers.v1.agents import router as agents_router
from nile.routers.v1.benchmarks import router as benchmarks_router
from nile.routers.v1.contracts import router as contracts_router
from nile.routers.v1.events import router as events_router
from nile.routers.v1.health import router as health_router
from nile.routers.v1.kpis import router as kpis_router
from nile.routers.v1.oracle import router as oracle_router
from nile.routers.v1.persons import router as persons_router
from nile.routers.v1.scans import router as scans_router
from nile.routers.v1.soul_tokens import router as soul_tokens_router
from nile.routers.v1.tasks import router as tasks_router
from nile.routers.v1.trading import router as trading_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router, tags=["health"])
api_router.include_router(contracts_router, prefix="/contracts", tags=["contracts"])
api_router.include_router(scans_router, prefix="/scans", tags=["scans"])
api_router.include_router(kpis_router, prefix="/kpis", tags=["kpis"])
api_router.include_router(benchmarks_router, prefix="/benchmarks", tags=["benchmarks"])
api_router.include_router(agents_router, prefix="/agents", tags=["agents"])
api_router.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
api_router.include_router(events_router, prefix="/events", tags=["events"])
api_router.include_router(persons_router, prefix="/persons", tags=["persons"])
api_router.include_router(soul_tokens_router, prefix="/soul-tokens", tags=["soul-tokens"])
api_router.include_router(trading_router, prefix="/trading", tags=["trading"])
api_router.include_router(oracle_router, prefix="/oracle", tags=["oracle"])
