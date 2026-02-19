"""Pydantic schemas for Person endpoints."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class PersonCreate(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=256)
    slug: str = Field(..., min_length=1, max_length=128, pattern=r"^[a-z0-9-]+$")
    bio: str | None = None
    avatar_url: str | None = None
    banner_url: str | None = None
    category: str = "general"
    tags: list[str] = Field(default_factory=list)
    social_links: dict[str, str] = Field(default_factory=dict)


class PersonUpdate(BaseModel):
    display_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    banner_url: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    social_links: dict[str, str] | None = None
    verification_level: str | None = None


class PersonResponse(BaseModel):
    id: uuid.UUID
    display_name: str
    slug: str
    bio: str | None = None
    avatar_url: str | None = None
    banner_url: str | None = None
    verification_level: str
    category: str
    tags: list[str]
    social_links: dict[str, str]
    nile_name_score: float
    nile_image_score: float
    nile_likeness_score: float
    nile_essence_score: float
    nile_total_score: float
    created_at: datetime

    # Optional token info (populated if soul token exists)
    token_symbol: str | None = None
    token_price_usd: float | None = None
    token_market_cap_usd: float | None = None

    model_config = {"from_attributes": True}


class PersonListItem(BaseModel):
    id: uuid.UUID
    display_name: str
    slug: str
    avatar_url: str | None = None
    verification_level: str
    category: str
    nile_total_score: float
    token_symbol: str | None = None
    token_price_usd: float | None = None
    token_market_cap_usd: float | None = None

    model_config = {"from_attributes": True}


class ValuationSnapshotResponse(BaseModel):
    id: uuid.UUID
    name_score: float
    image_score: float
    likeness_score: float
    essence_score: float
    total_score: float
    fair_value_usd: float
    trigger_type: str
    computed_at: datetime

    model_config = {"from_attributes": True}


class OracleEventResponse(BaseModel):
    id: uuid.UUID
    event_type: str
    source: str
    headline: str
    impact_score: int
    confidence: float
    status: str
    confirmations: int
    rejections: int
    created_at: datetime

    model_config = {"from_attributes": True}


class CategoryCount(BaseModel):
    category: str
    count: int
