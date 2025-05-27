# `automated_actions` Package 🚀

Welcome, developer, to the core of the Automated Actions system! This package houses the **FastAPI server application** that powers the entire automated actions workflow.

## 🎯 Overview

This package is responsible for:

* **Exposing the API:** Providing HTTP endpoints for clients (like `automated_actions_cli` or AlertManager) to submit action requests and query their status.
* **Request Handling:** Validating incoming requests, performing authentication and authorization.
* **Task Orchestration:** Enqueuing validated action requests into a Celery task queue (AWS SQS).
* **State Management:** Interacting with DynamoDB to store and update the status of actions.
* **Serving Celery Workers:** Defining and running the Celery worker processes that execute the actual action logic.

## 🛠️ Key Components

### API Endpoints

The API is built using **FastAPI**. Key routers and views are typically found in a directory like `automated_actions/api/`.

### Authentication & Authorization 🛡️

* **Authentication:**
  * Primarily handled via **OIDC (OpenID Connect)**, integrating with Red Hat SSO.
  * FastAPI dependencies are used to protect endpoints and extract user information from JWTs.
  * Look for OIDC client configurations in `automated_actions/config.py` or `automated_actions/auth/`.
* **Authorization:**
  * Leverages **Open Policy Agent (OPA)**.
  * The API server queries an OPA instance (configured via `AA_OPA_HOST`) to make authorization decisions.
  * The OPA policies themselves are defined in the separate [`opa` package](../opa/).
  * The API sends context (user info, requested action, parameters) to OPA.
  * Authorization logic within the API can be found in utility functions or FastAPI dependencies that interact with OPA.

### Celery Workers & Tasks 🐘

* **Celery Application:**
  * The Celery app instance is typically initialized in `automated_actions/celery/app.py`.
  * Configuration for brokers (SQS) and backends is managed here or via `automated_actions/config.py`.
* **Task Definitions:**
  * Individual Celery tasks representing specific automated actions (e.g., `restart_pod_task`, `run_db_migration_task`) are defined on `tasks.py` modules under `automated_actions/celery` and added into `automated_actions/celery/app.py` `include` directive.
  * These tasks contain the core logic for interacting with target systems (OpenShift, AWS services, etc.).
  * They utilize utilities from [automated_actions_utils](/packages/automated_actions_utils/) for interacting with Vault, AWS APIs, etc.
  * Tasks are responsible for updating the action's status in DynamoDB upon completion or failure. In order to do that, they take `automated_actions/automated_actions/celery/automated_action_task.py` as base, setting `base=AutomatedActionTask` in the task decorator, see `automated_actions/automated_actions/celery/openshift/tasks.py` as an example.

### Database Interaction (PynamoDB Models) 🗂️

* **PynamoDB:** Used as the ORM-like library for interacting with AWS DynamoDB.
* **Models:**
  * PynamoDB models defining the structure of data stored in DynamoDB are typically located in `automated_actions/db/models/`.
  * These models include attributes for `task_id`, `action_name`, `status`, `user_id`, `created_at`, `updated_at`, arguments, results, etc.
  * Table names are usually dynamically generated based on the environment (e.g., `aa-{settings.environment}-actions`).
* **Database Operations:**
  * Service functions or methods within the API views and Celery tasks handle creating, retrieving, and updating records in DynamoDB using these models.

### Configuration ⚙️

* Managed by `pydantic-settings`.
* Core settings are defined in `automated_actions/config.py` (e.g., `Settings` class).
* Settings can be loaded from environment variables starting with `AA_` prefix.
* This includes AWS credentials/region, SQS queue URLs, DynamoDB table names, OIDC settings, OPA endpoint, etc.

### Error Handling & Logging 📝

* **Custom Exceptions:** Defined in `automated_actions/exceptions.py` for specific error conditions.
* **FastAPI Exception Handlers:** Used to convert custom exceptions into appropriate HTTP responses.
* **Logging:** Standard Python logging is configured, often in `automated_actions/config.py` or a dedicated logging setup module. Ensure logs are structured and provide sufficient context for debugging.

## 🚀 Local Development & Running

See the main project [README.md](/README.md) for instructions on setting up a local development environment.

## 🤝 Contributing to this Package

* Follow the general contributing guidelines in the main project `README.md`.
* Ensure new API endpoints are documented with OpenAPI (via FastAPI's docstrings and Pydantic models).
* Write unit tests for new business logic and Celery tasks.
* Add and enhance the [integration tests](../integration_tests/) for new API endpoints.
* Don't forget to update the [automated-actions-client](../automated_actions_client/) if new API endpoints are added or existing ones are modified.
* Keep dependencies minimal and clearly defined in `pyproject.toml`.
* When adding new Celery tasks, consider queue routing and retry mechanisms.
