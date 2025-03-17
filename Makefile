.DEFAULT_GOAL := test

CONTAINER_ENGINE ?= $(shell which podman >/dev/null 2>&1 && echo podman || echo docker)

.PHONY: format
format:
	uv run ruff check
	uv run ruff format

.PHONY: test
test:
	@for d in $(shell find packages -mindepth 1 -maxdepth 1 -type d); do \
		$(MAKE) -C $$d test || exit 1; \
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

.PHONY: generate-client
generate-client:
	@rm -rf packages/automated_actions_client/automated_actions_client/*
	docker compose run --remove-orphans generate-automated-actions-client
	@touch packages/automated_actions_client/automated_actions_client/py.typed
