# `automated_actions_client` Package 🤖🐍

Welcome, developer, to the `automated_actions_client` package! This package provides a Python client library for interacting with the `automated_actions` API server.

## 🎯 Overview

The primary purpose of this client is to offer a convenient, type-safe, and Pythonic way to make API calls to the `automated_actions` service. It is **auto-generated** based on the OpenAPI (formerly Swagger) specification provided by the `automated_actions` server.

This package includes:

* A Python module that maps API operations to Python methods.
* Pydantic models for API request and response bodies, ensuring data validation and providing editor auto-completion.
* Auto-generated [CLI](../automated_actions_cli/) commands using Typer, built from the same OpenAPI specification.

## 🛠️ Generation Process

### Based on OpenAPI Schema

The client code is not manually written but **generated automatically** from the OpenAPI 3.x schema. This schema is typically exposed by the `automated_actions` FastAPI server (e.g., at `/openapi.json`). This ensures that the client stays in sync with the API's capabilities.

### `openapi-python-client`

We use the [openapi-python-client](https://github.com/openapi-generators/openapi-python-client) tool to perform the generation. This tool takes the OpenAPI schema as input and outputs the Python client code.

### `make generate-client`

To regenerate the client (e.g., after the `automated_actions` API has changed), you can use the following command from the **project root**:

```bash
make generate-client
```

This command typically performs the following steps:

1. Ensures the `automated_actions` server is running and its OpenAPI schema is accessible (or fetches a static schema file).
2. Invokes `openapi-python-client` with the appropriate configuration (input schema URL/file, output directory, custom templates).
3. Overwrites the existing client code in this package with the newly generated version.

**Important:** After regenerating the client, always review the changes and run tests to ensure compatibility.

## ✨ Key Features & Structure

### Client Class

The core of the generated client is usually a class (e.g., `AuthenticatedClient` or `Client`) that provides methods for each API endpoint.

```python
# Example Usage (conceptual)
from automated_actions_client import AuthenticatedClient
from automated_actions_client.models import ActionRequest, ActionStatus
from automated_actions_client.api.actions import submit_action, get_action_status
from automated_actions_client.types import Response

# Assuming client is initialized and authenticated
client = AuthenticatedClient(base_url="http://localhost:8080", token="your-auth-token")

# Submit an action
action_data = ActionRequest(action_name="restart_pod", parameters={"pod_name": "my-app-123"})
response: Response[ActionStatus] = submit_action.sync(client=client, json_body=action_data)

if response.status_code == 202 and response.parsed:
    task_id = response.parsed.task_id
    print(f"Action submitted, task ID: {task_id}")
```

See our [integration tests](../integration_tests/tests/test_views_user.py) for more examples.

### Pydantic Models

All request and response bodies, as well as complex parameters, are represented by Pydantic models. These are typically found in `automated_actions_client/models/`. This provides:

* Data validation.
* Type hints for better static analysis and auto-completion.
* Easy serialization and deserialization.

### API Modules

API operations are often grouped into modules corresponding to their tags in the OpenAPI specification (e.g., `automated_actions_client/api/actions.py`, `automated_actions_client/api/users.py`). Each module contains functions for synchronous and asynchronous calls to the endpoints.

### CLI Commands (via Custom Templates) 💻

This client package might also generate Command Line Interface (CLI) commands using [Typer](https://typer.tiangolo.com/). This is achieved by using **custom templates** with `openapi-python-client`.

* **Custom Templates:** These templates are located in a directory like `openapi_python_client_templates/` (often at the project root or within this package's parent). They instruct `openapi-python-client` on how to generate Typer app structures and commands based on the OpenAPI paths and operations.
* **Functionality:** This allows users to interact with the API directly from the command line using a familiar CLI structure, with arguments and options derived from the API parameters.
* **Entry Point:** The generated CLI might have an entry point defined in `pyproject.toml` (e.g., `automated-actions-client ...`) or be part of a larger CLI tool.

The `make generate-client` command should also handle the generation of these CLI components if custom templates are configured.

## 🚀 Development & Contribution

### When to Regenerate

You should regenerate the client whenever:

* The `automated_actions` API's OpenAPI schema changes (e.g., new endpoints, modified models, changed parameters).
* The version of `openapi-python-client` is updated, and you want to leverage new features or bug fixes from the generator.
* The custom templates for CLI generation are modified.

### Testing

See [tests](./tests/) for unit tests and [integration tests](../integration_tests/) that validate the generated client against the actual API. These tests ensure that the client behaves as expected and that any changes in the API are reflected correctly in the client.

### Release Process

Please refer to the main project [README.md](/README.md) for the release process, as it typically includes steps for versioning, changelogs, and deployment.
