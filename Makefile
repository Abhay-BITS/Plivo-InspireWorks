.PHONY: install test check lint typecheck run web-build docker-up

install:
	pip install -e ".[dev]"
	cd web && npm install

test:
	pytest --cov=app.ivr --cov=app.telephony --cov-report=term-missing

lint:
	ruff check app/ tests/ scripts/

typecheck:
	mypy app/

check: lint typecheck test

web-build:
	cd web && npm run build

run:
	uvicorn app.main:app --reload

docker-up:
	docker compose up --build
