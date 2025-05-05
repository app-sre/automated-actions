# ruff: noqa: S106, SLF001
from unittest.mock import MagicMock

import hvac
import hvac.exceptions
import pytest
from pytest_mock import MockerFixture

from automated_actions.utils.vault_client import (
    SECRET_VERSION_LATEST,
    VERSION_1,
    VERSION_2,
    SecretAccessForbiddenError,
    SecretNotFoundError,
    SecretVersionIsNoneError,
    VaultClient,
    VaultClientMissingArgsError,
)


@pytest.fixture
def mock_hvac_client(mocker: MockerFixture) -> MagicMock:
    return mocker.MagicMock(hvac.Client)


@pytest.fixture
def vault_client(mocker: MockerFixture, mock_hvac_client: MagicMock) -> VaultClient:
    mocker.patch("automated_actions.utils.vault_client.Kubernetes", autospec=True)
    return VaultClient(
        server_url="https://vault.example.com",
        role_id="test-role-id",
        secret_id="test-secret-id",
        hvac_client=mock_hvac_client,
    )


def test_vault_client_init_with_approle(mock_hvac_client: MagicMock) -> None:
    VaultClient(
        server_url="https://vault.example.com",
        role_id="test-role-id",
        secret_id="test-secret-id",
        hvac_client=mock_hvac_client,
    )
    mock_hvac_client.return_value.auth.approle.login.assert_called_once_with(
        role_id="test-role-id", secret_id="test-secret-id"
    )


def test_vault_client_init_with_kubernetes(
    mock_hvac_client: MagicMock, mocker: MockerFixture
) -> None:
    auth_kubernetes = mocker.patch(
        "automated_actions.utils.vault_client.Kubernetes", autospec=True
    )
    mocker.patch(
        "automated_actions.utils.vault_client.Path.read_text", return_value="jwt-token"
    )
    VaultClient(
        server_url="https://vault.example.com",
        kube_auth_role="test-role",
        kube_auth_mount="test-mount",
        hvac_client=mock_hvac_client,
    )
    auth_kubernetes.return_value.login.assert_called_once_with(
        role="test-role", jwt="jwt-token", mount_point="test-mount"
    )


def test_vault_client_init_missing_args() -> None:
    with pytest.raises(VaultClientMissingArgsError):
        VaultClient(server_url="https://vault.example.com")


def test_read_secret_v2_success(
    vault_client: VaultClient, mock_hvac_client: MagicMock
) -> None:
    mock_hvac_client.return_value.secrets.kv.v2.read_secret_version.return_value = {
        "data": {
            "data": {"key": "value"},
            "metadata": {"version": 2},
        }
    }

    result = vault_client.read_secret("mount/path", version=SECRET_VERSION_LATEST)

    assert result == {"key": "value"}
    mock_hvac_client.return_value.secrets.kv.v2.read_secret_version.assert_called_once_with(
        mount_point="mount", path="path", version=None
    )


def test_read_secret_v1_success(
    vault_client: VaultClient, mock_hvac_client: MagicMock
) -> None:
    mock_hvac_client.return_value.secrets.kv.v1.read_secret.return_value = {
        "data": {"key": "value"}
    }
    mock_hvac_client.return_value.secrets.kv.v2.read_configuration.side_effect = (
        hvac.exceptions.Forbidden("error")
    )

    result = vault_client.read_secret("mount/path")

    assert result == {"key": "value"}
    mock_hvac_client.return_value.secrets.kv.v1.read_secret.assert_called_once_with(
        mount_point="mount", path="path"
    )


def test_read_secret_not_found(
    vault_client: VaultClient, mock_hvac_client: MagicMock
) -> None:
    mock_hvac_client.return_value.secrets.kv.v2.read_secret_version.return_value = None

    with pytest.raises(SecretNotFoundError):
        vault_client.read_secret("mount/path", version=SECRET_VERSION_LATEST)


def test_read_secret_access_forbidden(
    vault_client: VaultClient, mock_hvac_client: MagicMock
) -> None:
    mock_hvac_client.return_value.secrets.kv.v2.read_secret_version.side_effect = (
        hvac.exceptions.Forbidden
    )

    with pytest.raises(SecretAccessForbiddenError):
        vault_client.read_secret("mount/path", version=SECRET_VERSION_LATEST)


def test_read_secret_version_is_none(vault_client: VaultClient) -> None:
    with pytest.raises(SecretVersionIsNoneError):
        vault_client.read_secret("mount/path", version=None)


def test_get_mount_version_v2(
    vault_client: VaultClient, mock_hvac_client: MagicMock
) -> None:
    mock_hvac_client.return_value.secrets.kv.v2.read_configuration.return_value = {}

    version = vault_client._get_mount_version("mount")

    assert version == VERSION_2
    mock_hvac_client.return_value.secrets.kv.v2.read_configuration.assert_called_once_with(
        "mount"
    )


def test_get_mount_version_v1(
    vault_client: VaultClient, mock_hvac_client: MagicMock
) -> None:
    mock_hvac_client.return_value.secrets.kv.v2.read_configuration.side_effect = (
        hvac.exceptions.Forbidden
    )

    version = vault_client._get_mount_version("mount")

    assert version == VERSION_1
