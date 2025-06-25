# Automated Actions Settings

These settings control the general behavior of the Automated Actions application. All settings can be configured via environment variables, prefixed with `AA_` or `OPA_` for the Open Policy Agent.

## General Application Configuration

* **`AA_DEBUG`**:
  * **Description**: Enables or disables debug mode for the application. When enabled, it provide more verbose logging.
  * **Default**: `false`
  * **Impact**: Setting to `true` can be helpful for development and troubleshooting.

* **`AA_URL`**:
  * **Description**: The base URL where the application is hosted. This is used for generating absolute URLs, for example, in API responses or callbacks.
  * **Default**: `http://localhost:8080`
  * **Impact**: Incorrect configuration can lead to issues with client communication and OIDC redirects.

* **`AA_ROOT_PATH`**:
  * **Description**: If the application is served under a sub-path (e.g., `/automated-actions`), this setting specifies that path. Only needed when running behind a reverse proxy.
  * **Default**: `""` (empty string)
  * **Impact**: Misconfiguration can lead to 404 errors as FastAPI won't be able to match routes correctly.

* **`AA_ENVIRONMENT`**:
  * **Description**: Specifies the deployment environment (e.g., `development`, `staging`, `production`). This is used to differentiate between environments in shared resources like DynamoDB.
  * **Required**: Yes
  * **Impact**: Critical for differentiating between environments. Used in naming resources (like DynamoDB tables).

* **`AA_START_MODE`**:
  * **Description**: Determines the start mode of the application. Use `api` to start the FastAPI server, or `worker` to start a Celery worker.
  * **Default**: `api`
  * **Impact**: Controls whether the container runs the API server or a Celery worker.

* **`AA_APP_PORT`**:
  * **Description**: The port on which the FastAPI application will listen.
  * **Default**: `8080`
  * **Impact**: Change if you need the API to listen on a different port.

* **`AA_AUTO_RELOAD`**:
  * **Description**: Enables auto-reload for development. When set to `1`, the API server or worker will automatically restart on code changes.
  * **Default**: `0`
  * **Impact**: Useful for development, should be disabled in production.

* **`AA_UVICORN_OPTS`**:
  * **Description**: Additional options to pass to the Uvicorn server when starting the API.
  * **Default**: `--host 0.0.0.0 --proxy-headers --forwarded-allow-ips=*`
  * **Impact**: Allows customization of the Uvicorn server.

* **`AA_WORKER_TEMP_DIR`**:
  * **Description**: Directory to use for temporary files created by Celery workers (e.g., for Prometheus multiprocess metrics).
  * **Default**: System default temp directory
  * **Impact**: Set this if you want worker temp files in a specific location.

## Celery Worker Configuration

These settings configure the Celery workers responsible for asynchronous task processing.

* **`AA_CELERY_OPTS`**:
  * **Description**: Additional options to pass to the Celery worker process.
  * **Default**: `--pool solo`
  * **Impact**: Controls Celery worker behavior. The default ensures only one worker per pod for metrics compatibility.

* **`AA_BROKER_URL`**:
  * **Description**: The URL of the message broker used by Celery (e.g., SQS, Redis, RabbitMQ).
  * **Default**: `sqs://localhost:4566` (for LocalStack SQS)
  * **Impact**: Essential for Celery workers to connect to the message queue. Incorrect URL will prevent task processing.

* **`AA_SQS_URL`**:
  * **Description**: The specific SQS queue URL that Celery workers will listen to for tasks.
  * **Default**: `http://localhost:4566/000000000000/automated-actions` (for LocalStack SQS)
  * **Impact**: Workers will not pick up tasks if this URL is incorrect or points to the wrong queue.

* **`AA_BROKER_AWS_REGION`**:
  * **Description**: The AWS region for the SQS broker if using AWS SQS.
  * **Default**: `us-east-1`
  * **Impact**: Must match the region where your SQS queue is located.

* **`AA_BROKER_AWS_ACCESS_KEY_ID`**:
  * **Description**: AWS access key ID for connecting to SQS.
  * **Default**: `localstack`
  * **Impact**: Required for authenticating with AWS SQS.

