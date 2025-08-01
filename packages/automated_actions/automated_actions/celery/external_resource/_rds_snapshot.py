from automated_actions_utils.aws_api import AWSApi, get_aws_credentials
from automated_actions_utils.external_resource import (
    ExternalResource,
    ExternalResourceProvider,
    get_external_resource,
)

from automated_actions.celery.app import app
from automated_actions.celery.automated_action_task import AutomatedActionTask
from automated_actions.db.models import Action


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
