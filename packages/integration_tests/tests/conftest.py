from collections.abc import Callable
from time import sleep

import pytest
from automated_actions_client import AuthenticatedClient
from automated_actions_client.api.general import action_detail
from automated_actions_client.models.action_schema_out import ActionSchemaOut
from automated_actions_client.models.action_status import ActionStatus
from pydantic import BaseModel, HttpUrl
from pydantic_settings import BaseSettings


class BaseParameters(BaseModel):
    retries: int = 10
    sleep_time: int = 10


class ExternalResourceFlushElasticache(BaseParameters):
    account: str
    identifier: str


class ExternalResourceRDSReboot(BaseParameters):
    account: str
    identifier: str


class ExternalResourceRDSSnapshot(BaseParameters):
    account: str
    identifier: str
    snapshot_identifier: str


class NoOpParameters(BaseParameters):
    pass


class OpenshiftDeploymentRestartParameters(BaseParameters):
    cluster: str
    namespace: str
    name: str


class OpenshiftPodRestartParameters(BaseParameters):
    cluster: str
    namespace: str
    parent_kind: str
    parent_kind_name: str


class Config(BaseSettings):
    """Configuration for the tests."""

    model_config = {"env_prefix": "aait_", "env_nested_delimiter": "__"}

    # ATTENTION: You also need to add all required environment variables to the
    # Openshift template (openshift/integration-tests.yaml)!

    # general
    url: HttpUrl = HttpUrl("http://localhost:8080")
    token: str

    external_resource_flush_elasticache: ExternalResourceFlushElasticache
    external_resource_rds_reboot: ExternalResourceRDSReboot
    external_resource_rds_snapshot: ExternalResourceRDSSnapshot
    no_op: NoOpParameters = NoOpParameters(sleep_time=2)
    openshift_deployment_restart: OpenshiftDeploymentRestartParameters
    openshift_pod_restart: OpenshiftPodRestartParameters


_config = Config()


@pytest.fixture(scope="session", autouse=True)
def config() -> Config:
    """Test that the environment variables are set correctly."""
    return _config


@pytest.fixture(scope="session")
def aa_client(config: Config) -> AuthenticatedClient:
    return AuthenticatedClient(
        base_url=str(config.url),
        token=config.token,
        raise_on_unexpected_status=True,
        follow_redirects=True,
    )


@pytest.fixture
def wait_for_action_completion(
    aa_client: AuthenticatedClient,
) -> Callable[[str, int, int], ActionSchemaOut]:
    """Wait for the action to complete and return the action details."""

    def _wait_for_completion(
        action_id: str, retries: int, sleep_time: int
    ) -> ActionSchemaOut:
        retry = 1
        detail = action_detail.sync(client=aa_client, action_id=action_id)
        assert isinstance(detail, ActionSchemaOut)

        while retry <= retries and detail.status in {
            ActionStatus.PENDING,
            ActionStatus.RUNNING,
        }:
            detail = action_detail.sync(client=aa_client, action_id=action_id)
            assert isinstance(detail, ActionSchemaOut)
            retry += 1
            sleep(sleep_time)

        assert isinstance(detail, ActionSchemaOut)
        return detail

    return _wait_for_completion


@pytest.fixture
def wait_for_action_success(
    wait_for_action_completion: Callable[[str, int, int], ActionSchemaOut],
) -> Callable[[str, int, int], ActionSchemaOut]:
    """Wait for the action to complete and assert it was successful."""

    def _wait_for_success(
        action_id: str, retries: int, sleep_time: int
    ) -> ActionSchemaOut:
        detail = wait_for_action_completion(action_id, retries, sleep_time)
        assert detail.status == ActionStatus.SUCCESS
        return detail

    return _wait_for_success
