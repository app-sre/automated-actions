import pytest
from automated_actions_client import AuthenticatedClient
from pydantic import HttpUrl
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Configuration for the tests."""

    model_config = {"env_prefix": "aa_"}

    # ATTENTION: You also need to add all required environment variables to the
    # Openshift template (openshift/integration-tests.yaml)!

    # general
    url: HttpUrl = HttpUrl("http://localhost:8080")
    token: str
    action_timeout_seconds: int = 30
    retries: int = 10

    # openshift
    cluster: str
    namespace: str
    kind: str
    name: str


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
