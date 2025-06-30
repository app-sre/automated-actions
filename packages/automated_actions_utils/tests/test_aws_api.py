# ruff: noqa: S105
from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel
from pytest_mock import MockerFixture

from automated_actions_utils.aws_api import (
    AWSApi,
    AWSStaticCredentials,
    get_aws_credentials,
)
from automated_actions_utils.vault_client import SecretFieldNotFoundError


@pytest.fixture(autouse=True)
def mock_settings(mocker: MockerFixture) -> MagicMock:
    """Mocks the settings used by VaultClient."""
    settings_mock = mocker.patch("automated_actions_utils.aws_api.settings")
    settings_mock.vault_server_url = "http://vault.example.com"
    settings_mock.vault_role_id = "test_role_id"
    settings_mock.vault_secret_id = "test_secret_id"
    settings_mock.vault_kube_auth_role = "test_kube_role"
    settings_mock.vault_kube_auth_mount = "test_kube_mount"
    return settings_mock


@pytest.fixture
def mock_vault_client_instance(mocker: MockerFixture) -> MagicMock:
    """Mocks the VaultClient instance and its methods."""
    mock_instance = MagicMock()
    mocker.patch(
        "automated_actions_utils.aws_api.VaultClient", return_value=mock_instance
    )
    return mock_instance


class VaultSecret(BaseModel):
    path: str
    field: str
    version: int | None = None
    q_format: str | None = None


@pytest.mark.parametrize(
    (
        "secret_data",
        "vault_secret_args",
        "region",
        "expect_exception",
        "expected_details",
    ),
    [
        (
            {"aws_access_key_id": "key1", "aws_secret_access_key": "secret1"},
            {"path": "secret/path1", "field": "data", "version": 1},
            "us-west-2",
            None,
            {
                "access_key_id": "key1",
                "secret_access_key": "secret1",
                "region": "us-west-2",
                "read_secret_version_arg": "1",
            },
        ),
        (
            {"aws_access_key_id": "key2", "aws_secret_access_key": "secret2"},
            {"path": "secret/path2", "field": "data", "version": None},
            "eu-central-1",
            None,
            {
                "access_key_id": "key2",
                "secret_access_key": "secret2",
                "region": "eu-central-1",
                "read_secret_version_arg": "None",
            },
        ),
        (
            {"aws_secret_access_key": "secret3"},
            {"path": "secret/missing_key", "field": "data", "version": 2},
            "ap-southeast-1",
            SecretFieldNotFoundError,
            {
                "error_msg_parts": [
                    "aws_access_key_id or aws_secret_access_key not found",
                    "secret/missing_key",
                ],
                "read_secret_version_arg": "2",
            },
        ),
        (
            {"aws_access_key_id": "key4"},
            {"path": "secret/missing_secret", "field": "data", "version": 3},
            "ca-central-1",
            SecretFieldNotFoundError,
            {
                "error_msg_parts": [
                    "aws_access_key_id or aws_secret_access_key not found",
                    "secret/missing_secret",
                ],
                "read_secret_version_arg": "3",
            },
        ),
    ],
    ids=[
        "success_with_version",
        "success_none_version",
        "missing_access_key",
        "missing_secret_key",
    ],
)
def test_get_aws_credentials(
    mock_vault_client_instance: MagicMock,
    secret_data: dict[str, str],
    vault_secret_args: dict[str, Any],
    region: str,
    expect_exception: type[Exception] | None,
    expected_details: dict[str, Any],
) -> None:
    """Tests get_aws_credentials with various scenarios."""
    mock_vault_client_instance.read_secret.return_value = secret_data
    vault_secret = VaultSecret(**vault_secret_args)

    if expect_exception:
        with pytest.raises(expect_exception) as excinfo:
            get_aws_credentials(vault_secret, region)
        for part in expected_details["error_msg_parts"]:
            assert part in str(excinfo.value)
    else:
        credentials = get_aws_credentials(vault_secret, region)
        assert isinstance(credentials, AWSStaticCredentials)
        assert credentials.access_key_id == expected_details["access_key_id"]
        assert credentials.secret_access_key == expected_details["secret_access_key"]
        assert credentials.region == region

    mock_vault_client_instance.read_secret.assert_called_once_with(
        path=vault_secret_args["path"],
        version=expected_details["read_secret_version_arg"],
    )


@pytest.fixture
def mock_aws_credentials(mocker: MockerFixture) -> MagicMock:
    """Mocks AWSCredentials and its build_session method."""
    mock_creds = mocker.MagicMock(spec=AWSStaticCredentials)
    mock_session = mocker.MagicMock()
    # Ensure that the client attribute of the mock_session is also a MagicMock
    # to allow asserting calls on it, like session.client("rds", ...)
    mock_session.client = mocker.MagicMock()
    mock_creds.build_session.return_value = mock_session
    return mock_creds


@pytest.fixture
def mock_boto_config(mocker: MockerFixture) -> MagicMock:
    """Mocks botocore.config.Config."""
    return mocker.patch("automated_actions_utils.aws_api.Config")


