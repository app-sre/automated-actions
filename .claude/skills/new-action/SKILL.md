---
name: new-action
description: >
  End-to-end guide for implementing a new automated action across all required repositories
  (automated-actions, qontract-schemas, qontract-reconcile, app-interface). Use this skill
  whenever someone wants to add a new action type, implement a new automated action, or asks
  "how do I add an action" / "new action" / "implement action". Also trigger when the user
  mentions adding a new Celery task + FastAPI endpoint + schema for automated-actions.
---

# Implementing a New Automated Action

This skill guides you through adding a new automated action end-to-end. Four repositories are
involved, each with specific changes. The automated-actions repo is the current working directory;
the other three are provided by the user.

## Step 1: Gather Information

Before writing any code, ask the user for:

1. **Action name** — kebab-case identifier (e.g. `external-resource-rds-start`). This becomes
   the action type in schemas, the URL path segment, and the OPA policy object.
2. **Action category** — which subsystem does it belong to? Currently:
   - `external_resource` — AWS RDS, ElastiCache operations
   - `openshift` — workload restart, delete, trigger cronjob
   - New category if it doesn't fit the above
3. **Parameters** — what arguments does the action accept beyond account/identifier?
   (e.g. `force_failover: bool` for rds-reboot, `snapshot_identifier: str` for rds-snapshot)
4. **Underlying API call** — what boto3/OpenShift/other method does it invoke?
5. **Local repo paths** — ask the user for their local working copies of:
   - `qontract-schemas`
   - `qontract-reconcile`
   - `app-interface`

## Step 2: automated-actions (this repo)

All paths below are relative to the repo root.

### 2.1 Add the underlying API method

**File:** `packages/automated_actions_utils/automated_actions_utils/aws_api.py` (for AWS actions)

Add a method to the `AWSApi` class. Follow the existing pattern:

```python
def start_rds_instance(self, identifier: str) -> None:
    """Starts a stopped RDS database instance."""
    log.info(f"Starting RDS instance {identifier}")
    self.rds_client.start_db_instance(DBInstanceIdentifier=identifier)
```

### 2.2 Add the Celery task

**File:** `packages/automated_actions/automated_actions/celery/external_resource/tasks.py`
(or create a new subdirectory under `celery/` for a new category)

Two components per action:

**Task class** — encapsulates the operation:

```python
class ExternalResourceRDSStart:
    def __init__(self, aws_api: AWSApi, rds: ExternalResource) -> None:
        self.aws_api = aws_api
        self.rds = rds

    def run(self) -> None:
        self.aws_api.start_rds_instance(identifier=self.rds.identifier)
```

**Celery task function** — wires up dependencies and calls the class:

```python
@app.task(base=AutomatedActionTask)
def external_resource_rds_start(
    account: str,
    identifier: str,
    *,
    action: Action,  # noqa: ARG001
) -> None:
    rds = get_external_resource(
        account=account,
        identifier=identifier,
        provider=ExternalResourceProvider.RDS,
    )
    credentials = get_aws_credentials(
        vault_secret=rds.account.automation_token, region=rds.account.region
    )
    with AWSApi(credentials=credentials, region=rds.region) as aws_api:
        ExternalResourceRDSStart(aws_api, rds).run()
```

The `action` parameter is consumed by `AutomatedActionTask` base class (lifecycle management:
PENDING -> RUNNING -> SUCCESS/FAILURE). The `# noqa: ARG001` is needed because it's not used
directly in the function body.

### 2.3 Add the FastAPI endpoint

**File:** `packages/automated_actions/automated_actions/api/v1/views/external_resource.py`
(or the appropriate view module)

Three pieces:

1. **Action ID constant:**
   ```python
   EXTERNAL_RESOURCE_RDS_START_ACTION_ID = "external-resource-rds-start"
   ```

2. **Import the Celery task** (with alias to avoid name collision):
   ```python
   from automated_actions.celery.external_resource.tasks import (
       external_resource_rds_start as external_resource_rds_start_task,
   )
   ```

3. **Dependency function + endpoint:**
   ```python
   def get_action_external_resource_rds_start(
       action_mgr: Annotated[ActionManager, Depends(get_action_manager)], user: UserDep
   ) -> Action:
       return action_mgr.create_action(
           name=EXTERNAL_RESOURCE_RDS_START_ACTION_ID, owner=user
       )

   @router.post(
       "/external-resource/rds-start/{account}/{identifier}",
       operation_id=EXTERNAL_RESOURCE_RDS_START_ACTION_ID,
       status_code=202,
       tags=["Actions"],
   )
   def external_resource_rds_start(
       account: Annotated[str, Path(description="AWS account name")],
       identifier: Annotated[str, Path(description="RDS instance identifier")],
       action: Annotated[Action, Depends(get_action_external_resource_rds_start)],
   ) -> ActionSchemaOut:
       """Start a stopped RDS instance."""
       log.info(
           f"Starting RDS {identifier} in AWS account {account}. action_id={action.action_id}"
       )
       external_resource_rds_start_task.apply_async(
           kwargs={
               "account": account,
               "identifier": identifier,
               "action": action,
           },
           task_id=action.action_id,
       )
       return action.dump()
   ```

