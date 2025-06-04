from collections.abc import Callable

import pytest
from automated_actions_client import AuthenticatedClient
from automated_actions_client.api.v1 import no_op
from automated_actions_client.models.action_schema_out import ActionSchemaOut
from automated_actions_client.models.action_status import ActionStatus

from tests.conftest import Config


@pytest.fixture(scope="session")
def action_id(aa_client: AuthenticatedClient) -> str:
    """Trigger a no-op action and return the action id.

    We use a pytest fixture with session scope to avoid multiple actions being triggered
    """
    action = no_op.sync(client=aa_client)
    assert isinstance(action, ActionSchemaOut)
    assert action.status == ActionStatus.PENDING
    assert not action.result
    return action.action_id


def test_no_op(
    action_id: str, wait_for_action_success: Callable, config: Config
) -> None:
    wait_for_action_success(
        action_id=action_id,
        retries=config.no_op.retries,
        sleep_time=config.no_op.sleep_time,
    )
