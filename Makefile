.PHONY: up down logs test shell migrate help

help:
	@echo "  make up        start all containers"
	@echo "  make down      stop containers"
	@echo "  make logs      tail all logs"
	@echo "  make test      run pytest"
	@echo "  make migrate   run alembic upgrade head"
	@echo "  make shell     bash inside flask container"

up:
	cp -n .env.example .env 2>/dev/null || true
	docker compose up --build -d
	@echo "Running on http://localhost:5001"

down:
	docker compose down

logs:
	docker compose logs -f

logs-api:
	docker compose logs -f flask-api

test:
	docker compose exec flask-api pytest tests/ -v

migrate:
	docker compose exec flask-api alembic upgrade head

shell:
	docker compose exec flask-api bash