.PHONY: test
test:
	uv run ruff check --no-fix
	uv run ruff format --check
	uv run mypy
	uv run pytest -vv --cov=$(notdir $(CURDIR)) --cov-report=term-missing --cov-report xml
