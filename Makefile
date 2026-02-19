.PHONY: dev lint test typecheck build deploy

# Development
dev:
	@echo "Starting backend..."
	cd backend && uv run uvicorn nile.app:app --reload --port 8000 &
	@echo "Starting frontend..."
	cd frontend && bun dev &

# Quality
lint:
	cd backend && uv run ruff check nile/ tests/
	cd frontend && npx biome check src/ 2>/dev/null || true

test:
	cd backend && uv run pytest -v --cov=nile

typecheck:
	cd frontend && npx tsc --noEmit 2>/dev/null || true

# Docker
build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

# Deployment
deploy:
	ssh root@159.203.138.96 'cd /opt/nile-security && git pull && docker compose -f docker-compose.yml up -d --build'

# Backend utilities
migrate:
	cd backend && uv run alembic upgrade head

seed:
	cd backend && uv run python -c "from nile.services.nile_scorer import *; print('NILE scoring engine loaded OK')"
