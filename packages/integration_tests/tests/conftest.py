import pytest
from automated_actions_client import AuthenticatedClient
from pydantic import BaseModel, HttpUrl
from pydantic_settings import BaseSettings


class OpenshiftDeploymentRestartParameters(BaseModel):
    cluster: str
    namespace: str
    name: str
    retries: int = 10
    sleep_time: int = 10


class OpenshiftPodRestartParameters(BaseModel):
    cluster: str
    namespace: str
    parent_kind: str
    parent_kind_name: str
    retries: int = 10
    sleep_time: int = 10


class NoOpParameters(BaseModel):
    retries: int = 10
    sleep_time: int = 2


class Config(BaseSettings):
    """Configuration for the tests."""

    model_config = {"env_prefix": "aait_", "env_nested_delimiter": "__"}

    # ATTENTION: You also need to add all required environment variables to the
    # Openshift template (openshift/integration-tests.yaml)!

    # general
    url: HttpUrl = HttpUrl("http://localhost:8080")
    token: str

    openshift_deployment_restart: OpenshiftDeploymentRestartParameters
    openshift_pod_restart: OpenshiftPodRestartParameters
    no_op: NoOpParameters = NoOpParameters()


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
