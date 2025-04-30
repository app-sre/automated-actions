.DEFAULT_GOAL := test

CONTAINER_ENGINE ?= $(shell which podman >/dev/null 2>&1 && echo podman || echo docker)

.PHONY: format
format:
	uv run ruff check
	uv run ruff format

.PHONY: test
test:
	@for d in $(wildcard packages/*); do \
		if [ -d "$$d" ]; then \
			$(MAKE) -C $$d test || exit 1; \
		fi \
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

.PHONY: gql-introspection
gql-introspection:
	@uv run qenerate introspection http://localhost:4000/graphql > packages/automated_actions/automated_actions/gql_definitions/introspection.json

.PHONY: gql-query-classes
gql-query-classes:
	@uv run qenerate code -i packages/automated_actions/automated_actions/gql_definitions/introspection.json packages/automated_actions/automated_actions/gql_definitions
	@find packages/automated_actions/automated_actions/gql_definitions -path '*/__pycache__' -prune -o -type d -exec touch "{}/__init__.py" \;

.PHONY: qenerate
qenerate: gql-introspection gql-query-classes