All endpoints return HTTP 202 (Accepted) since the work is async via Celery.

### 2.4 Add unit tests

Three test files need updates:

**`packages/automated_actions_utils/tests/test_aws_api.py`** — test the new API method:
- Parametrized test verifying the correct boto3 method is called with correct arguments
- Follow the `test_aws_api_reboot_rds_instance` pattern

**`packages/automated_actions/tests/celery/test_external_resource.py`** — three tests per action:
- `test_<action>_run` — test the task class `.run()` method directly
- `test_<action>_task` — test full Celery task execution (success path via `.signature().apply()`)
- `test_<action>_task_non_retryable_failure` — test failure path (side_effect=Exception)
- Import the new task class and function
- Reuse the existing `er` and `mock_aws` fixtures

**`packages/automated_actions/tests/api/v1/views/test_external_resource.py`** — endpoint tests:
- Add mock fixture for the new task
- Update `test_app` fixture to override the new dependency
- Add test function verifying 202 response and correct `apply_async` call
- Add the new dependency function to the `test_dependency_type_aliases_resolve_at_runtime`
  parametrize list

### 2.5 Bump package versions

New actions add endpoints to the client, so both client and CLI packages need version bumps.

**`packages/automated_actions_client/pyproject.toml`**:
- Bump `version` (e.g. `0.3.0` -> `0.4.0`)

**`packages/automated_actions_cli/pyproject.toml`**:
- Bump `version` to match
- Update the `automated-actions-client==` dependency pin to the new client version

### 2.6 Regenerate client + fix CLI tests

1. Run `make generate-client` — regenerates `packages/automated_actions_client/` from the
   updated OpenAPI spec. This requires Docker (spins up LocalStack + the app).
2. Update `EXPECTED_COMMANDS` in `packages/automated_actions_cli/tests/test_cli.py` — add the
   new command name to the set.
3. Run `make test` to verify everything passes.

### 2.7 Verification

```bash
make format     # ruff lint + format
make test       # all package tests + OPA policy tests
```

All 4 packages must pass: automated_actions, automated_actions_utils, automated_actions_cli, opa.

## Step 3: qontract-schemas

Path provided by user. All paths below are relative to that repo root.

### 3.1 JSON Schema

**File:** `schemas/app-sre/automated-action-1.yml`

Add a new `oneOf` block in the `type` discriminator list. For external-resource actions with
namespace + identifier arguments:

```yaml
- properties:
    type:
      enum:
      - external-resource-rds-start
    arguments:
      type: array
      items:
        type: object
        properties:
          namespace:
            "$ref": "/common-1.json#/definitions/crossref"
            "$schemaRef": "/openshift/namespace-1.yml"
            description: "The namespace where the RDS instance is located."
          identifier:
            type: string
            description: "The RDS identifier regex pattern to match."
        required:
        - namespace
        - identifier
  required:
  - arguments
```

Insert it near the other `external-resource-rds-*` blocks for readability.

### 3.2 GraphQL Schema

**File:** `graphql-schemas/schema.yml`

Two changes:

1. **Add fieldMap entry** in `AutomatedAction_v1` (search for `strategy: fieldMap`):
   ```yaml
   external-resource-rds-start: AutomatedActionExternalResourceRdsStart_v1
   ```

2. **Add GraphQL type definition** (near the other RDS types):
   ```yaml
   - name: AutomatedActionExternalResourceRdsStart_v1
     interface: AutomatedAction_v1
     fields:
     - { name: schema, type: string, isRequired: true }
     - { name: path, type: string, isRequired: true }
     - { name: type, type: string, isRequired: true }
     - { name: description, type: string }
     - { name: maxOps, type: int, isRequired: true }
     - { name: instances, type: AutomatedActionsInstance_v1, isList: true, isRequired: true }
     - name: permissions
       type: PermissionAutomatedActions_v1
       isList: true
       synthetic:
         schema: /access/permission-1.yml
         subAttr: actions
     - { name: arguments, type: AutomatedActionExternalResourceArgument_v1, isList: true, isRequired: true }
   ```

   For external-resource actions, reuse `AutomatedActionExternalResourceArgument_v1` (namespace
   + identifier). For actions with different argument shapes, define a new argument type.

## Step 4: qontract-reconcile

Path provided by user. All paths below are relative to that repo root.

### 4.1 GQL query fragment

**File:** `reconcile/gql_definitions/automated_actions/instance.gql`

