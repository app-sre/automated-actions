from automated_actions_utils.aws_api import AWSApi, get_aws_credentials
from automated_actions_utils.external_resource import (
    ExternalResource,
    ExternalResourceAppInterfaceError,
    get_external_resource,
)
from fastapi import HTTPException

from automated_actions.celery.app import app
from automated_actions.celery.automated_action_task import AutomatedActionTask
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
    try:
        rds = get_external_resource(account=account, identifier=identifier)
    except ExternalResourceAppInterfaceError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None

    credentials = get_aws_credentials(
        vault_secret=rds.account.automation_token, region=rds.account.region
    )
    with AWSApi(credentials=credentials, region=rds.region) as aws_api:
        ExternalResourceRDSReboot(aws_api, rds).run(force_failover=force_failover)
