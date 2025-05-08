import pytest
from automated_actions_client import AuthenticatedClient
from automated_actions_client.api.v1 import action_detail, openshift_workload_restart
from automated_actions_client.models.action_schema_out import ActionSchemaOut
from automated_actions_client.models.openshift_workload_restart_kind import (
    OpenshiftWorkloadRestartKind,
)

from tests.conftest import Config, _config


@pytest.fixture(scope="session")
def run_openshift_workload_restart(
    aa_client: AuthenticatedClient, config: Config
) -> str:
    """Trigger an OpenShift workload restart action and return the action id."""
    action = openshift_workload_restart.sync(
        client=aa_client,
        cluster=config.cluster,
        namespace=config.namespace,
        kind=OpenshiftWorkloadRestartKind(config.kind),
        name=config.name,
    )
    assert isinstance(action, ActionSchemaOut)
    return action.action_id


ACTION_FIXTURES = [
    "run_openshift_workload_restart",
]


@pytest.mark.parametrize("action_fixture", ACTION_FIXTURES)
def test_action_queued(
    request: pytest.FixtureRequest, aa_client: AuthenticatedClient, action_fixture: str
) -> None:
    """Test that the action is queued."""
    action_id = request.getfixturevalue(action_fixture)
    action = action_detail.sync(client=aa_client, action_id=action_id)

    assert isinstance(action, ActionSchemaOut)
    assert action.status in {"PENDING", "RUNNING"}
    assert not action.result


@pytest.mark.parametrize("action_fixture", ACTION_FIXTURES)
@pytest.mark.flaky(
    reruns=_config.action_timeout_seconds, reruns_delay=1, only_rerun=["AssertionError"]
)
@pytest.mark.order(after="test_action_queued")
def test_action_completion(
    request: pytest.FixtureRequest, aa_client: AuthenticatedClient, action_fixture: str
) -> None:
    """Test that the action completes successfully."""
    action_id = request.getfixturevalue(action_fixture)
    action = action_detail.sync(client=aa_client, action_id=action_id)

    assert isinstance(action, ActionSchemaOut)
    assert action.status == "SUCCESS"
    assert action.result
