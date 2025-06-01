from time import sleep

from automated_actions_client import AuthenticatedClient
from automated_actions_client.api.v1 import action_detail, no_op
from automated_actions_client.models.action_schema_out import ActionSchemaOut
from automated_actions_client.models.action_status import ActionStatus

from tests.conftest import Config


def test_no_op(aa_client: AuthenticatedClient, config: Config) -> None:
    action = no_op.sync(client=aa_client)
    assert isinstance(action, ActionSchemaOut)
    assert action.status == ActionStatus.PENDING
    assert not action.result

    detail = action_detail.sync(client=aa_client, action_id=action.action_id)
    assert isinstance(detail, ActionSchemaOut)

    retry = 1
    while retry <= config.no_op.retries and detail.status in {
        ActionStatus.PENDING,
        ActionStatus.RUNNING,
    }:
        detail = action_detail.sync(client=aa_client, action_id=action.action_id)
        assert isinstance(detail, ActionSchemaOut)
        retry += 1
        sleep(config.no_op.sleep_time)

    assert isinstance(detail, ActionSchemaOut)
    assert detail.status == ActionStatus.SUCCESS
