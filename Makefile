.PHONY: up down test lint fmt

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