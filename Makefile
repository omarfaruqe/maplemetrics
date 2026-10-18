.PHONY: up down test lint fmt refresh audit

up:
	cp -n .env.example .env || true
	docker compose up --build

down:
	docker compose down

test:
	pytest

lint:
	ruff check . && ruff format --check .

fmt:
	ruff check --fix . && ruff format .

refresh:
	docker compose run --rm --build refresh

audit:
	bandit -q -r apps config -c pyproject.toml
	pip-audit -r requirements.txt