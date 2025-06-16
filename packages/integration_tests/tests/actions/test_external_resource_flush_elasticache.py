from collections.abc import Callable

import pytest
from automated_actions_client import AuthenticatedClient
from automated_actions_client.api.actions import external_resource_flush_elasticache
from automated_actions_client.models.action_schema_out import ActionSchemaOut
from automated_actions_client.models.action_status import ActionStatus

from tests.conftest import Config


@pytest.fixture(scope="session")
def action_id(aa_client: AuthenticatedClient, config: Config) -> str:
    """Trigger a flush elasticache action and return the action id."""
    action = external_resource_flush_elasticache.sync(
        account=config.external_resource_flush_elasticache.account,
        identifier=config.external_resource_flush_elasticache.identifier,
        client=aa_client,
    )
    assert isinstance(action, ActionSchemaOut)
    assert action.status == ActionStatus.PENDING
    assert not action.result
    return action.action_id


@pytest.mark.flaky(
    reruns=30, reruns_delay=1, only_rerun=["AssertionError"]
)  # retry on AssertionError because AWS events can take a while to propagate
def test_external_resource_flush_elasticache(
    action_id: str,
    wait_for_action_success: Callable,
    config: Config,
) -> None:
    """Test the flush elasticache action."""
    # wait for the action to complete and assert it was successful
    wait_for_action_success(
        action_id=action_id,
        retries=config.external_resource_flush_elasticache.retries,
        sleep_time=config.external_resource_flush_elasticache.sleep_time,
    )

    # unfortunately, AWS does not provide a good way to check if the cache was flushed
    # so we cannot assert anything here
