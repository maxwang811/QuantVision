.PHONY: help dev down logs migrate seed ingest test test-backend test-frontend lint typegen prod-up prod-down prod-logs smoke

help:
	@echo "QuantVision dev commands:"
	@echo "  make dev          - start full stack via docker-compose"
	@echo "  make down         - stop the stack"
	@echo "  make logs         - tail backend + frontend logs"
	@echo "  make migrate      - run alembic upgrade head inside backend container"
	@echo "  make seed         - seed assets table with S&P 500 + ETFs"
	@echo "  make ingest       - pull historical prices from yfinance for seeded tickers"
	@echo "  make test         - run backend + frontend test suites"
	@echo "  make test-backend - pytest only"
	@echo "  make test-frontend- vitest + playwright"
	@echo "  make lint         - ruff + mypy + eslint + tsc"
	@echo "  make typegen      - regenerate TS types from FastAPI OpenAPI"
	@echo "  make prod-up      - build + start prod images via docker-compose.prod.yml overlay"
	@echo "  make prod-down    - stop the prod stack"
	@echo "  make prod-logs    - tail prod backend + frontend logs"
	@echo "  make smoke        - run end-to-end smoke harness against the dev stack"

dev:
	docker-compose up --build

down:
	docker-compose down

logs:
	docker-compose logs -f backend frontend

migrate:
	docker-compose exec backend alembic upgrade head

seed:
	docker-compose exec backend python scripts/seed_assets.py

ingest:
	docker-compose exec backend python scripts/ingest_prices.py --tickers SPY,AAPL,MSFT,GOOGL,NVDA --years 5

test: test-backend test-frontend

test-backend:
	docker-compose exec backend pytest -n auto --cov=app

test-frontend:
	cd frontend && npm test

lint:
	docker-compose exec backend ruff check .
	docker-compose exec backend mypy app
	cd frontend && npm run lint && npx tsc --noEmit

typegen:
	cd frontend && npm run typegen

prod-up:
	docker-compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml up -d --build

prod-down:
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

prod-logs:
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f backend frontend

smoke:
	./scripts/smoke.sh
