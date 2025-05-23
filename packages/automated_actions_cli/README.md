# `automated_actions_cli` Package 💻🚀

Welcome, developer, to the `automated_actions_cli` package! This is the command-line interface (CLI) for interacting with the Automated Actions system. It allows users (tenants, SREs) to trigger actions, check their status, and manage other aspects of the system directly from their terminal.

## 🎯 Overview

The `automated_actions_cli` provides a user-friendly way to:

* List available automated actions.
* Trigger predefined actions with necessary parameters.
* Query the status and results of submitted actions.
* Perform administrative tasks (e.g., token generation for service accounts, if applicable).

## ✨ Key Technologies

* **[Typer](https://typer.tiangolo.com/):** The CLI is built using Typer, which makes it easy to create modern, user-friendly command-line applications with excellent support for type hints, auto-completion, and help generation.
* **`automated_actions_client`:** This CLI heavily relies on the `automated_actions_client` package. The client package provides the actual Python functions and Pydantic models for making HTTP requests to the `automated_actions` API server.

## ⚙️ Core Functionality

The CLI acts as a wrapper around the `automated_actions_client`. When a user executes a CLI command:

1. Typer parses the command, subcommands, arguments, and options.
2. Authentication is handled (see [Authentication](#-authentication) section below).
3. The appropriate function from `automated_actions_client` is called with the user-provided parameters.
4. The response from the API (via the client) is then processed and presented to the user in a human-readable format.

Commands are typically structured in a hierarchical way, for example:
`automated-actions <command> [arguments_and_options]`

## 🔑 Authentication (Kerberos)

Authentication with the `automated_actions` API server is primarily handled via Red Hat SSO. Users are expected to have a valid Kerberos ticket-granting ticket (TGT) before using the CLI. This is typically obtained by running `kinit` and available on all Red Hat managed systems.

The CLI does execute `kinit` directly if the user has not already obtained a ticket. This is done using the `kinit` command, which prompts the user for their Kerberos password.

From the user's perspective, if they have a valid Kerberos ticket, authentication should be seamless. The CLI will automatically use the ticket to authenticate API requests. If no ticket is present or it's invalid, API calls will likely fail with an authentication error.

## 💡 Usage Examples

**1. Listing all user available action:**

```bash
$ automated-actions me
---
allowed_actions:
- action-cancel
- action-detail
- action-list
- create-token
- me
- openshift-workload-restart-unthrottled
created_at: 1747919185.209177
email: your-email@address.com
name: Your Name
updated_at: 1747996842.377609
username: your-username
```

**2. List all past actions:**

```bash
$ automated-actions action-list
---
- action_id: b8ff9963-516f-437a-b93c-b7354cd5225d
  created_at: 1747919261.038378
  name: openshift-workload-restart
  owner: your-username
  result: ok
  status: SUCCESS
  task_args:
    cluster: cluster-1
    kind: Pod
    name: example-74d78dbfbf-89rl2
    namespace: namespace-dev
  updated_at: 1747919261.962519
...
```

**2. Triggering an action (e.g., restarting an OpenShift deployment):**

```bash
$ automated-actions openshift-workload-restart --cluster "my-cluster" --namespace "my-namespace" --kind Deployment --name "my-app"
---
- action_id: b8ff9963-516f-437a-b93c-b7354cd5225d
  created_at: 1747919261.038378
  name: openshift-workload-restart
  owner: your-username
  result: ok
  status: PENDING
  task_args:
    cluster: my-cluster
    kind: Deployment
    name: my-app
    namespace: my-namespac
  updated_at: 1747919261.962519
```

## 🧑‍💻 Development

See the main project `README.md` for general development instructions.

### Running the CLI Locally

During development, you can invoke the CLI directly using `automated-actions`:

```bash
automated-actions --help
```

### Relationship with `automated_actions_client`

* **Generated Code:** Many CLI commands in this package might be **auto-generated** based on the OpenAPI specification, similar to how `automated_actions_client` is generated. This is often done using custom templates with `openapi-python-client` that output Typer application structures.
* **Manual Wrappers:** Alternatively, or in addition, there might be manually written Typer commands in this package that import and use functions and models from `automated_actions_client`.
* **Updates:** If the `automated_actions_client` is regenerated due to API changes, the CLI commands (especially auto-generated ones) might also need to be regenerated or updated to reflect those changes. The `make generate-client` (or a similar target like `make generate-cli`) from the project root should handle this.

### Testing

Tests for this package are located within its `tests/` directory. These typically involve:

* Using Typer's `CliRunner` to invoke CLI commands and assert their output and exit codes.
* Mocking the `automated_actions_client` to avoid making real API calls during unit tests.
* Integration tests that do make real API calls to a test instance of the server.

To run tests specifically for this package:

```bash
make test
```

## 🤝 Contributing to this Package

* Follow the general contributing guidelines in the main project `README.md`.
* Ensure new CLI commands are intuitive and provide helpful error messages.
* Add or update tests for any new or modified commands.
* Keep Typer's auto-completion features in mind for a good user experience.
