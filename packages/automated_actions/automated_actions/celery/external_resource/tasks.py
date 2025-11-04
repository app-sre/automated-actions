from automated_actions_utils.aws_api import AWSApi, get_aws_credentials
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
from automated_actions.db.models import Action


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