* **`AA_BROKER_AWS_SECRET_ACCESS_KEY`**:
  * **Description**: AWS secret access key for connecting to SQS.
  * **Default**: `localstack`
  * **Impact**: Required for authenticating with AWS SQS.

* **`AA_RETRIES`**:
  * **Description**: The number of times a Celery task will be retried if it fails. *(Not implemented yet)*
  * **Default**: `None` (Celery's default, or task-specific retry settings)
  * **Impact**: Controls the fault tolerance of task execution.

* **`AA_RETRY_DELAY`**:
  * **Description**: The delay (in seconds) before a failed Celery task is retried. *(Not implemented yet)*
  * **Default**: `10`
  * **Impact**: Affects how quickly retries are attempted.

## Database Configuration (DynamoDB)

Settings for connecting to AWS DynamoDB, used for storing action states and metadata.

* **`AA_DYNAMODB_URL`**:
  * **Description**: The endpoint URL for DynamoDB.
  * **Default**: `http://localhost:4566` (for LocalStack DynamoDB)
  * **Impact**: Application will not be able to persist or retrieve action data if this is incorrect.

* **`AA_DYNAMODB_AWS_REGION`**:
  * **Description**: The AWS region for DynamoDB.
  * **Default**: `us-east-1`
  * **Impact**: Must match the region where your DynamoDB tables are located.

* **`AA_DYNAMODB_AWS_ACCESS_KEY_ID`**:
  * **Description**: AWS access key ID for connecting to DynamoDB.
  * **Default**: `localstack`
  * **Impact**: Required for authenticating with AWS DynamoDB.

* **`AA_DYNAMODB_AWS_SECRET_ACCESS_KEY`**:
  * **Description**: AWS secret access key for connecting to DynamoDB.
  * **Default**: `localstack`
  * **Impact**: Required for authenticating with AWS DynamoDB.

## OIDC (OpenID Connect) Configuration

Settings for integrating with an OIDC provider (e.g., Red Hat SSO) for authentication.

* **`AA_OIDC_ISSUER`**:
  * **Description**: The issuer URL of the OIDC provider.
  * **Default**: `https://auth.redhat.com/auth/realms/EmployeeIDP`
  * **Impact**: Critical for OIDC discovery and token validation.

* **`AA_OIDC_CLIENT_ID`**:
  * **Description**: The client ID registered with the OIDC provider for this application.
  * **Required**: Yes
  * **Impact**: Essential for the OIDC authentication flow.

* **`AA_OIDC_CLIENT_SECRET`**:
  * **Description**: The client secret for this application, provided by the OIDC provider.
  * **Required**: Yes
  * **Impact**: Required for secure communication with the OIDC provider. Treat as sensitive.

The OIDC client must have the following settings configured in the OIDC provider:

* **request URIs**: Must include the application's base URL. E.g., `https://automated-actions.devshift.net`.
* **redirect URIs**: Must include the application's base URL followed by `/api/v1/auth/callback`. E.g., `https://automated-actions.devshift.net/api/v1/auth/callback`.
* **grant types**: Must include `authorization_code`.
* **response types**: Must include `code`.
* **scopes**: Must include `openid`, `profile`, and `email`.

## Session Management Configuration

* **`AA_SESSION_SECRET`**:
  * **Description**: A secret key used to sign and encrypt session cookies.
  * **Required**: Yes
  * **Impact**: Must be a strong, unique secret. Changing it will invalidate all existing sessions.

* **`AA_SESSION_TIMEOUT_SECS`**:
  * **Description**: The duration (in seconds) for which a user's session remains active.
  * **Default**: `3600` (1 hour)
  * **Impact**: Controls how long users stay logged in.

* **`AA_TOKEN_SECRET`**:
  * **Description**: A secret key used for signing internal API tokens for service accounts.
  * **Required**: Yes
  * **Impact**: Must be a strong, unique secret. Critical for the security of tokens it signs.

## Authorization (Open Policy Agent - OPA)

Settings for connecting to an OPA instance for authorization decisions.

* **`AA_OPA_HOST`**:
  * **Description**: The URL of the Open Policy Agent (OPA) server. The API server queries OPA to make authorization decisions.
  * **Default**: `http://opa:8181`
  * **Impact**: If the API server cannot reach OPA, authorization checks will fail.

* **`OPA_ACTION_API_URL`**:
  * **Description**: The API URL of the automated-actions server used by OPA. E.g., `http://automated-actions:8080/api/v1`
  * **Required**: Yes
  * **Impact**: If this URL is incorrect, the OPA server will not be able to communicate with the automated-actions server and can't retrieve previously executed user actions.
* **`OPA_ACTION_API_TOKEN`**:
  * **Description**: The token used by OPA to authenticate with the automated-actions API. This is a service account token. See below on how to generate this token.
  * **Required**: Yes
  * **Impact**: If this token is incorrect or missing, OPA will not be able to authenticate with the automated-actions API.
* **`OPA_MAX_AGE_MINUTES`**:
  * **Description**: The maximum age (in minutes) of actions that OPA can retrieve from the automated-actions API. This is used to limit the number of actions OPA has to consider when making authorization decisions.
  * **Default**: `60`
  * **Impact**: If set too low, OPA may not have enough historical data to make informed decisions. If set too high, it may lead to performance issues.

The `OPA_ACTION_API_TOKEN` can be generated using the `create-token` command provided by the `automated_actions_cli` (once available and configured):

```bash
automated-actions create-token --name "OPA service account" --username "open-policy-agent" --email "not-used@example.com" --expiration "2200-09-30 20:15:00"
```

Ensure the username is `open-policy-agent` and the expiration date is set to a future date. This command will return a token that you can use in your local configuration.

## Worker Metrics Configuration

Settings related to exposing metrics from Celery workers.

* **`AA_WORKER_METRICS_PORT`**:
  * **Description**: The port on which Celery workers expose their Prometheus metrics.
  * **Default**: `8000`
  * **Impact**: Used for monitoring worker health and performance.

## Qontract Server Configuration

Settings for interacting with a Qontract server instance, typically used for fetching configuration or data.

* **`AA_QONTRACT_SERVER_URL`**:
  * **Description**: The GraphQL endpoint URL of the Qontract server.
  * **Default**: `http://localhost:4000/graphql`
  * **Impact**: If workers need to fetch data from Qontract server, this URL must be correct.

* **`AA_QONTRACT_SERVER_TOKEN`**:
  * **Description**: An optional authentication token for accessing the Qontract server.
  * **Default**: `None`
  * **Impact**: Required if the Qontract server needs authentication.

## HashiCorp Vault Configuration

Settings for connecting to HashiCorp Vault to retrieve secrets.

* **`AA_VAULT_SERVER_URL`**:
  * **Description**: The URL of the HashiCorp Vault server.
  * **Default**: `http://localhost:8200`
  * **Impact**: Essential if actions need to fetch secrets from Vault.

* **`AA_VAULT_ROLE_ID`**:
  * **Description**: The RoleID for AppRole authentication with Vault. Used by workers to authenticate to Vault.
  * **Default**: `None`
  * **Impact**: Required for AppRole authentication.

* **`AA_VAULT_SECRET_ID`**:
  * **Description**: The SecretID for AppRole authentication with Vault.
  * **Default**: `None`
  * **Impact**: Required for AppRole authentication. Treat as sensitive.

* **`AA_VAULT_KUBE_AUTH_ROLE`**:
  * **Description**: The Vault Kubernetes authentication role. Used if authenticating to Vault via Kubernetes service account.
  * **Default**: `None`
  * **Impact**: Required for Kubernetes authentication method.

* **`AA_VAULT_KUBE_AUTH_MOUNT`**:
  * **Description**: The path where the Kubernetes authentication method is mounted in Vault.
  * **Default**: `None`
  * **Impact**: Required for Kubernetes authentication method.
