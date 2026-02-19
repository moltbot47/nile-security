"""Agent authentication — JWT tokens and API key validation."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nile.config import settings
from nile.core.database import get_db
from nile.models.agent import Agent

JWT_SECRET = settings.jwt_secret
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 1

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def generate_api_key() -> str:
    return f"nile_{secrets.token_urlsafe(32)}"


def create_agent_token(agent_id: str) -> str:
    payload = {
        "sub": agent_id,
        "exp": datetime.now(UTC) + timedelta(hours=JWT_EXPIRE_HOURS),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_agent_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


async def get_current_agent(
    db: AsyncSession = Depends(get_db),
    api_key: str | None = Security(api_key_header),
    bearer: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> Agent:
    """Extract agent identity from API key or JWT bearer token."""
    agent = None

    # Try API key first
    if api_key:
        key_hash = hash_api_key(api_key)
        result = await db.execute(select(Agent).where(Agent.api_key_hash == key_hash))
        agent = result.scalar_one_or_none()

    # Fall back to JWT bearer
    if agent is None and bearer:
        try:
            payload = decode_agent_token(bearer.credentials)
            agent_id = payload["sub"]
            result = await db.execute(select(Agent).where(Agent.id == agent_id))
            agent = result.scalar_one_or_none()
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as err:
            raise HTTPException(status_code=401, detail="Invalid or expired token") from err

    if agent is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    if agent.status == "suspended":
        raise HTTPException(status_code=403, detail="Agent is suspended")

    return agent


async def get_optional_agent(
    db: AsyncSession = Depends(get_db),
    api_key: str | None = Security(api_key_header),
    bearer: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> Agent | None:
    """Like get_current_agent but returns None instead of raising."""
    if not api_key and not bearer:
        return None
    try:
        return await get_current_agent(db, api_key, bearer)
    except HTTPException:
        return None
