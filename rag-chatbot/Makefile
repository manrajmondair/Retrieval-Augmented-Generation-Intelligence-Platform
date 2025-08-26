SHELL := /bin/bash

.PHONY: up down dev seed test itest format lint typecheck bench eval postman

up:
	docker compose up -d --build

down:
	docker compose down -v

dev:
	UVICORN_WORKERS=1 uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

seed:
	bash scripts/seed.sh

test:
	pytest -q --maxfail=1 --disable-warnings

itest:
	pytest -q -m integration --maxfail=1 --disable-warnings

format:
	black . && ruff check --fix .

lint:
	ruff check .

typecheck:
	mypy app

bench:
	bash scripts/bench.sh

eval:
	python -m app.evals.harness --n 50 --store $${VECTOR_STORE:-qdrant}

postman:
	bash scripts/export_postman_collection.sh

