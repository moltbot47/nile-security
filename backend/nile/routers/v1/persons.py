"""Person API endpoints — profiles, valuation, oracle events."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from nile.core.database import get_db
from nile.models.oracle_event import OracleEvent
from nile.models.person import Person
from nile.models.soul_token import SoulToken
from nile.models.valuation_snapshot import ValuationSnapshot
from nile.schemas.person import (
    CategoryCount,
    OracleEventResponse,
    PersonCreate,
    PersonListItem,
    PersonResponse,
    PersonUpdate,
    ValuationSnapshotResponse,
)

router = APIRouter()


@router.post("", response_model=PersonResponse, status_code=201)
async def create_person(
    req: PersonCreate, db: AsyncSession = Depends(get_db)
) -> PersonResponse:
    """Create a new person profile."""
    existing = await db.execute(select(Person).where(Person.slug == req.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(409, f"Person with slug '{req.slug}' already exists")

    person = Person(
        display_name=req.display_name,
        slug=req.slug,
        bio=req.bio,
        avatar_url=req.avatar_url,
        banner_url=req.banner_url,
        category=req.category,
        tags=req.tags,
        social_links=req.social_links,
    )
    db.add(person)
    await db.flush()
    await db.commit()
    await db.refresh(person)
    return _to_response(person)


@router.get("", response_model=list[PersonListItem])
async def list_persons(
    category: str | None = None,
    verification: str | None = None,
    search: str | None = None,
    sort: str = "score",
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> list[PersonListItem]:
    """List and search persons."""
    query = select(Person).options(selectinload(Person.soul_token))

    if category:
        query = query.where(Person.category == category)
    if verification:
        query = query.where(Person.verification_level == verification)
    if search:
        query = query.where(Person.display_name.ilike(f"%{search}%"))

    if sort == "score":
        query = query.order_by(Person.nile_total_score.desc())
    elif sort == "newest":
        query = query.order_by(Person.created_at.desc())
    elif sort == "name":
        query = query.order_by(Person.display_name.asc())

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    persons = result.scalars().all()

    return [_to_list_item(p) for p in persons]


@router.get("/trending", response_model=list[PersonListItem])
async def trending_persons(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> list[PersonListItem]:
    """List persons with highest trading volume."""
    query = (
        select(Person)
        .join(SoulToken, Person.id == SoulToken.person_id)
        .options(selectinload(Person.soul_token))
        .order_by(SoulToken.volume_24h_usd.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    persons = result.scalars().all()
    return [_to_list_item(p) for p in persons]


@router.get("/categories", response_model=list[CategoryCount])
async def list_categories(
    db: AsyncSession = Depends(get_db),
) -> list[CategoryCount]:
    """List categories with person counts."""
    query = (
        select(Person.category, func.count(Person.id).label("count"))
        .group_by(Person.category)
        .order_by(func.count(Person.id).desc())
    )
    result = await db.execute(query)
    return [CategoryCount(category=row[0], count=row[1]) for row in result.all()]


@router.get("/{person_id}", response_model=PersonResponse)
async def get_person(
    person_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> PersonResponse:
    """Get person profile with NILE scores."""
    query = (
        select(Person)
        .where(Person.id == person_id)
        .options(selectinload(Person.soul_token))
    )
    result = await db.execute(query)
    person = result.scalar_one_or_none()
    if not person:
        raise HTTPException(404, "Person not found")
    return _to_response(person)


@router.patch("/{person_id}", response_model=PersonResponse)
async def update_person(
    person_id: uuid.UUID,
    req: PersonUpdate,
    db: AsyncSession = Depends(get_db),
) -> PersonResponse:
    """Update person profile."""
    query = select(Person).where(Person.id == person_id)
    result = await db.execute(query)
    person = result.scalar_one_or_none()
    if not person:
        raise HTTPException(404, "Person not found")

    update_data = req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(person, key, value)

    await db.flush()
    await db.commit()
    await db.refresh(person)
    return _to_response(person)


@router.get("/{person_id}/valuation-history", response_model=list[ValuationSnapshotResponse])
async def valuation_history(
    person_id: uuid.UUID,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[ValuationSnapshotResponse]:
    """Get valuation snapshots over time."""
    query = (
        select(ValuationSnapshot)
        .where(ValuationSnapshot.person_id == person_id)
        .order_by(ValuationSnapshot.computed_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    return [ValuationSnapshotResponse.model_validate(s) for s in result.scalars().all()]


@router.get("/{person_id}/oracle-events", response_model=list[OracleEventResponse])
async def oracle_events(
    person_id: uuid.UUID,
    status: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[OracleEventResponse]:
    """Get oracle events for a person."""
    query = (
        select(OracleEvent)
        .where(OracleEvent.person_id == person_id)
    )
    if status:
        query = query.where(OracleEvent.status == status)
    query = query.order_by(OracleEvent.created_at.desc()).limit(limit)

    result = await db.execute(query)
    return [OracleEventResponse.model_validate(e) for e in result.scalars().all()]


# --- Helpers ---


def _to_response(person: Person) -> PersonResponse:
    token = person.soul_token if hasattr(person, "soul_token") else None
    return PersonResponse(
        id=person.id,
        display_name=person.display_name,
        slug=person.slug,
        bio=person.bio,
        avatar_url=person.avatar_url,
        banner_url=person.banner_url,
        verification_level=person.verification_level,
        category=person.category,
        tags=person.tags or [],
        social_links=person.social_links or {},
        nile_name_score=float(person.nile_name_score or 0),
        nile_image_score=float(person.nile_image_score or 0),
        nile_likeness_score=float(person.nile_likeness_score or 0),
        nile_essence_score=float(person.nile_essence_score or 0),
        nile_total_score=float(person.nile_total_score or 0),
        created_at=person.created_at,
        token_symbol=token.symbol if token else None,
        token_price_usd=float(token.current_price_usd) if token else None,
        token_market_cap_usd=float(token.market_cap_usd) if token else None,
    )


def _to_list_item(person: Person) -> PersonListItem:
    token = person.soul_token if hasattr(person, "soul_token") else None
    return PersonListItem(
        id=person.id,
        display_name=person.display_name,
        slug=person.slug,
        avatar_url=person.avatar_url,
        verification_level=person.verification_level,
        category=person.category,
        nile_total_score=float(person.nile_total_score or 0),
        token_symbol=token.symbol if token else None,
        token_price_usd=float(token.current_price_usd) if token else None,
        token_market_cap_usd=float(token.market_cap_usd) if token else None,
    )
