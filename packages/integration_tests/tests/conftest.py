from time import sleep
from typing import TYPE_CHECKING

import pytest
from automated_actions_client.client import action_detail
from automated_actions_client.client import client as aa_api_client
from automated_actions_client.config import Config as ClientConfig
from automated_actions_client.schemas import ActionSchemaOut, ActionStatus
from pydantic import BaseModel, HttpUrl
from pydantic_settings import BaseSettings

if TYPE_CHECKING:
    from collections.abc import Callable


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


class OpenshiftTriggerCronJobParameters(BaseParameters):
    cluster: str
    namespace: str
    cronjob: str


class OpenshiftWorkloadDeleteParameters(BaseParameters):
    cluster: str
    namespace: str


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
    openshift_trigger_cronjob: OpenshiftTriggerCronJobParameters
    openshift_workload_delete: OpenshiftWorkloadDeleteParameters


_config = Config()


@pytest.fixture(scope="session", autouse=True)
def config() -> Config:
    """Test that the environment variables are set correctly."""
    return _config


@pytest.fixture(scope="session", autouse=True)
def _configure_client(config: Config) -> None:
    """Configure the clientele API client singleton."""
    aa_api_client.configure(
        config=ClientConfig(
            base_url=str(config.url),
            headers={"Authorization": f"Bearer {config.token}"},
            follow_redirects=True,
        )
    )


@pytest.fixture
def wait_for_action_completion() -> Callable[[str, int, int], ActionSchemaOut]:
    """Wait for the action to complete and return the action details."""

    def _wait_for_completion(
        action_id: str, retries: int, sleep_time: int
    ) -> ActionSchemaOut:
        retry = 1
        detail = action_detail(action_id=action_id)
        assert isinstance(detail, ActionSchemaOut)

        while retry <= retries and detail.status in {
            ActionStatus.PENDING,
            ActionStatus.RUNNING,
        }:
            detail = action_detail(action_id=action_id)
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
