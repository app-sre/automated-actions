from __future__ import annotations

from clientele import api as clientele_api

from . import config, schemas

client = clientele_api.APIClient(config=config.Config())


@client.post(
    "/api/v1/admin/token",
    response_map={200: schemas.ResponseCreateToken, 422: schemas.HTTPValidationError},
)
def create_token(
    result: schemas.HTTPValidationError | schemas.ResponseCreateToken,
    data: schemas.CreateTokenParam,
) -> schemas.HTTPValidationError | schemas.ResponseCreateToken:
    """Create Token

    Create a token for a service account.
    """
    return result


@client.post(
    "/api/v1/external-resource/rds-reboot/{account}/{identifier}",
    response_map={202: schemas.ActionSchemaOut, 422: schemas.HTTPValidationError},
)
def external_resource_rds_reboot(
    result: schemas.ActionSchemaOut | schemas.HTTPValidationError,
    account: str,
    identifier: str,
    force_failover: bool | None = None,
) -> schemas.ActionSchemaOut | schemas.HTTPValidationError:
    """External Resource Rds Reboot

        Reboot an RDS instance.

    This action initiates a reboot of a specified RDS instance in a given AWS account.
    """
    return result


@client.post(
    "/api/v1/external-resource/rds-start/{account}/{identifier}",
    response_map={202: schemas.ActionSchemaOut, 422: schemas.HTTPValidationError},
)
def external_resource_rds_start(
    result: schemas.ActionSchemaOut | schemas.HTTPValidationError,
    account: str,
    identifier: str,
) -> schemas.ActionSchemaOut | schemas.HTTPValidationError:
    """External Resource Rds Start

        Start a stopped RDS instance.

    This action initiates a start of a specified stopped RDS instance in a given AWS account.
    """
    return result


@client.post(
    "/api/v1/external-resource/rds-stop/{account}/{identifier}",
    response_map={202: schemas.ActionSchemaOut, 422: schemas.HTTPValidationError},
)
def external_resource_rds_stop(
    result: schemas.ActionSchemaOut | schemas.HTTPValidationError,
    account: str,
    identifier: str,
) -> schemas.ActionSchemaOut | schemas.HTTPValidationError:
    """External Resource Rds Stop

        Stop a running RDS instance.

    This action initiates a stop of a specified running RDS instance in a given AWS account.
    """
    return result


@client.post(
    "/api/v1/external-resource/rds-snapshot/{account}/{identifier}/{snapshot_identifier}",
    response_map={202: schemas.ActionSchemaOut, 422: schemas.HTTPValidationError},
)
def external_resource_rds_snapshot(
    result: schemas.ActionSchemaOut | schemas.HTTPValidationError,
    account: str,
    identifier: str,
    snapshot_identifier: str,
) -> schemas.ActionSchemaOut | schemas.HTTPValidationError:
    """External Resource Rds Snapshot

        Create a snapshot of an RDS instance.

    This action initiates a snapshot of a specified RDS instance in a given AWS account.
    """
    return result


@client.post(
    "/api/v1/external-resource/flush-elasticache/{account}/{identifier}",
    response_map={202: schemas.ActionSchemaOut, 422: schemas.HTTPValidationError},
)
def external_resource_flush_elasticache(
    result: schemas.ActionSchemaOut | schemas.HTTPValidationError,
    account: str,
    identifier: str,
) -> schemas.ActionSchemaOut | schemas.HTTPValidationError:
    """External Resource Flush Elasticache

        Flush an ElastiCache instance.

    This action initiates a flush of a specified ElastiCache instance in a given AWS account.
    """
    return result


@client.post(
    "/api/v1/openshift/workload-restart/{cluster}/{namespace}/{kind}/{name}",
    response_map={202: schemas.ActionSchemaOut, 422: schemas.HTTPValidationError},
)
def openshift_workload_restart(
    result: schemas.ActionSchemaOut | schemas.HTTPValidationError,
    cluster: str,
    namespace: str,
    kind: str,
    name: str,
) -> schemas.ActionSchemaOut | schemas.HTTPValidationError:
    """Openshift Workload Restart

        Initiates a restart of a specified OpenShift workload.

    This action triggers a restart of a workload (e.g., Pod, Deployment)
    within a given OpenShift cluster and namespace.
    """
    return result