@pytest.mark.parametrize(
    ("region_input", "expected_region_in_config"),
    [
        ("us-east-1", "us-east-1"),
        (None, None),
    ],
    ids=["with_region", "none_region"],
)
def test_aws_api_init_and_rds_client_setup(
    mock_aws_credentials: MagicMock,
    mock_boto_config: MagicMock,
    region_input: str | None,
    expected_region_in_config: str | None,
) -> None:
    """Tests the __init__ method of AWSApi and RDS client setup."""
    mock_session = mock_aws_credentials.build_session.return_value
    mock_rds_client_returned_by_session = MagicMock()
    mock_session.client.return_value = mock_rds_client_returned_by_session

    aws_api = AWSApi(credentials=mock_aws_credentials, region=region_input)

    mock_aws_credentials.build_session.assert_called_once()
    assert aws_api.session == mock_session

    mock_boto_config.assert_called_once_with(
        region_name=expected_region_in_config,
        retries={
            "max_attempts": 5,
            "mode": "standard",
        },
    )
    assert aws_api.config == mock_boto_config.return_value

    # This checks that AWSApi.__init__ called self.session.client(...) correctly
    mock_session.client.assert_called_once_with("rds", config=aws_api.config)
    # And that aws_api.rds_client is the instance returned by that call
    assert aws_api.rds_client == mock_rds_client_returned_by_session


@pytest.mark.parametrize(
    ("region", "identifier", "force_failover"),
    [
        ("ap-northeast-1", "test-db-instance", True),
        ("sa-east-1", "another-db", False),
    ],
    ids=["force_failover_true", "force_failover_false"],
)
def test_aws_api_reboot_rds_instance(
    mock_aws_credentials: MagicMock,
    mocker: MockerFixture,
    region: str,
    identifier: str,
    *,
    force_failover: bool,
) -> None:
    """Tests the reboot_rds_instance method of AWSApi."""
    aws_api = AWSApi(credentials=mock_aws_credentials, region=region)

    mock_rds_client_on_instance = mocker.MagicMock()
    aws_api.rds_client = mock_rds_client_on_instance

    aws_api.reboot_rds_instance(identifier=identifier, force_failover=force_failover)

    mock_rds_client_on_instance.reboot_db_instance.assert_called_once_with(
        DBInstanceIdentifier=identifier, ForceFailover=force_failover
    )


@pytest.mark.parametrize(
    (
        "region",
        "identifier",
        "duration_min",
        "paginator_return_value",
        "expected_events",
    ),
    [
        (
            "eu-central-1",
            "test-db-instance",
            60,
            [{"Events": [{"Message": "Event 1"}, {"Message": "Event 2"}]}],
            [{"Message": "Event 1"}, {"Message": "Event 2"}],
        ),
        (
            "us-west-1",
            "no-events-db",
            30,
            [{"Events": []}],
            [],
        ),
        (
            "ap-south-1",
            "multi-page-db",
            120,
            [
                {"Events": [{"Message": "Page 1 Event 1"}]},
                {
                    "Events": [
                        {"Message": "Page 2 Event 1"},
                        {"Message": "Page 2 Event 2"},
                    ]
                },
            ],
            [
                {"Message": "Page 1 Event 1"},
                {"Message": "Page 2 Event 1"},
                {"Message": "Page 2 Event 2"},
            ],
        ),
        (
            "eu-north-1",
            "missing-key-db",
            45,
            [
                {"Events": [{"Message": "Event A"}]},
                {
                    "NotEvents": [{"Message": "Should be ignored"}]
                },  # Page missing 'Events' key
            ],
            [{"Message": "Event A"}],
        ),
        (
            "sa-east-1",
            "empty-response-db",
            15,
            [],
            [],
        ),
        (
            "af-south-1",
            "none-response-db",
            10,
            None,
            [],
        ),
    ],
    ids=[
        "success_single_page",
        "no_events",
        "multiple_pages",
        "events_key_missing_in_page",
        "empty_paginator_response",
        "paginator_response_none",
    ],
)
def test_aws_api_rds_get_events(
    mock_aws_credentials: MagicMock,
    mocker: MockerFixture,
    region: str,
    identifier: str,
    duration_min: int,
    paginator_return_value: list[dict[str, list[dict[str, str]]]] | None,
    expected_events: list[dict[str, str]],
) -> None:
    """Tests the rds_get_events method of AWSApi with various scenarios."""
    aws_api = AWSApi(credentials=mock_aws_credentials, region=region)

    # Mock the rds_client *instance variable* on aws_api
    mock_rds_client_on_instance = mocker.MagicMock()
    aws_api.rds_client = mock_rds_client_on_instance

    mock_paginator = mocker.MagicMock()
    mock_rds_client_on_instance.get_paginator.return_value = mock_paginator
    mock_paginator.paginate.return_value = (
        paginator_return_value if paginator_return_value is not None else iter([])
    )

    events = aws_api.rds_get_events(identifier=identifier, duration_min=duration_min)

    mock_rds_client_on_instance.get_paginator.assert_called_once_with("describe_events")
    mock_paginator.paginate.assert_called_once_with(
        SourceIdentifier=identifier, SourceType="db-instance", Duration=duration_min
    )
    assert events == expected_events


@pytest.mark.parametrize(
    ("region", "identifier", "snapshot_identifier"),
    [
        ("eu-central-1", "test-db-instance", "test-snapshot-identifier"),
    ],
    ids=["success"],
)
def test_aws_api_create_rds_snapshot(
    mock_aws_credentials: MagicMock,
    mocker: MockerFixture,
    region: str,
    identifier: str,
    snapshot_identifier: str,
) -> None:
    """Tests the create_rds_snapshot method of AWSApi."""
    aws_api = AWSApi(credentials=mock_aws_credentials, region=region)

    mock_rds_client_on_instance = mocker.MagicMock()
    aws_api.rds_client = mock_rds_client_on_instance

    aws_api.create_rds_snapshot(
        identifier=identifier, snapshot_identifier=snapshot_identifier
    )

    mock_rds_client_on_instance.create_db_snapshot.assert_called_once_with(
        DBInstanceIdentifier=identifier, DBSnapshotIdentifier=snapshot_identifier
    )
