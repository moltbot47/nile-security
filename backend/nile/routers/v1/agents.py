"""Agent registry API — register, manage, and query ecosystem agents."""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nile.core.auth import (
    create_agent_token,
    generate_api_key,
    get_current_agent,
    hash_api_key,
)
from nile.core.database import get_db
from nile.core.event_bus import publish_event
from nile.models.agent import Agent
from nile.models.agent_contribution import AgentContribution

router = APIRouter()


# --- Schemas ---


class AgentRegisterRequest(BaseModel):
    name: str
    description: str | None = None
    version: str = "0.1.0"
    owner_id: str
    capabilities: list[str] = []
    config_schema: dict = {}
    api_endpoint: str | None = None
    docker_image: str | None = None


class AgentRegisterResponse(BaseModel):
    id: str
    name: str
    api_key: str
    jwt_token: str
    status: str


class AgentResponse(BaseModel):
    id: str
    name: str
    description: str | None
    version: str
    owner_id: str
    capabilities: list
    status: str
    nile_score_total: float
    nile_score_name: float
    nile_score_image: float
    nile_score_likeness: float
    nile_score_essence: float
    total_points: int
    total_contributions: int
    is_online: bool
    created_at: str


class AgentUpdateRequest(BaseModel):
    description: str | None = None
    version: str | None = None
    capabilities: list[str] | None = None
    config_schema: dict | None = None
    api_endpoint: str | None = None
    docker_image: str | None = None


class ContributionResponse(BaseModel):
    id: str
    contribution_type: str
    severity_found: str | None
    verified: bool
    points_awarded: int
    summary: str | None
    created_at: str


class LeaderboardEntry(BaseModel):
    id: str
    name: str
    total_points: int
    total_contributions: int
    nile_score_total: float
    capabilities: list
    is_online: bool


# --- Endpoints ---


@router.post("/register", response_model=AgentRegisterResponse)
async def register_agent(req: AgentRegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check for duplicate name
    existing = await db.execute(select(Agent).where(Agent.name == req.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Agent name already taken")

    api_key = generate_api_key()
    agent = Agent(
        name=req.name,
        description=req.description,
        version=req.version,
        owner_id=req.owner_id,
        capabilities=req.capabilities,
        config_schema=req.config_schema,
        api_endpoint=req.api_endpoint,
        docker_image=req.docker_image,
        api_key_hash=hash_api_key(api_key),
        status="active",
    )
    db.add(agent)
    await db.flush()

    jwt_token = create_agent_token(str(agent.id))

    await publish_event(
        event_type="agent.joined",
        actor_id=str(agent.id),
        metadata={"name": agent.name, "capabilities": agent.capabilities},
        db=db,
    )

    await db.commit()

    return AgentRegisterResponse(
        id=str(agent.id),
        name=agent.name,
        api_key=api_key,
        jwt_token=jwt_token,
        status=agent.status,
    )


@router.get("", response_model=list[AgentResponse])
async def list_agents(
    status: str | None = None,
    capability: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Agent)
    if status:
        query = query.where(Agent.status == status)
    query = query.order_by(Agent.total_points.desc())

    result = await db.execute(query)
    agents = result.scalars().all()

    # Filter by capability in Python (JSONB array contains)
    if capability:
        agents = [a for a in agents if capability in (a.capabilities or [])]

    return [
        AgentResponse(
            id=str(a.id),
            name=a.name,
            description=a.description,
            version=a.version,
            owner_id=a.owner_id,
            capabilities=a.capabilities or [],
            status=a.status,
            nile_score_total=float(a.nile_score_total),
            nile_score_name=float(a.nile_score_name),
            nile_score_image=float(a.nile_score_image),
            nile_score_likeness=float(a.nile_score_likeness),
            nile_score_essence=float(a.nile_score_essence),
            total_points=a.total_points,
            total_contributions=a.total_contributions,
            is_online=a.is_online,
            created_at=a.created_at.isoformat() if a.created_at else "",
        )
        for a in agents
    ]


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
async def leaderboard(
    capability: str | None = None,
    limit: int = 25,
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Agent)
        .where(Agent.status == "active")
        .order_by(Agent.total_points.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    agents = result.scalars().all()

    if capability:
        agents = [a for a in agents if capability in (a.capabilities or [])]

    return [
        LeaderboardEntry(
            id=str(a.id),
            name=a.name,
            total_points=a.total_points,
            total_contributions=a.total_contributions,
            nile_score_total=float(a.nile_score_total),
            capabilities=a.capabilities or [],
            is_online=a.is_online,
        )
        for a in agents
    ]


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return AgentResponse(
        id=str(agent.id),
        name=agent.name,
        description=agent.description,
        version=agent.version,
        owner_id=agent.owner_id,
        capabilities=agent.capabilities or [],
        status=agent.status,
        nile_score_total=float(agent.nile_score_total),
        nile_score_name=float(agent.nile_score_name),
        nile_score_image=float(agent.nile_score_image),
        nile_score_likeness=float(agent.nile_score_likeness),
        nile_score_essence=float(agent.nile_score_essence),
        total_points=agent.total_points,
        total_contributions=agent.total_contributions,
        is_online=agent.is_online,
        created_at=agent.created_at.isoformat() if agent.created_at else "",
    )


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: uuid.UUID,
    req: AgentUpdateRequest,
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    if str(current_agent.id) != str(agent_id):
        raise HTTPException(status_code=403, detail="Can only update your own agent")

    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    for field_name, value in req.model_dump(exclude_none=True).items():
        setattr(agent, field_name, value)

    await db.commit()
    return await get_agent(agent_id, db)


@router.post("/{agent_id}/heartbeat")
async def heartbeat(
    agent_id: uuid.UUID,
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    if str(current_agent.id) != str(agent_id):
        raise HTTPException(status_code=403, detail="Can only heartbeat your own agent")

    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.is_online = True
    agent.last_heartbeat = datetime.now(UTC)
    await db.commit()

    return {"status": "ok", "agent_id": str(agent_id)}


@router.get("/{agent_id}/contributions", response_model=list[ContributionResponse])
async def agent_contributions(
    agent_id: uuid.UUID,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AgentContribution)
        .where(AgentContribution.agent_id == agent_id)
        .order_by(AgentContribution.created_at.desc())
        .limit(limit)
    )
    contributions = result.scalars().all()

    return [
        ContributionResponse(
            id=str(c.id),
            contribution_type=c.contribution_type,
            severity_found=c.severity_found,
            verified=c.verified,
            points_awarded=c.points_awarded,
            summary=c.summary,
            created_at=c.created_at.isoformat() if c.created_at else "",
        )
        for c in contributions
    ]
