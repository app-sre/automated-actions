# Actions

This document outlines the available automated actions that can be triggered and administrative commands for interacting with the system.

## Available Actions

These are the core operations that users can request the system to perform.

* **`openshift-workload-restart`**:
  * **Description**: Restarts a specified workload (e.g., Deployment, StatefulSet, Pod) in an OpenShift cluster.
  * **Use Case**: Useful for resolving issues with applications by restarting their components, applying new configurations that require a restart, or clearing a stuck state.
  * **Required Parameters**: Cluster name, namespace name, workload kind (e.g., `Deployment`, `Pod`), workload name.
  * **Usage Example (CLI)**: `automated-actions openshift-workload-restart --cluster my-cluster --namespace my-namespace --kind Deployment --name my-app-deployment`

* **`external-resource-rds-reboot`**:
  * **Description**: Reboots an Amazon RDS instance.
  * **Use Case**: Typically used for maintenance, applying updates, or resolving performance issues.
  * **Required Parameters**: The AWS account name and the RDS instance identifier.
  * **Usage Example (CLI)**: `automated-actions external-resource-rds-reboot --account aws-account-name --identifier my-rds-instance`

* **`no-op`**:
  * **Description**: It does nothing, it is just enqueued and immediately succeeds.
  * **Use Case**: It is used for monitoring purposes, to have and action that tests the whole automated actions stack without any external dependency.
  * **Required Parameters**: none
  * **Usage Example (CLI)**: `automated-actions no-op`

## Administrative & Utility Commands

These commands are typically used for managing actions, retrieving information, or system administration rather than performing an automated task on an external system.

* **`me`**:
  * **Description**: Displays information about the currently authenticated user.
  * **Use Case**: Verifying user identity and permissions within the system.
  * **Usage Example (CLI)**: `automated-actions me`

* **`action-list`**:
  * **Description**: Lists previously executed or currently running actions, potentially with filtering options.
  * **Use Case**: Monitoring the status of actions, reviewing action history.
  * **Usage Example (CLI)**: `automated-actions action-list` or `automated-actions list --status PENDING`

* **`action-detail`**:
  * **Description**: Shows detailed information about a specific action, including its status, parameters, and logs.
  * **Use Case**: Investigating a particular action's execution, troubleshooting failures.
  * **Required Parameters**: Action ID.
  * **Usage Example (CLI)**: `automated-actions action-detail --action-id <action_uuid>`

* **`action-cancel`**:
  * **Description**: Attempts to cancel an action that is currently in progress.
  * **Use Case**: Stopping an action that was initiated by mistake or is no longer needed.
  * **Required Parameters**: Action ID.
  * **Usage Example (CLI)**: `automated-actions action-cancel --action-id <action_uuid>`

* **`create-token`**:
  * **Description**: Generates a new API token for service accounts or programmatic access.
  * **Use Case**: Enabling other services (like OPA) or scripts to authenticate with the Automated Actions API.
  * **Required Parameters**: Token name, username, email, expiration date.
  * **Usage Example (CLI)**: `automated-actions create-token --name my-service-token --username service-account --email service@example.com --expiration "2025-12-31 23:59:59"`
