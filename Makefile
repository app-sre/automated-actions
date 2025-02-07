.DEFAULT_GOAL := test

CONTAINER_ENGINE ?= $(shell which podman >/dev/null 2>&1 && echo podman || echo docker)

.PHONY: format
format:
	uv run ruff check
	uv run ruff format

.PHONY: test
test:
	uv run ruff check --no-fix
	uv run ruff format --check
	uv run mypy
	uv run pytest -vv --cov=automated_actions --cov-report=term-missing --cov-report xml

.PHONY: build
build:
	$(CONTAINER_ENGINE) build -t automated-actions:test --target test .

.PHONY: dev-env
dev-env:
	uv sync

.PHONY: generate-client
generate-client:
	@./app.sh & echo $$! > app.pid
	openapi-python-client generate --url http://localhost:8080/docs/openapi.json --meta none --output-path automated_actions_client/automated_actions_client --overwrite
	@kill `cat app.pid` && rm app.pid
