# AI Agent Instructions

This file provides guidance to any AI agents we use, e.g. Claude Code (claude.ai/code) when working with code in this repository.

## Important Instruction Reminders

Do what has been asked; nothing more, nothing less.
ALWAYS follow the instructions provided in this file!
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files but ask the User if they want you to create one. Only create documentation files if explicitly requested by the User.

## Common Development Commands

### Environment Setup

- `make dev-env` - Set up development environment with uv (creates virtual environment and installs dependencies)
- `source .venv/bin/activate` - Activate the virtual environment

### Testing and Code Quality

- `make test` - Run tests for all packages
- `make format` - Run ruff linting and formatting checks
- `uv run ruff check` - Lint code with ruff
- `uv run ruff format` - Format code with ruff
- `uv run mypy` - Type checking with mypy
- `uv run pytest -vv --cov=<package> --cov-report=term-missing --cov-report xml` - Run tests with coverage for specific package

### Building and Running

- `docker compose up automated-actions` - Run the application locally with dependencies (LocalStack for AWS services)
- `make build` - Build test container
- `make prod` - Build production container
- `make generate-client` - Regenerate the automated-actions-client from OpenAPI spec

### Package-Specific Testing

Each package has its own Makefile with test commands. Run tests for individual packages:

```bash
cd packages/automated_actions && make test
cd packages/automated_actions_cli && make test
```

## Architecture Overview

This is a microservices-based automated actions system with the following key components:

### Core Packages (in packages/ directory)

- **automated_actions**: FastAPI server + Celery workers - the core application
- **automated_actions_client**: Auto-generated Python HTTP client from OpenAPI spec
- **automated_actions_cli**: Command-line interface for users
- **automated_actions_utils**: Shared utilities (AWS API, Vault, OpenShift clients, GraphQL)
- **integration_tests**: End-to-end integration tests
- **opa**: Open Policy Agent authorization policies (Rego files)

### Technology Stack

- **Backend**: Python 3.x with FastAPI for API server
- **Task Queue**: Celery with AWS SQS as message broker
- **Database**: AWS DynamoDB for action state storage
- **Authentication**: OIDC via Red Hat SSO
- **Authorization**: Open Policy Agent (OPA) with Rego policies
- **Package Management**: uv for Python dependency management
- **Code Quality**: Ruff for linting/formatting, mypy for type checking

### Application Structure

The FastAPI server (`automated_actions/`) handles:

- Authentication via Red Hat SSO (OIDC)
- Authorization via OPA policy evaluation
- Action validation and throttling
- Task queuing to Celery workers
- Action status tracking in DynamoDB

Celery workers execute actions by:

- Fetching configuration from qontract-server (GraphQL)
- Retrieving secrets from HashiCorp Vault
- Interacting with target systems (AWS, OpenShift)
- Updating action status in DynamoDB

### Key Directories

- `automated_actions/api/v1/views/` - FastAPI endpoint definitions
- `automated_actions/celery/` - Celery task implementations organized by action type
- `automated_actions/db/models/` - DynamoDB model definitions
- `automated_actions_utils/` - Shared client libraries for AWS, Vault, OpenShift, GraphQL

## Configuration

- Local configuration in `settings.conf` (git-ignored)
- Environment variables prefixed with `AA_` for app settings, `OPA_` for policy agent
- See `settings.md` for comprehensive configuration reference
- Docker Compose setup uses LocalStack for local AWS service emulation

## Development

### Development Philosophy

- **Type Safety**: ALWAYS use complete type hints - this is non-negotiable for all Python code
- **Simplicity**: Write simple, straightforward code
- **Readability**: Make code easy to understand
- **Performance**: Consider performance without sacrificing readability
- **Maintainability**: Write code that's easy to update
- **Testability**: Ensure code is testable and use dependency injection where possible
- **Reusability**: Create reusable components and functions
- **Modularity**: Organize code into logical modules
- **Less Code = Less Debt**: Minimize code footprint
- **Consistency**: Follow established patterns and conventions in the codebase

### Coding Best Practices

- **Early Returns**: Use to avoid nested conditions
- **Descriptive Names**: Use clear variable/function names (prefix handlers with "handle")
- **Constants Over Functions**: Use constants where possible
- **DRY Code**: Don't repeat yourself
- **Functional Style**: Prefer functional, immutable approaches when not verbose
- **Minimal Changes**: Only modify code related to the task at hand
- **Function Ordering**: Define composing functions before their components
- **TODO Comments**: Mark issues in existing code with "TODO:" prefix
- **Simplicity**: Prioritize simplicity and readability over clever solutions
- **Build Iteratively** Start with minimal functionality and verify it works before adding complexity
- **Run Tests**: Test your code frequently with realistic inputs and validate outputs
- **Functional Code**: Use functional and stateless approaches where they improve clarity
- **Clean logic**: Keep core logic clean and push implementation details to the edges
- **File Organization**: Balance file organization with simplicity - use an appropriate number of files for the project scale
- **Configuration**: Use environment variables for configuration

### Python Code Style

- **ALWAYS use complete type hints**: Every function parameter and return value must have type annotations
- Follow PEP 8 style guide
- Use Python 3.11+ features
- Use f-strings for string formatting
- Use `dataclasses` or `pydantic` for data structures
- Use docstrings for all public methods
- Use `typing.Protocol` for defining interfaces
- Use `typing.Literal` for fixed values
- Use `pytest` for testing and use `pytest.fixture` for reusable test setup
- **ALWAYS use pytest methods instead**  of class-based approach
- Use `ruff` for linting and formatting
- Use `mypy` for type checking

## Development Workflow

### Adding New Actions

Follow the checklist in `docs/development-guides/implementing-new-actions.md`:

1. Define 3rd party interfaces in `automated_actions_utils`
2. Create FastAPI endpoints in `automated_actions/api/v1/views/`
3. Implement Celery tasks in `automated_actions/celery/<action_type>/`
4. Write unit and integration tests
5. Regenerate client with `make generate-client`
6. Update documentation in `actions.md`

### Testing Strategy

- Unit tests for individual components
- Integration tests that test end-to-end workflows
- Use LocalStack for AWS service mocking in development
- Test both API endpoints and Celery task execution

### Workspace Structure

This is a uv workspace with multiple packages. The root `pyproject.toml` defines workspace members. Each package has its own `pyproject.toml` with specific dependencies and test configurations.

## Type Hints - MANDATORY

- CRITICAL: All Python code MUST use complete type hints
  - Every function parameter must have type annotations
  - Every function must have return type annotation (use `-> None` for void functions)
- Use proper imports from `typing` or `collections.abc` module when needed
- Use Python 3.11+ features like `str | None` for optional types, and use build-in types like `list`, `dict`, `set`, etc. directly
- Prefer generics over concrete types, e.g. `Iterable[str]` instead of `list[str]` or `Mapping[str, int]` instead of `dict[str, int]`
- Example:

```python

from unittest.mock import MagicMock

def my_function(param: str, optional_param: int | None = None) -> None:
    pass

def process_data(items: Iterable[Mapping[str, str]]) -> dict[str, int]:
    return {"count": len([for i in items if i.get("status") == "active"])}
```
