# `integration_tests` Package 🧪⚙️

Welcome, developer, to the `integration_tests` package for the Automated Actions system! This package is crucial for ensuring the end-to-end functionality and reliability of the entire system by testing its components working together in a realistic environment.

## 🎯 Overview

The primary purpose of these integration tests is to:

1. **Validate End-to-End Flows:** Verify that actions can be successfully submitted via the API (often using the `automated_actions_client` or `automated_actions_cli`), processed by the `automated_actions` server and Celery workers, and that the expected outcomes occur in target systems.
2. **Test CLI Functionality:** Directly invoke and test the `automated_actions_cli` commands to ensure they behave as expected, correctly interact with the API, and provide appropriate user feedback.
3. **Execute Real Actions:** Unlike unit tests that mock dependencies, these tests often execute real, albeit controlled and potentially destructive, actions against live (but non-production) instances of dependent services (e.g., AppSRE staging applications, resources, and environments).
4. **Build Confidence for Deployments:** Serve as a critical quality gate before promoting changes to stage and production environments.

## ✨ Key Characteristics

* **Client-Driven Tests:** Tests in this package primarily interact with the system from a client's perspective, using:
  * **`automated_actions_client`:** For programmatic interaction with the API endpoints, allowing for precise control over requests and assertions on responses.
  * **`automated_actions_cli`:** For testing the command-line interface directly, ensuring its usability and correctness. This involves running CLI commands as subprocesses and inspecting their output, exit codes, and side effects.
* **Real Environment Interaction:** These tests are designed to run against a deployed instance of the `automated_actions` server and its dependencies (SQS, DynamoDB, OPA, RH SSO, etc.) in a dedicated "integration" environment.
* **Focus on Scenarios:** Tests often cover complete user scenarios, such as "submit a pod restart action via CLI and verify the pod is restarted and the action status is updated to success."

## 🐳 Docker Image for Tests

A dedicated Docker image is built for running these integration tests, typically defined by a `Dockerfile.integration_tests` located at the root of the project or within this package.

* **Contents:** This Docker image usually includes:
  * The Python environment with all necessary dependencies, including `pytest`, `automated_actions_client`, `automated_actions_cli`, and any other testing libraries.
  * The integration test scripts themselves.
  * Configuration files or scripts needed to set up the testing environment or connect to the target services.
* **Purpose:** Provides a consistent and isolated environment for executing the integration tests, especially within CI/CD pipelines.

## 🚀 Deployment and CI/CD Workflow

1. **Deployment to Integration Environment:**
    * Before running the integration tests, the latest version of the `automated_actions` application (API server, workers) is deployed to a dedicated "integration" namespace. This environment mirrors production as closely as possible in terms of configuration and dependencies.
2. **Test Execution:**
    * The `integration_tests` Docker image is run, executing the test suite (e.g., `pytest`) against the `automated_actions` system deployed in the integration environment.
    * Tests will use the CLI and client to trigger actions, poll for status, and verify outcomes.
3. **Success Criteria & Promotion:**
    * **If all integration tests pass successfully:** This provides a strong signal that the current version of the application is stable and behaves as expected. This success typically triggers the next steps in the CI/CD pipeline:
        * Automated rollout/promotion of the application to the **staging environment**.
        * After further validation in staging (which might include another, possibly more extensive, set of tests or manual QA), a rollout to the **production environment** can be initiated.
    * **If any integration test fails:** The pipeline is halted. The failure indicates a problem with the application that needs to be investigated and fixed before it can be promoted further. Detailed logs and test reports are crucial for debugging.

## 🧑‍💻 Writing and Running Integration Tests

### Test Structure

* Tests are typically written using `pytest`.
* Fixtures (`pytest` fixtures) are heavily used to:
  * Set up and tear down test environments or specific test data.
  * Provide initialized instances of `automated_actions_client`.
  * Helper functions for running CLI commands.
* Test files might be organized by the feature or action type they are testing.

> :information_source: **Note**:
>
> Crucially, integration tests must validate the *actual* effect of an action. For example, when testing an OpenShift workload restart, it's not enough to see the command was accepted; the test **must** confirm the workload was indeed restarted.

### Running Locally

* Running integration tests locally can be complex due to the need for a fully deployed system and its dependencies.
* If possible, ensure you are targeting a non-production, dedicated integration environment.
* You might need to set specific environment variables for API endpoints, credentials, and target cluster details.

Run the tests using `pytest` from within this package directory or as configured in your `Makefile`.

```bash
make test
```

## 🤝 Contributing

* When adding new actions or significant features to the main application, corresponding integration tests **must** be added.
* Tests should be as independent as possible, though some sequential dependencies might be unavoidable for complex scenarios.
* Ensure tests clean up any resources they create, if applicable and feasible.
* Make tests robust against minor timing issues by using appropriate polling and timeouts.
* Provide clear and descriptive test names and failure messages.
