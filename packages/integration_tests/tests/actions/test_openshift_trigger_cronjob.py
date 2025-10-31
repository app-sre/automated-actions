from collections.abc import Callable
from datetime import UTC, timedelta
from datetime import datetime as dt

import pytest
from automated_actions.config import settings
from automated_actions_client import AuthenticatedClient
from automated_actions_client.api.actions import (
    openshift_trigger_cronjob,
)
from automated_actions_client.models.action_schema_out import ActionSchemaOut
from automated_actions_client.models.action_status import ActionStatus
from automated_actions_utils.cluster_connection import get_cluster_connection_data
from automated_actions_utils.openshift_client import (
    OpenshiftClient,
)

from tests.conftest import Config


@pytest.fixture
def openshift_client(config: Config) -> OpenshiftClient:
    cluster_connection = get_cluster_connection_data(
        config.openshift_trigger_cronjob.cluster, settings
    )
    return OpenshiftClient(
        server_url=cluster_connection.url, token=cluster_connection.token
    )


@pytest.fixture(scope="session")
def action_id(aa_client: AuthenticatedClient, config: Config) -> str:
    """Trigger an Openshift trigger cronjob action and return the action id.

    We use a pytest fixture with session scope to avoid multiple actions being triggered
    in case of retry via the flaky mark
    """
    action = openshift_trigger_cronjob.sync(
        client=aa_client,
        cluster=config.openshift_trigger_cronjob.cluster,
        namespace=config.openshift_trigger_cronjob.namespace,
        cronjob=config.openshift_trigger_cronjob.cronjob,
    )
    assert isinstance(action, ActionSchemaOut)
    assert action.status == ActionStatus.PENDING
    assert not action.result
    return action.action_id


@pytest.mark.flaky(
    reruns=10, reruns_delay=10, only_rerun=["AssertionError", "ApiException"]
)  # give kubernetes time to actually create the job
def test_openshift_trigger_cronjob_success(
    action_id: str,
    wait_for_action_success: Callable,
    config: Config,
    openshift_client: OpenshiftClient,
) -> None:
    # wait for the action to complete and assert it was successful
    wait_for_action_success(
        action_id=action_id,
        retries=config.openshift_trigger_cronjob.retries,
        sleep_time=config.openshift_trigger_cronjob.sleep_time,
    )

    # verify that a job was created from the cronjob
    for job in openshift_client.batch_v1.list_namespaced_job(
        namespace=config.openshift_trigger_cronjob.namespace
    ).items:
        if (
            config.openshift_trigger_cronjob.cronjob in job.metadata.name
            and job.metadata.creation_timestamp >= dt.now(UTC) - timedelta(minutes=5)
        ):
            # found a recent job created from the cronjob
            return

    pytest.fail("No job was created from the cronjob")
