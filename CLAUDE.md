# NILE Security Intelligence Platform

## Project Overview
NILE (Name Image Likeness Essence) is a smart contract security intelligence platform that profiles contracts through four dimensions and tracks attacker/defender KPIs. Built to integrate with EVMbench (OpenAI/Paradigm) and support applications to cybersecurity grant programs.

## Tech Stack
- **Backend:** Python 3.11+ / FastAPI / SQLAlchemy 2.0 / asyncpg / Pydantic v2
- **Frontend:** Next.js 16 / React 19 / Tailwind CSS 4 / shadcn/ui / Zustand / Recharts
- **Database:** PostgreSQL 18 / Redis 7
- **Blockchain:** Foundry (Forge/Anvil/Cast) / Slither
- **AI:** Claude API (Anthropic) + OpenAI API
- **Deployment:** Docker Compose on Digital Ocean

## Commands
- `make dev` - Start development environment
- `make lint` - Run ruff (Python) + biome (TypeScript)
- `make test` - Run pytest (backend) + bun test (frontend)
- `make typecheck` - Run type checking
- `make build` - Build Docker images
- `make deploy` - Deploy to production

## Project Structure
- `backend/` - FastAPI application with NILE scoring engine
- `frontend/` - Next.js KPI dashboard
- `evmbench-integration/` - EVMbench benchmark harness integration
- `deploy/` - Docker and deployment configurations
- `docs/` - Architecture docs, ADRs, grant applications

## NILE Scoring Model
Each contract scored 0-100 across four dimensions (25% each):
- **Name** (N): Identity verification, provenance, audit history
- **Image** (I): Security posture, open vulnerabilities, patch cadence
- **Likeness** (L): Pattern matching against known vulnerability signatures
- **Essence** (E): Test coverage, complexity, upgrade risk, dependencies

## Development Guidelines
- All API endpoints under `/api/v1/`
- Use async SQLAlchemy throughout
- Pydantic v2 for all request/response schemas
- All security testing in sandboxed Anvil environments only
- Never interact with live blockchain networks
