# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-06-01

### Added

- 🚀 **Initial Release** of the Automated Actions system!
- **Core API Server (`automated_actions` package):**
  - FastAPI application setup.
  - Endpoints for action submission and status retrieval.
  - Integration with Celery for task queuing via AWS SQS.
  - DynamoDB integration for storing action requests and state.
  - Basic OIDC authentication structure (via Red Hat SSO).
  - Initial OPA integration for authorization (policy definitions to be expanded).
- **Python Client (`automated_actions_client` package):**
  - Auto-generated Python HTTP client from OpenAPI specification.
- **Command Line Interface (`automated_actions_cli` package):**
  - Basic CLI structure for interacting with the API.
  - Initial commands for triggering predefined actions (e.g., `openshift-workload-restart`).
  - Command for creating OPA service account tokens.
- **OPA Policies (`opa` package):**
  - Initial set of Rego policies for basic authorization.
- **Utilities (`automated_actions_utils` package):**
  - Common utility functions for AWS (SQS, DynamoDB) and Vault interactions.
- **Integration Tests (`integration_test` package):**
  - Basic integration tests covering API submission and action flow.
- **Development Environment:**
  - `Makefile` for common development tasks (`dev-env`, `test`, `format`).
  - `docker-compose.yml` for local development with LocalStack.
- **Documentation:**
  - Initial `README.md` for the project.
  - OpenAPI documentation for the API server.
- **Configuration:**
  - Settings management via `pydantic-settings`.
  - Initial structure for action definitions and permissions in `app-interface`.

### Changed

- N/A (Initial Release)

### Deprecated

- N/A (Initial Release)

### Removed

- N/A (Initial Release)

### Fixed

- N/A (Initial Release)

### Security

- N/A (Initial Release)