Add an inline fragment inside the `actions` block. For external-resource actions:

```graphql
... on AutomatedActionExternalResourceRdsStart_v1 {
  external_resource_rds_start_arguments: arguments {
    namespace {
      externalResources {
        provisioner {
          ... on AWSAccount_v1 {
            name
          }
        }
      }
    }
    identifier
  }
}
```

The alias (`external_resource_rds_start_arguments`) avoids field name collisions across the
inline fragments — each action type aliases `arguments` differently.

### 4.2 Regenerate Pydantic models

**File:** `reconcile/gql_definitions/automated_actions/instance.py`

This file is auto-generated by `qenerate` (plugin=pydantic_v2). The user must run this manually
because it requires a running qontract-server with the updated schemas. Remind the user:

> You need to run `qenerate` to regenerate the Pydantic models from the updated GQL file.
> This requires a running qontract-server with the qontract-schemas changes deployed.

### 4.3 Integration logic

**File:** `reconcile/automated_actions/config/integration.py`

Two changes:

1. **Add import** for the new generated Pydantic class:
   ```python
   from reconcile.gql_definitions.automated_actions.instance import (
       AutomatedActionExternalResourceRdsStartV1,
   )
   ```

2. **Add match case** in `compile_roles()`. For external-resource actions:
   ```python
   case AutomatedActionExternalResourceRdsStartV1():
       for rds_start_arg in action.external_resource_rds_start_arguments:
           for rds_start_er in (
               rds_start_arg.namespace.external_resources or []
           ):
               if not isinstance(rds_start_er.provisioner, AWSAccountV1):
                   continue
               parameters.append({
                   "account": f"^{rds_start_er.provisioner.name}$",
                   "identifier": rds_start_arg.identifier,
               })
   ```

## Step 5: app-interface

Path provided by user. All paths below are relative to that repo root.

### 5.1 Documentation (always)

**File:** `docs/platform-users/platform-services/automated-actions/actions.md`

Add a section following the existing pattern (Schema, Example, Usage subsections). Insert it
alphabetically near related actions. Example:

```markdown
## external-resource-rds-start

This action starts a stopped RDS instance. It is useful for DR scenarios where RDS instances
need to be started in a controlled manner.

### Schema

\```yaml
---
$schema: /app-sre/automated-action-1.yml

type: external-resource-rds-start
description: |
  <A USER-FRIENDLY DESCRIPTION OF THE ACTION>

maxOps: 1  # in ops/hour

instances:
- $ref: /dependencies/automated-actions/production.yml

arguments:
- namespace:
    $ref: <PATH_TO_NAMESPACE_FILE>
  identifier: <REGEX_IDENTIFIER>
\```

### Usage

To use this action, you can run the following command:

\```bash
automated-action external-resource-rds-start \
  --account <AWS_ACCOUNT> \
  --identifier <RDS_IDENTIFIER>
\```
```

### 5.2 Action YAML files (per-service, user decides)

Tell the user: to enable this action for a specific service, create an action file at:

```
data/dependencies/automated-actions/actions/<service>/<action-name>.yml
```

Example structure:

```yaml
---
$schema: /app-sre/automated-action-1.yml

type: external-resource-rds-start
description: |
  Start the <service> RDS instances in AWS.

maxOps: 5  # in ops/hour

instances:
- $ref: /dependencies/automated-actions/production.yml

arguments:
- namespace:
    $ref: /services/<service>/namespaces/<namespace>.yml
  identifier: '<identifier-regex>'
```

For integration tests, use `maxOps: 0` and reference the integration instance:
```yaml
instances:
- $ref: /dependencies/automated-actions/integration.yml
```

### 5.3 Permission files (per-service, user decides)

Tell the user: to grant a team access to the action, add a `$ref` to the relevant permission
file at:

```
data/dependencies/automated-actions/permissions/<service>.yml
```

Add a line like:
```yaml
- $ref: /dependencies/automated-actions/actions/<service>/<action-name>.yml
```

Do NOT create these files automatically — the user decides which services and teams get access.

## Naming Conventions

| Context | Pattern | Example |
|---------|---------|---------|
| Action type (kebab-case) | `<category>-<operation>` | `external-resource-rds-start` |
| Python constant | `EXTERNAL_RESOURCE_RDS_START_ACTION_ID` | |
| Task class | `ExternalResourceRDSStart` | |
| Task function | `external_resource_rds_start` | |
| Task import alias | `external_resource_rds_start_task` | |
| Dependency function | `get_action_external_resource_rds_start` | |
| GQL type | `AutomatedActionExternalResourceRdsStart_v1` | |
| GQL arguments alias | `external_resource_rds_start_arguments` | |
| Pydantic class | `AutomatedActionExternalResourceRdsStartV1` | |
| URL path | `/external-resource/rds-start/{account}/{identifier}` | |
