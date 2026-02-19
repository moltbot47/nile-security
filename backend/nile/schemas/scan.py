"""Pydantic schemas for scan jobs."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class ScanCreate(BaseModel):
    contract_id: uuid.UUID
    mode: str  # detect, patch, exploit
    agent: str = "claude-opus-4-6"
    config: dict = {}
    hint_level: str = "none"


class ScanResponse(BaseModel):
    id: uuid.UUID
    contract_id: uuid.UUID
    status: str
    mode: str
    agent: str
    config: dict
    hint_level: str
    result: dict | None
    result_error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    tokens_used: int
    api_cost_usd: float

    model_config = {"from_attributes": True}
