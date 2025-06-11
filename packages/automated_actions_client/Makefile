.PHONY: test
test:
	uv run ruff check --no-fix
	uv run ruff format --check
	uv run mypy
	uv run pytest -vv --cov=$(notdir $(CURDIR)) --cov-report=term-missing --cov-report xml

# do not print pypi commands to avoid the token leaking to the logs
.SILENT: pypi
.PHONY: pypi
pypi:
	uv build --sdist --wheel --out-dir dist
	UV_PUBLISH_TOKEN=$(shell cat /run/secrets/app-sre-pypi-credentials/token) uv publish
