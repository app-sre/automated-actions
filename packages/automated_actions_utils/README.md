# `automated_actions_utils` Package 🛠️🔧

Welcome, developer, to the `automated_actions_utils` package! This package serves as a **common library of shared utilities, helper functions, and core API client implementations** used across various parts of the Automated Actions project.

## 🎯 Overview

The primary goal of this package is to promote code reuse, consistency, and maintainability by centralizing common logic that would otherwise be duplicated in other packages. Think of it as the shared toolbox for the Automated Actions ecosystem.

This package is primarily utilized by:

* **`automated_actions` (FastAPI Server & Celery Workers):** For interacting with external services (like AWS, Vault), handling common data transformations, or implementing shared business logic not directly tied to API request/response handling.
* **`integration_test`:** For setting up test data, interacting with services in a controlled manner during tests, or using the same utility functions that the main application uses to ensure consistency.
* Potentially other packages like `automated_actions_cli` if there's complex shared logic beyond simple API calls.

## ✨ Key Features & Potential Contents

This package might contain a variety of utilities, including but not limited to:

* **AWS Client Wrappers:** Simplified clients or helper functions for interacting with AWS services like SQS, DynamoDB, S3, and Secrets Manager.
* **HashiCorp Vault Client Wrapper:** Functions to simplify interaction with HashiCorp Vault for fetching secrets.
* **OpenShift Client Wrapper:** Functions to interact with OpenShift APIs for managing resources like deployments, pods, etc.
* **GQL app-interface Queries & Models:** GQL app-interface queries and models for interacting with the app-interface.

## 🧑‍💻 Development & Usage

### Adding New Utilities

When considering adding a new utility to this package, ask yourself:

* Is this logic likely to be needed by more than one package (e.g., both the server and integration tests)?
* Does it abstract away a common, potentially complex interaction with an external service?
* Does it help in reducing boilerplate code in other packages?

If the answer is yes to one or more of these, `automated_actions_utils` is likely the right place for it.

### Dependencies

* This package should strive to have minimal dependencies to avoid pulling in unnecessary libraries into packages that consume it.
* Dependencies should be clearly defined in its `pyproject.toml`.

### Testing

* Utilities in this package **must be thoroughly unit-tested**.
* Tests should be self-contained and not rely on external services where possible (use mocking).
* Tests are located within the `tests/` directory of this package.

To run tests specifically for this package:

```bash
# From within packages/automated_actions_utils/
make test
```

## 🤝 Contributing to this Package

* Ensure new utilities are well-documented with docstrings explaining their purpose, arguments, and return values.
* Write comprehensive unit tests for all new functionalities.
* Keep functions focused on a single responsibility.
* Avoid circular dependencies with other packages in the monorepo. This package should generally be a foundational layer.
