import time
from collections.abc import Callable

import pytest
from automated_actions_client import AuthenticatedClient
from automated_actions_client.api.actions import external_resource_rds_snapshot
from automated_actions_client.models.action_schema_out import ActionSchemaOut
from automated_actions_client.models.action_status import ActionStatus
from automated_actions_utils.aws_api import AWSApi, get_aws_credentials
from automated_actions_utils.external_resource import (
    ExternalResourceProvider,
    get_external_resource,
)

from tests.conftest import Config


@pytest.fixture(scope="session")
def aws_api(config: Config) -> AWSApi:
    rds = get_external_resource(
        account=config.external_resource_rds_snapshot.account,
        identifier=config.external_resource_rds_snapshot.identifier,
        provider=ExternalResourceProvider.RDS,
    )
    credentials = get_aws_credentials(
        vault_secret=rds.account.automation_token, region=rds.account.region
    )
    return AWSApi(credentials=credentials, region=rds.region)


@pytest.fixture(scope="session")
def action_id(aws_api: AWSApi, aa_client: AuthenticatedClient, config: Config) -> str:
    """Trigger an RDS restart action and return the action id.

    We use a pytest fixture with session scope to avoid multiple actions being triggered
    in case of retry via the flaky mark
    """
    snapshot_delete_retries = 0
    snapshot_delete_retry_wait_time = 30
    max_snapshot_delete_retry_wait_time = 300  # 5 minutes

    while True:
        try:
            snapshot_delete_retries += 1
            # remove old test snapshot if it exists
            aws_api.rds_client.delete_db_snapshot(
                DBSnapshotIdentifier=config.external_resource_rds_snapshot.snapshot_identifier
            )
            break
        except aws_api.rds_client.exceptions.DBSnapshotNotFoundFault:
            break
        except aws_api.rds_client.exceptions.InvalidDBSnapshotStateFault:
            if (
                snapshot_delete_retries * snapshot_delete_retry_wait_time
                > max_snapshot_delete_retry_wait_time
            ):
                raise
            time.sleep(snapshot_delete_retry_wait_time)
            continue

    action = external_resource_rds_snapshot.sync(
        account=config.external_resource_rds_snapshot.account,
        identifier=config.external_resource_rds_snapshot.identifier,
        snapshot_identifier=config.external_resource_rds_snapshot.snapshot_identifier,
        client=aa_client,
    )
    assert isinstance(action, ActionSchemaOut)
    assert action.status == ActionStatus.PENDING
    assert not action.result
    return action.action_id


@pytest.mark.flaky(
    reruns=30, reruns_delay=1, only_rerun=["AssertionError"]
)  # retry on AssertionError because AWS events can take a while to propagate
def test_external_resource_rds_snapshot(
    action_id: str,
    wait_for_action_success: Callable,
    aws_api: AWSApi,
    config: Config,
) -> None:
    """Test the RDS snapshot action."""
    # wait for the action to complete and assert it was successful
    wait_for_action_success(
        action_id=action_id,
        retries=config.external_resource_rds_snapshot.retries,
        sleep_time=config.external_resource_rds_snapshot.sleep_time,
    )

    # list snapshots and assert the snapshot was created
    snapshots = aws_api.rds_client.describe_db_snapshots(
        DBInstanceIdentifier=config.external_resource_rds_snapshot.identifier
    )
    for snapshot in snapshots["DBSnapshots"]:
        if (
            snapshot["DBSnapshotIdentifier"]
            and snapshot["DBSnapshotIdentifier"]
            == config.external_resource_rds_snapshot.snapshot_identifier
        ):
            return

    pytest.fail(
        f"Snapshot {config.external_resource_rds_snapshot.snapshot_identifier} not found"
    )
