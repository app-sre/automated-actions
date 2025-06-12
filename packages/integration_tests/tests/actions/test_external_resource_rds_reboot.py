from collections.abc import Callable

import pytest
from automated_actions_client import AuthenticatedClient
from automated_actions_client.api.actions import external_resource_rds_reboot
from automated_actions_client.models.action_schema_out import ActionSchemaOut
from automated_actions_client.models.action_status import ActionStatus
from automated_actions_utils.aws_api import AWSApi, get_aws_credentials
from automated_actions_utils.external_resource import get_external_resource

from tests.conftest import Config


@pytest.fixture
def aws_api(config: Config) -> AWSApi:
    rds = get_external_resource(
        account=config.external_resource_rds_reboot.account,
        identifier=config.external_resource_rds_reboot.identifier,
    )
    credentials = get_aws_credentials(
        vault_secret=rds.account.automation_token, region=rds.account.region
    )
    return AWSApi(credentials=credentials, region=rds.region)


@pytest.fixture(scope="session")
def action_id(aa_client: AuthenticatedClient, config: Config) -> str:
    """Trigger an RDS restart action and return the action id.

    We use a pytest fixture with session scope to avoid multiple actions being triggered
    in case of retry via the flaky mark
    """
    action = external_resource_rds_reboot.sync(
        account=config.external_resource_rds_reboot.account,
        identifier=config.external_resource_rds_reboot.identifier,
        client=aa_client,
    )
    assert isinstance(action, ActionSchemaOut)
    assert action.status == ActionStatus.PENDING
    assert not action.result
    return action.action_id


@pytest.mark.flaky(
    reruns=30, reruns_delay=1, only_rerun=["AssertionError"]
)  # retry on AssertionError because AWS events can take a while to propagate
def test_external_resource_rds_reboot(
    action_id: str,
    wait_for_action_success: Callable,
    aws_api: AWSApi,
    config: Config,
) -> None:
    """Test the RDS reboot action."""
    # wait for the action to complete and assert it was successful
    wait_for_action_success(
        action_id=action_id,
        retries=config.external_resource_rds_reboot.retries,
        sleep_time=config.external_resource_rds_reboot.sleep_time,
    )

    # check the RDS instance was really rebooted
    events = aws_api.rds_get_events(
        identifier=config.external_resource_rds_reboot.identifier,
        duration_min=2,
    )
    assert events, "No events found for the RDS instance."
    last_event = events[-1]
    assert (
        last_event["SourceIdentifier"] == config.external_resource_rds_reboot.identifier
    )
    # let's hope we don't have to deal with other events during our tests, e.g. DB backups
    assert last_event["Message"] in {"DB instance restarted", "DB instance shutdown"}