@client.post(
    "/api/v1/openshift/workload-delete/{cluster}/{namespace}/{kind}/{name}",
    response_map={202: schemas.ActionSchemaOut, 422: schemas.HTTPValidationError},
)
def openshift_workload_delete(
    result: schemas.ActionSchemaOut | schemas.HTTPValidationError,
    cluster: str,
    namespace: str,
    kind: str,
    name: str,
    api_version: str | None = None,
) -> schemas.ActionSchemaOut | schemas.HTTPValidationError:
    """Openshift Workload Delete

        Initiates a delete of a specified OpenShift workload.

    This action triggers a delete of a workload (e.g., Pod, Deployment)
    within a given OpenShift cluster and namespace.
    """
    return result


@client.post(
    "/api/v1/openshift/trigger-cronjob/{cluster}/{namespace}/{cronjob}",
    response_map={202: schemas.ActionSchemaOut, 422: schemas.HTTPValidationError},
)
def openshift_trigger_cronjob(
    result: schemas.ActionSchemaOut | schemas.HTTPValidationError,
    cluster: str,
    namespace: str,
    cronjob: str,
) -> schemas.ActionSchemaOut | schemas.HTTPValidationError:
    """Openshift Trigger Cronjob

    Run a specified OpenShift cronjob immediately.
    """
    return result


@client.get(
    "/api/v1/actions",
    response_map={200: schemas.ResponseActionList, 422: schemas.HTTPValidationError},
)
def action_list(
    result: schemas.HTTPValidationError | schemas.ResponseActionList,
    status: schemas.ActionStatus | None = None,
    action_user: str | None = None,
    max_age_minutes: int | None = None,
) -> schemas.HTTPValidationError | schemas.ResponseActionList:
    """Action List

    Lists actions, optionally filtered by status, user, or age.
    """
    return result


@client.get(
    "/api/v1/actions/{action_id}",
    response_map={200: schemas.ActionSchemaOut, 422: schemas.HTTPValidationError},
)
def action_detail(
    result: schemas.ActionSchemaOut | schemas.HTTPValidationError, action_id: str
) -> schemas.ActionSchemaOut | schemas.HTTPValidationError:
    """Action Detail

    Retrieves the details of a specific action by its ID.
    """
    return result


@client.post(
    "/api/v1/actions/{action_id}",
    response_map={202: schemas.ActionSchemaOut, 422: schemas.HTTPValidationError},
)
def action_cancel(
    result: schemas.ActionSchemaOut | schemas.HTTPValidationError, action_id: str
) -> schemas.ActionSchemaOut | schemas.HTTPValidationError:
    """Action Cancel

    Cancels a pending or running action by its ID.
    """
    return result


@client.get("/api/v1/me")
def me(result: schemas.UserSchemaOut) -> schemas.UserSchemaOut:
    """Me

    Get the current user information.
    """
    return result


@client.post("/api/v1/no-op")
def no_op(result: schemas.ActionSchemaOut) -> schemas.ActionSchemaOut:
    """No Op

        Initiates a no-operation action.

    This action performs no actual operation but can be used for testing.
    """
    return result


@client.post(
    "/api/v1/payload-tracker/create-partition/{cluster}/{namespace}/{date}",
    response_map={202: schemas.ActionSchemaOut, 422: schemas.HTTPValidationError},
)
def payload_tracker_create_partition(
    result: schemas.ActionSchemaOut | schemas.HTTPValidationError,
    cluster: str,
    namespace: str,
    date: str,
) -> schemas.ActionSchemaOut | schemas.HTTPValidationError:
    """Payload Tracker Create Partition

        Create a payload-tracker database partition for a given date.

    Runs a one-off Job in the payload-tracker namespace that calls the
    idempotent create_partition SQL function for the requested date. Useful to
    recover a partition that the daily vacuum cronjob failed to create.
    """
    return result
