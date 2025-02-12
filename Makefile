.DEFAULT_GOAL := test

CONTAINER_ENGINE ?= $(shell which podman >/dev/null 2>&1 && echo podman || echo docker)

.PHONY: format
format:
	uv run ruff check
	uv run ruff format

.PHONY: test
test:
	@for d in $(shell find packages -mindepth 1 -maxdepth 1 -type d); do \
		cd $$d; \
		uv run ruff check --no-fix || exit 1; \
		uv run ruff format --check || exit 1; \
		uv run mypy || exit 1; \
		uv run pytest -vv --cov=`basename $$d` --cov-report=term-missing --cov-report xml || exit 1; \
		cd -; \
	done

.PHONY: build
build:
	$(CONTAINER_ENGINE) build -t automated-actions:test --target test .

.PHONY: build
prod:
	$(CONTAINER_ENGINE) build -t automated-actions:prod --target prod .

.PHONY: dev-env
dev-env:
	uv sync --all-packages

.PHONY: kill-uvicorn
kill-uvicorn:
	@pkill -KILL -f bin/uvicorn || true
	@pkill -KILL -f "from multiprocessing.spawn import spawn_main" || true

.PHONY: generate-client
generate-client: kill-uvicorn
	@./app.sh &
	@sleep 3
	openapi-python-client generate \
		--url http://localhost:8080/docs/openapi.json \
		--meta none --output-path packages/automated_actions_client/automated_actions_client \
		--custom-template-path=openapi_python_client_templates \
		--overwrite
	@make kill-uvicorn
