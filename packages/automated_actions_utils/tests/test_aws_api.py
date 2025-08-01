# ruff: noqa: S105
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel
from pytest_mock import MockerFixture

from automated_actions_utils.aws_api import (
    AWSApi,
    AWSStaticCredentials,
    LogStream,
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
def test_aws_api_init_and_client_setup(
    mock_aws_credentials: MagicMock,
    mock_boto_config: MagicMock,
    region_input: str | None,
    expected_region_in_config: str | None,
) -> None:
    """Tests the __init__ method of AWSApi and both RDS and S3 client setup."""
    mock_session = mock_aws_credentials.build_session.return_value
    mock_rds_client_returned_by_session = MagicMock()
    mock_s3_client_returned_by_session = MagicMock()

    # Configure session.client to return different mocks based on service
    def client_side_effect(service_name: str, **_: Any) -> MagicMock:
        if service_name == "rds":
            return mock_rds_client_returned_by_session
        if service_name == "s3":
            return mock_s3_client_returned_by_session
        raise ValueError(f"Unexpected service: {service_name}")

    mock_session.client.side_effect = client_side_effect

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

    # Verify both RDS and S3 clients were created
    mock_session.client.assert_any_call("rds", config=aws_api.config)
    mock_session.client.assert_any_call("s3", config=aws_api.config, endpoint_url=None)

    # And that both clients are properly assigned
    assert aws_api.rds_client == mock_rds_client_returned_by_session
    assert aws_api.s3_client == mock_s3_client_returned_by_session


def test_aws_api_init_with_s3_endpoint_url(mock_aws_credentials: MagicMock) -> None:
    """Tests AWSApi initialization with a custom S3 endpoint URL."""
    mock_session = mock_aws_credentials.build_session.return_value
    mock_rds_client = MagicMock()
    mock_s3_client = MagicMock()

    def client_side_effect(service_name: str, **_: Any) -> MagicMock:
        if service_name == "rds":
            return mock_rds_client
        if service_name == "s3":
            return mock_s3_client
        raise ValueError(f"Unexpected service: {service_name}")

    mock_session.client.side_effect = client_side_effect

    s3_endpoint = "https://localstack:4566"
    aws_api = AWSApi(
        credentials=mock_aws_credentials,
        region="us-west-2",
        s3_endpoint_url=s3_endpoint,
    )

    # Verify S3 client was called with the custom endpoint URL
    mock_session.client.assert_any_call(
        "s3", config=aws_api.config, endpoint_url=s3_endpoint
    )
    assert aws_api.s3_client == mock_s3_client


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


@pytest.mark.parametrize(
    ("region", "identifier", "paginator_return_value", "expected_log_files"),
    [
        (
            "us-west-2",
            "test-db-instance",
            [
                {
                    "DescribeDBLogFiles": [
                        {"LogFileName": "error/mysql-error.log"},
                        {"LogFileName": "slowquery/mysql-slowquery.log"},
                    ]
                }
            ],
            ["error/mysql-error.log", "slowquery/mysql-slowquery.log"],
        ),
        (
            "us-east-1",
            "postgres-instance",
            [{"DescribeDBLogFiles": [{"LogFileName": "postgresql.log"}]}],
            ["postgresql.log"],
        ),
        (
            "eu-west-1",
            "empty-instance",
            [{"DescribeDBLogFiles": []}],
            [],
        ),
        (
            "ap-south-1",
            "multi-page-db",
            [
                {"DescribeDBLogFiles": [{"LogFileName": "error.log"}]},
                {
                    "DescribeDBLogFiles": [
                        {"LogFileName": "slow.log"},
                        {"LogFileName": "general.log"},
                    ]
                },
            ],
            ["error.log", "slow.log", "general.log"],
        ),
        (
            "eu-north-1",
            "missing-key-db",
            [
                {"DescribeDBLogFiles": [{"LogFileName": "valid.log"}]},
                {"NotDescribeDBLogFiles": []},  # Page missing 'DescribeDBLogFiles' key
            ],
            ["valid.log"],
        ),
        (
            "ca-central-1",
            "empty-filename-db",
            [
                {
                    "DescribeDBLogFiles": [
                        {"LogFileName": "valid.log"},
                        {"LogFileName": ""},  # Empty filename should be filtered out
                        {"LogFileName": "another.log"},
                    ]
                }
            ],
            ["valid.log", "another.log"],
        ),
    ],
    ids=[
        "success_single_page",
        "postgres_instance",
        "empty_instance",
        "multiple_pages",
        "missing_key_in_page",
        "empty_filename_filtered",
    ],
)
def test_aws_api_list_rds_logs(
    mock_aws_credentials: MagicMock,
    mocker: MockerFixture,
    region: str,
    identifier: str,
    paginator_return_value: list[dict[str, list[dict[str, str]]]],
    expected_log_files: list[str],
) -> None:
    """Tests the list_rds_logs method of AWSApi with paginated responses."""
    aws_api = AWSApi(credentials=mock_aws_credentials, region=region)

    mock_rds_client_on_instance = mocker.MagicMock()
    aws_api.rds_client = mock_rds_client_on_instance

    mock_paginator = mocker.MagicMock()
    mock_rds_client_on_instance.get_paginator.return_value = mock_paginator
    mock_paginator.paginate.return_value = paginator_return_value

    result = aws_api.list_rds_logs(identifier=identifier)

    mock_rds_client_on_instance.get_paginator.assert_called_once_with(
        "describe_db_log_files"
    )
    mock_paginator.paginate.assert_called_once_with(DBInstanceIdentifier=identifier)
    assert result == expected_log_files


@pytest.mark.parametrize(
    ("region", "identifier", "log_file", "log_data_chunks"),
    [
        ("us-west-2", "test-db", "error.log", ["log line 1\n", "log line 2\n"]),
        ("us-east-1", "test-db", "slow.log", ["slow query data\n"]),
        ("eu-west-1", "test-db", "empty.log", []),
    ],
)
def test_aws_api_stream_rds_log(
    mock_aws_credentials: MagicMock,
    mocker: MockerFixture,
    region: str,
    identifier: str,
    log_file: str,
    log_data_chunks: list[str],
) -> None:
    """Tests the stream_rds_log method of AWSApi."""
    aws_api = AWSApi(credentials=mock_aws_credentials, region=region)

    mock_rds_client_on_instance = mocker.MagicMock()
    aws_api.rds_client = mock_rds_client_on_instance

    # Mock sequential responses for download_db_log_file_portion
    mock_responses = []
    for i, chunk in enumerate(log_data_chunks):
        is_last = i == len(log_data_chunks) - 1
        mock_responses.append({
            "LogFileData": chunk,
            "Marker": str(i + 1),
            "AdditionalDataPending": not is_last,
        })

    # If no chunks, return a single response with empty data
    if not log_data_chunks:
        mock_responses = [
            {
                "LogFileData": "",
                "Marker": "0",
                "AdditionalDataPending": False,
            }
        ]

    mock_rds_client_on_instance.download_db_log_file_portion.side_effect = (
        mock_responses
    )

    # Collect all streamed data
    result_data = b"".join(
        aws_api.stream_rds_log(identifier=identifier, log_file=log_file)
    )

    # Verify the expected data was returned
    expected_data = "".join(log_data_chunks).encode("utf-8")
    assert result_data == expected_data

    # Verify the RDS client was called correctly
    expected_calls = len(mock_responses)
    assert (
        mock_rds_client_on_instance.download_db_log_file_portion.call_count
        == expected_calls
    )


@pytest.mark.parametrize(
    ("region", "bucket", "s3_key", "log_stream_count"),
    [
        ("us-west-2", "test-bucket", "logs/test.zip", 2),
        ("us-east-1", "my-bucket", "rds-logs/instance-logs.zip", 1),
        ("eu-west-1", "backup-bucket", "logs/backup.zip", 0),
    ],
)
def test_aws_api_stream_rds_logs_to_s3_zip(
    mock_aws_credentials: MagicMock,
    mocker: MockerFixture,
    region: str,
    bucket: str,
    s3_key: str,
    log_stream_count: int,
) -> None:
    """Tests the stream_rds_logs_to_s3_zip method of AWSApi."""
    aws_api = AWSApi(credentials=mock_aws_credentials, region=region)

    mock_s3_client_on_instance = mocker.MagicMock()
    aws_api.s3_client = mock_s3_client_on_instance

    # Mock S3 multipart upload responses
    upload_id = "test-upload-id"
    mock_s3_client_on_instance.create_multipart_upload.return_value = {
        "UploadId": upload_id
    }
    mock_s3_client_on_instance.upload_part.return_value = {"ETag": "test-etag"}

    # Create test log streams
    log_streams = []
    for i in range(log_stream_count):

        def generate_log_content() -> Generator[bytes, Any, None]:
            yield b"log data chunk 1"
            yield b"log data chunk 2"

        log_streams.append(
            LogStream(name=f"test-log-{i}.log", content=generate_log_content())
        )

    # Mock ZipStream to avoid actual zip creation
    mock_zip_stream = mocker.patch("automated_actions_utils.aws_api.ZipStream")
    mock_zip_instance = mocker.MagicMock()
    mock_zip_stream.return_value = mock_zip_instance
    mock_zip_instance.__iter__.return_value = iter([b"zip content chunk"])

    # Mock _upload_multipart_chunk
    mocker.patch.object(
        aws_api,
        "_upload_multipart_chunk",
        return_value={"PartNumber": 1, "ETag": "test-etag"},
    )

    aws_api.stream_rds_logs_to_s3_zip(
        log_streams=log_streams,
        bucket=bucket,
        s3_key=s3_key,
    )

    # Verify S3 operations were called
    mock_s3_client_on_instance.create_multipart_upload.assert_called_once_with(
        Bucket=bucket, Key=s3_key, ContentType="application/zip"
    )
    mock_s3_client_on_instance.complete_multipart_upload.assert_called_once()

    # Verify log streams were added to zip
    assert mock_zip_instance.add.call_count == log_stream_count


@pytest.mark.parametrize("region", ["us-west-2"])
def test_aws_api_stream_rds_logs_to_s3_zip_with_target_api(
    mock_aws_credentials: MagicMock,
    mocker: MockerFixture,
    region: str,
) -> None:
    """Tests stream_rds_logs_to_s3_zip with a different target AWS API."""
    source_aws_api = AWSApi(credentials=mock_aws_credentials, region=region)
    target_aws_api = AWSApi(credentials=mock_aws_credentials, region="us-east-1")

    mock_target_s3_client = mocker.MagicMock()
    target_aws_api.s3_client = mock_target_s3_client

    upload_id = "test-upload-id"
    mock_target_s3_client.create_multipart_upload.return_value = {"UploadId": upload_id}

    # Mock ZipStream
    mock_zip_stream = mocker.patch("automated_actions_utils.aws_api.ZipStream")
    mock_zip_instance = mocker.MagicMock()
    mock_zip_stream.return_value = mock_zip_instance
    mock_zip_instance.__iter__.return_value = iter([b"zip content"])

    # Mock _upload_multipart_chunk
    mocker.patch.object(
        source_aws_api,
        "_upload_multipart_chunk",
        return_value={"PartNumber": 1, "ETag": "test-etag"},
    )

    log_streams = [LogStream(name="test.log", content=iter([b"test data"]))]

    source_aws_api.stream_rds_logs_to_s3_zip(
        log_streams=log_streams,
        bucket="test-bucket",
        s3_key="test.zip",
        target_aws_api=target_aws_api,
    )

    # Verify the target API was used for S3 operations
    mock_target_s3_client.create_multipart_upload.assert_called_once()
    mock_target_s3_client.complete_multipart_upload.assert_called_once()


@pytest.mark.parametrize(
    ("region", "bucket", "s3_key", "expiration_secs", "expected_url"),
    [
        (
            "us-west-2",
            "test-bucket",
            "logs/test.zip",
            3600,
            "https://s3.amazonaws.com/test-bucket/logs/test.zip",
        ),
        (
            "us-east-1",
            "my-logs",
            "rds.zip",
            7200,
            "https://s3.amazonaws.com/my-logs/rds.zip",
        ),
    ],
)
def test_aws_api_generate_s3_download_url(
    mock_aws_credentials: MagicMock,
    mocker: MockerFixture,
    region: str,
    bucket: str,
    s3_key: str,
    expiration_secs: int,
    expected_url: str,
) -> None:
    """Tests the generate_s3_download_url method of AWSApi."""
    aws_api = AWSApi(credentials=mock_aws_credentials, region=region)

    mock_s3_client_on_instance = mocker.MagicMock()
    aws_api.s3_client = mock_s3_client_on_instance

    mock_s3_client_on_instance.generate_presigned_url.return_value = expected_url

    result = aws_api.generate_s3_download_url(
        bucket=bucket, s3_key=s3_key, expiration_secs=expiration_secs
    )

    mock_s3_client_on_instance.generate_presigned_url.assert_called_once_with(
        "get_object",
        Params={"Bucket": bucket, "Key": s3_key},
        ExpiresIn=expiration_secs,
    )
    assert result == expected_url
