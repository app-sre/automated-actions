from typing import TYPE_CHECKING

from automated_actions_utils.aws_api import (
    RDS_TERMINAL_ERROR_STATES,
    AWSApi,
    RdsInstanceStatus,
    get_aws_credentials,
)
from automated_actions_utils.cluster_connection import get_cluster_connection_data
from automated_actions_utils.external_resource import (
    ExternalResource,
    ExternalResourceProvider,
    get_external_resource,
)
from automated_actions_utils.openshift_client import (
    OpenshiftClient,
    SecretKeyRef,
    job_builder,
)

from automated_actions.celery.app import app
from automated_actions.celery.automated_action_task import AutomatedActionTask
from automated_actions.config import settings

if TYPE_CHECKING:
    from automated_actions.db.models import Action
    from celery import Task

RDS_STATUS_POLL_COUNTDOWN = 30


class ExternalResourceRDSReboot:
    def __init__(self, aws_api: AWSApi, rds: ExternalResource) -> None:
        self.aws_api = aws_api
        self.rds = rds

    def run(self, *, force_failover: bool) -> None:
        self.aws_api.reboot_rds_instance(
            identifier=self.rds.identifier, force_failover=force_failover
        )


@app.task(base=AutomatedActionTask)
def external_resource_rds_reboot(
    account: str,
    identifier: str,
    *,
    force_failover: bool,
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
        ExternalResourceRDSReboot(aws_api, rds).run(force_failover=force_failover)


class ExternalResourceRDSSnapshot:
    """Create a snapshot of an RDS instance."""

    def __init__(self, aws_api: AWSApi, rds: ExternalResource) -> None:
        self.aws_api = aws_api
        self.rds = rds

    def run(self, snapshot_identifier: str) -> None:
        self.aws_api.create_rds_snapshot(
            identifier=self.rds.identifier,
            snapshot_identifier=snapshot_identifier,
        )


@app.task(base=AutomatedActionTask)
def external_resource_rds_snapshot(
    account: str,
    identifier: str,
    snapshot_identifier: str,
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
        ExternalResourceRDSSnapshot(aws_api, rds).run(
            snapshot_identifier=snapshot_identifier
        )


class ExternalResourceRDSStart:
    """Idempotent RDS start — safe to retry on worker restart."""

    def __init__(self, aws_api: AWSApi, rds: ExternalResource) -> None:
        self.aws_api = aws_api
        self.rds = rds

    def run(self) -> bool:
        """Returns True if the instance is available, False if a retry is needed."""
        status = self.aws_api.get_rds_instance_status(self.rds.identifier)
        if status == RdsInstanceStatus.AVAILABLE:
            return True
        if status in RDS_TERMINAL_ERROR_STATES:
            msg = f"RDS instance {self.rds.identifier} entered terminal error state '{status}'"
            raise RuntimeError(msg)
        if status == RdsInstanceStatus.STOPPED:
            self.aws_api.start_rds_instance(identifier=self.rds.identifier)
        return False


@app.task(bind=True, base=AutomatedActionTask, max_retries=60)
def external_resource_rds_start(
    self: Task,
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
        if not ExternalResourceRDSStart(aws_api, rds).run():
            raise self.retry(countdown=RDS_STATUS_POLL_COUNTDOWN)


class ExternalResourceRDSStop:
    """Idempotent RDS stop — safe to retry on worker restart."""

    def __init__(self, aws_api: AWSApi, rds: ExternalResource) -> None:
        self.aws_api = aws_api
        self.rds = rds

    def run(self) -> bool:
        """Returns True if the instance is stopped, False if a retry is needed."""
        status = self.aws_api.get_rds_instance_status(self.rds.identifier)
        if status == RdsInstanceStatus.STOPPED:
            return True
        if status in RDS_TERMINAL_ERROR_STATES:
            msg = f"RDS instance {self.rds.identifier} entered terminal error state '{status}'"
            raise RuntimeError(msg)
        if status == RdsInstanceStatus.AVAILABLE:
            self.aws_api.stop_rds_instance(identifier=self.rds.identifier)
        return False


@app.task(bind=True, base=AutomatedActionTask, max_retries=60)
def external_resource_rds_stop(
    self: Task,
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
        if not ExternalResourceRDSStop(aws_api, rds).run():
            raise self.retry(countdown=RDS_STATUS_POLL_COUNTDOWN)


class ExternalResourceFlushElastiCache:
    def __init__(
        self, action: Action, oc: OpenshiftClient, elasticache: ExternalResource
    ) -> None:
        self.action = action
        self.oc = oc
        self.elasticache = elasticache

    def run(
        self,
        image: str,
        command: list[str],
        args: list[str],
        secret_name: str,
        env_secret_mappings: dict[str, str],
    ) -> None:
        job = job_builder(
            image=image,
            command=command,
            args=args,
            job_name="flush-elasticache",
            annotations={
                "automated-actions.action_id": str(self.action.action_id),
            },
            env_secrets={
                key: SecretKeyRef(
                    secret=secret_name,
                    key=value,
                )
                for key, value in env_secret_mappings.items()
            },
        )
        return self.oc.run_job(namespace=self.elasticache.namespace, job=job)


@app.task(base=AutomatedActionTask)
def external_resource_flush_elasticache(
    account: str,
    identifier: str,
    *,
    action: Action,
) -> None:
    elasticache = get_external_resource(
        account=account,
        identifier=identifier,
        provider=ExternalResourceProvider.ELASTICACHE,
    )

    cluster_connection = get_cluster_connection_data(elasticache.cluster, settings)
    oc = OpenshiftClient(
        server_url=cluster_connection.url, token=cluster_connection.token
    )
    if not elasticache.output_resource_name:
        raise ValueError(
            f"Output resource name not defined for {elasticache.identifier} in {elasticache.namespace} namespace.",
        )
    ExternalResourceFlushElastiCache(
        action=action,
        oc=oc,
        elasticache=elasticache,
    ).run(
        image=settings.external_resource_elasticache.image,
        command=settings.external_resource_elasticache.flush_command,
        args=settings.external_resource_elasticache.flush_command_args,
        secret_name=elasticache.output_resource_name,
        env_secret_mappings=settings.external_resource_elasticache.env_secret_mappings,
    )
