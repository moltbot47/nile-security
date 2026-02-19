"""Pydantic schemas for benchmark runs."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class BenchmarkCreate(BaseModel):
    split: str = "all"
    mode: str  # detect, patch, exploit
    agent: str = "claude-opus-4-6"
    baseline_agent: str | None = None


class BenchmarkResponse(BaseModel):
    id: uuid.UUID
    split: str
    mode: str
    agent: str
    total_score: float
    max_score: float
    score_pct: float
    audit_results: list
    baseline_agent: str | None
    baseline_score_pct: float | None
    status: str
    started_at: datetime
    finished_at: datetime | None
    metadata: dict

    model_config = {"from_attributes": True}


class BenchmarkBaseline(BaseModel):
    agent: str
    mode: str
    score_pct: float
    source: str  # "evmbench_published" or "nile_run"
