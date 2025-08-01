import uuid
from unittest.mock import ANY, Mock

import pytest
from automated_actions_utils.aws_api import AWSApi, AWSStaticCredentials
from automated_actions_utils.cluster_connection import ClusterConnectionData
from automated_actions_utils.external_resource import (
    AwsAccount,
    ExternalResource,
    VaultSecret,
)
from pytest_mock import MockerFixture

from automated_actions.celery.external_resource.tasks import (
    ExternalResourceFlushElastiCache,
    ExternalResourceRDSLogs,
    ExternalResourceRDSReboot,
    external_resource_flush_elasticache,
    external_resource_rds_logs,
    external_resource_rds_reboot,
)
from automated_actions.db.models import ActionStatus


@pytest.fixture
def mock_aws(mocker: MockerFixture) -> Mock:
    return mocker.Mock(spec=AWSApi)


@pytest.fixture
def er() -> ExternalResource:
    return ExternalResource(
        identifier="test-identifier",
        region="us-west-2",
        account=AwsAccount(
            name="test-account",
            automation_token=VaultSecret(
                path="test-path", field="test-field", version=None, q_format=None
            ),
            region="us-west-2",
        ),
        name="test-rds",
        cluster="test-cluster",
        namespace="test-namespace",
        output_resource_name="test-output-name",
    )


@pytest.mark.parametrize("force_failover", [True, False])
def test_external_resource_rds_reboot_run(
    mock_aws: Mock, er: ExternalResource, *, force_failover: bool
) -> None:
    automated_action = ExternalResourceRDSReboot(aws_api=mock_aws, rds=er)

    automated_action.run(force_failover=force_failover)

    mock_aws.reboot_rds_instance.assert_called_once_with(
        identifier=er.identifier, force_failover=force_failover
    )


def test_external_resource_rds_reboot_task(
    mocker: MockerFixture, mock_action: Mock, er: ExternalResource
) -> None:
    mocker.patch(
        "automated_actions.celery.external_resource._rds_reboot.get_external_resource",
        return_value=er,
    )
    mocker.patch(
        "automated_actions.celery.external_resource._rds_reboot.get_aws_credentials",
        return_value=AWSStaticCredentials(
            access_key_id="test-access-key",
            secret_access_key="test-secret-key",  # noqa: S106
            region="us-west-2",
        ),
    )
    mock_rds_reboot_run = mocker.patch.object(ExternalResourceRDSReboot, "run")

    action_id = str(uuid.uuid4())
    task_args = {
        "account": "test-account",
        "identifier": "test-identifier",
        "force_failover": False,
    }
    external_resource_rds_reboot.signature(
        kwargs={**task_args, "action": mock_action},
        task_id=action_id,
    ).apply()

    mock_rds_reboot_run.assert_called_once()
    mock_action.set_status.assert_called_once_with(ActionStatus.RUNNING)
    mock_action.set_final_state.assert_called_once_with(
        status=ActionStatus.SUCCESS, result="ok", task_args=task_args
    )


def test_external_resource_rds_reboot_task_non_retryable_failure(
    mocker: MockerFixture, mock_action: Mock, er: ExternalResource
) -> None:
    mocker.patch(
        "automated_actions.celery.external_resource._rds_reboot.get_external_resource",
        return_value=er,
    )
    mocker.patch(
        "automated_actions.celery.external_resource._rds_reboot.get_aws_credentials",
        return_value=AWSStaticCredentials(
            access_key_id="test-access-key",
            secret_access_key="test-secret-key",  # noqa: S106
            region="us-west-2",
        ),
    )
    mock_rds_reboot_run = mocker.patch.object(
        ExternalResourceRDSReboot,
        "run",
        side_effect=Exception("what a failure!"),
    )

    action_id = str(uuid.uuid4())
    task_args = {
        "account": "test-account",
        "identifier": "test-identifier",
        "force_failover": False,
    }
    external_resource_rds_reboot.signature(
        kwargs={**task_args, "action": mock_action},
        task_id=action_id,
    ).apply()

    mock_rds_reboot_run.assert_called_once()
    mock_action.set_status.assert_called_once_with(ActionStatus.RUNNING)
    mock_action.set_final_state.assert_called_once_with(
        status=ActionStatus.FAILURE,
        result="what a failure!",
        task_args=task_args,
    )


def test_external_resource_flush_elasticache_run(
    mock_oc: Mock,
    er: ExternalResource,
    mock_action: Mock,
) -> None:
    automated_action = ExternalResourceFlushElastiCache(
        action=mock_action, oc=mock_oc, elasticache=er
    )

    automated_action.run(
        image="test-image",
        command=["test-command"],
        args=["arg1"],
        secret_name="test-secret",  # noqa: S106
        env_secret_mappings={"ENV_VAR": "test-key"},
    )

    mock_oc.run_job.assert_called_once_with(namespace=er.namespace, job=ANY)


def test_external_resource_flush_elasticache_task(
    mocker: MockerFixture, mock_action: Mock, er: ExternalResource
) -> None:
    mocker.patch(
        "automated_actions.celery.external_resource._elasticache_flush.get_external_resource",
        return_value=er,
    )
    mocker.patch(
        "automated_actions.celery.external_resource._elasticache_flush.get_cluster_connection_data",
        return_value=ClusterConnectionData(
            url="https://test-cluster-url",
            token="test-cluster-token",  # noqa: S106
        ),
    )
    mocker.patch(
        "automated_actions.celery.external_resource._elasticache_flush.OpenshiftClient",
    )
    mock_flush_elasticache_run = mocker.patch.object(
        ExternalResourceFlushElastiCache, "run"
    )

    action_id = str(uuid.uuid4())
    task_args = {
        "account": "test-account",
        "identifier": "test-identifier",
    }
    external_resource_flush_elasticache.signature(
        kwargs={**task_args, "action": mock_action},
        task_id=action_id,
    ).apply()

    mock_flush_elasticache_run.assert_called_once()
    mock_action.set_status.assert_called_once_with(ActionStatus.RUNNING)
    mock_action.set_final_state.assert_called_once_with(
        status=ActionStatus.SUCCESS, result="ok", task_args=task_args
    )


def test_external_resource_flush_elasticache_task_non_retryable_failure(
    mocker: MockerFixture, mock_action: Mock, er: ExternalResource
) -> None:
    mocker.patch(
        "automated_actions.celery.external_resource._elasticache_flush.get_external_resource",
        return_value=er,
    )
    mocker.patch(
        "automated_actions.celery.external_resource._elasticache_flush.get_cluster_connection_data",
        return_value=ClusterConnectionData(
            url="https://test-cluster-url",
            token="test-cluster-token",  # noqa: S106
        ),
    )
    mocker.patch(
        "automated_actions.celery.external_resource._elasticache_flush.OpenshiftClient",
    )
    mock_flush_elasticache_run = mocker.patch.object(
        ExternalResourceFlushElastiCache,
        "run",
        side_effect=Exception("what a failure!"),
    )

    action_id = str(uuid.uuid4())
    task_args = {
        "account": "test-account",
        "identifier": "test-identifier",
    }
    external_resource_flush_elasticache.signature(
        kwargs={**task_args, "action": mock_action},
        task_id=action_id,
    ).apply()

    mock_flush_elasticache_run.assert_called_once()
    mock_action.set_status.assert_called_once_with(ActionStatus.RUNNING)
    mock_action.set_final_state.assert_called_once_with(
        status=ActionStatus.FAILURE,
        result="what a failure!",
        task_args=task_args,
    )


@pytest.fixture
def mock_target_aws(mocker: MockerFixture) -> Mock:
    return mocker.Mock(spec=AWSApi)


def test_external_resource_rds_logs_run_with_default_filename(
    mock_aws: Mock, mock_target_aws: Mock, er: ExternalResource
) -> None:
    s3_bucket = "test-bucket"
    s3_prefix = "logs"
    rds_logs = ExternalResourceRDSLogs(
        aws_api=mock_aws, rds=er, s3_bucket=s3_bucket, s3_prefix=s3_prefix
    )

    mock_aws.list_rds_logs.return_value = ["error.log", "slow.log"]
    mock_aws.stream_rds_log.return_value = iter([b"log content"])
    mock_aws.generate_s3_download_url.return_value = "https://s3.example.com/download"

    result = rds_logs.run(
        target_aws_api=mock_target_aws,
        expiration_days=3,
    )

    expected_s3_key = f"{s3_prefix}/{er.account.name}-{er.identifier}.zip"

    mock_aws.list_rds_logs.assert_called_once_with(er.identifier)
    assert mock_aws.stream_rds_log.call_count == 2  # noqa: PLR2004
    mock_aws.stream_rds_logs_to_s3_zip.assert_called_once()
    mock_aws.generate_s3_download_url.assert_called_once_with(
        bucket=s3_bucket,
        s3_key=expected_s3_key,
        expiration_secs=3 * 24 * 3600,
    )

    assert result == "https://s3.example.com/download"


def test_external_resource_rds_logs_run_with_custom_filename(
    mock_aws: Mock, mock_target_aws: Mock, er: ExternalResource
) -> None:
    s3_bucket = "test-bucket"
    s3_prefix = "logs"
    custom_filename = "custom-logs.zip"
    rds_logs = ExternalResourceRDSLogs(
        aws_api=mock_aws, rds=er, s3_bucket=s3_bucket, s3_prefix=s3_prefix
    )

    mock_aws.list_rds_logs.return_value = ["error.log"]
    mock_aws.stream_rds_log.return_value = iter([b"log content"])
    mock_aws.generate_s3_download_url.return_value = "https://s3.example.com/download"

    result = rds_logs.run(
        target_aws_api=mock_target_aws,
        expiration_days=7,
        s3_file_name=custom_filename,
    )

    mock_aws.stream_rds_logs_to_s3_zip.assert_called_once()
    mock_aws.generate_s3_download_url.assert_called_once_with(
        bucket=s3_bucket,
        s3_key=custom_filename,
        expiration_secs=7 * 24 * 3600,
    )

    assert result == "https://s3.example.com/download"


def test_external_resource_rds_logs_run_appends_zip_extension(
    mock_aws: Mock, mock_target_aws: Mock, er: ExternalResource
) -> None:
    s3_bucket = "test-bucket"
    s3_prefix = "logs"
    filename_without_zip = "custom-logs"
    rds_logs = ExternalResourceRDSLogs(
        aws_api=mock_aws, rds=er, s3_bucket=s3_bucket, s3_prefix=s3_prefix
    )

    mock_aws.list_rds_logs.return_value = ["error.log"]
    mock_aws.stream_rds_log.return_value = iter([b"log content"])
    mock_aws.generate_s3_download_url.return_value = "https://s3.example.com/download"

    rds_logs.run(
        target_aws_api=mock_target_aws,
        expiration_days=1,
        s3_file_name=filename_without_zip,
    )

    call_args = mock_aws.stream_rds_logs_to_s3_zip.call_args
    assert call_args.kwargs["s3_key"] == f"{filename_without_zip}.zip"


def test_external_resource_rds_logs_task(
    mocker: MockerFixture, mock_action: Mock, er: ExternalResource
) -> None:
    mocker.patch(
        "automated_actions.celery.external_resource._rds_logs.get_external_resource",
        return_value=er,
    )
    mocker.patch(
        "automated_actions.celery.external_resource._rds_logs.get_aws_credentials",
        return_value=AWSStaticCredentials(
            access_key_id="test-access-key",
            secret_access_key="test-secret-key",  # noqa: S106
            region="us-west-2",
        ),
    )
    mock_settings = mocker.patch(
        "automated_actions.celery.external_resource._rds_logs.settings"
    )
    mock_settings.external_resource_rds_logs.access_key_id = "log-access-key"
    mock_settings.external_resource_rds_logs.secret_access_key = "log-secret-key"  # noqa: S105
    mock_settings.external_resource_rds_logs.region = "us-east-1"
    mock_settings.external_resource_rds_logs.s3_url = "https://s3.amazonaws.com"
    mock_settings.external_resource_rds_logs.bucket = "log-bucket"
    mock_settings.external_resource_rds_logs.prefix = "rds-logs"

    mock_rds_logs_run = mocker.patch.object(
        ExternalResourceRDSLogs, "run", return_value="https://download.url"
    )

    action_id = str(uuid.uuid4())
    task_args = {
        "account": "test-account",
        "identifier": "test-identifier",
        "expiration_days": 5,
        "s3_file_name": "custom.zip",
    }

    result = (
        external_resource_rds_logs.signature(
            kwargs={**task_args, "action": mock_action},
            task_id=action_id,
        )
        .apply()
        .result
    )

    mock_rds_logs_run.assert_called_once()
    call_args = mock_rds_logs_run.call_args
    assert call_args.kwargs["expiration_days"] == 5  # noqa: PLR2004
    assert call_args.kwargs["s3_file_name"] == "custom.zip"

    mock_action.set_status.assert_called_once_with(ActionStatus.RUNNING)
    mock_action.set_final_state.assert_called_once_with(
        status=ActionStatus.SUCCESS,
        result="Download the RDS logs from the following URL: https://download.url. This link will expire in 5 days.",
        task_args=task_args,
    )

    assert (
        result
        == "Download the RDS logs from the following URL: https://download.url. This link will expire in 5 days."
    )


def test_external_resource_rds_logs_task_no_url_returned(
    mocker: MockerFixture, mock_action: Mock, er: ExternalResource
) -> None:
    mocker.patch(
        "automated_actions.celery.external_resource._rds_logs.get_external_resource",
        return_value=er,
    )
    mocker.patch(
        "automated_actions.celery.external_resource._rds_logs.get_aws_credentials",
        return_value=AWSStaticCredentials(
            access_key_id="test-access-key",
            secret_access_key="test-secret-key",  # noqa: S106
            region="us-west-2",
        ),
    )
    mock_settings = mocker.patch(
        "automated_actions.celery.external_resource._rds_logs.settings"
    )
    mock_settings.external_resource_rds_logs.access_key_id = "log-access-key"
    mock_settings.external_resource_rds_logs.secret_access_key = "log-secret-key"  # noqa: S105
    mock_settings.external_resource_rds_logs.region = "us-east-1"
    mock_settings.external_resource_rds_logs.s3_url = "https://s3.amazonaws.com"
    mock_settings.external_resource_rds_logs.bucket = "log-bucket"
    mock_settings.external_resource_rds_logs.prefix = "rds-logs"

    mock_rds_logs_run = mocker.patch.object(
        ExternalResourceRDSLogs, "run", return_value=""
    )

    action_id = str(uuid.uuid4())
    task_args = {
        "account": "test-account",
        "identifier": "test-identifier",
        "expiration_days": 7,
    }

    result = (
        external_resource_rds_logs.signature(
            kwargs={**task_args, "action": mock_action},
            task_id=action_id,
        )
        .apply()
        .result
    )

    mock_rds_logs_run.assert_called_once()
    mock_action.set_status.assert_called_once_with(ActionStatus.RUNNING)
    mock_action.set_final_state.assert_called_once_with(
        status=ActionStatus.SUCCESS,
        result="No logs found or no logs available for download.",
        task_args=task_args,
    )

    assert result == "No logs found or no logs available for download."


def test_external_resource_rds_logs_task_failure(
    mocker: MockerFixture, mock_action: Mock, er: ExternalResource
) -> None:
    mocker.patch(
        "automated_actions.celery.external_resource._rds_logs.get_external_resource",
        return_value=er,
    )
    mocker.patch(
        "automated_actions.celery.external_resource._rds_logs.get_aws_credentials",
        return_value=AWSStaticCredentials(
            access_key_id="test-access-key",
            secret_access_key="test-secret-key",  # noqa: S106
            region="us-west-2",
        ),
    )
    mock_settings = mocker.patch(
        "automated_actions.celery.external_resource._rds_logs.settings"
    )
    mock_settings.external_resource_rds_logs.access_key_id = "log-access-key"
    mock_settings.external_resource_rds_logs.secret_access_key = "log-secret-key"  # noqa: S105
    mock_settings.external_resource_rds_logs.region = "us-east-1"
    mock_settings.external_resource_rds_logs.s3_url = "https://s3.amazonaws.com"
    mock_settings.external_resource_rds_logs.bucket = "log-bucket"
    mock_settings.external_resource_rds_logs.prefix = "rds-logs"

    mock_rds_logs_run = mocker.patch.object(
        ExternalResourceRDSLogs,
        "run",
        side_effect=Exception("RDS logs retrieval failed!"),
    )

    action_id = str(uuid.uuid4())
    task_args = {
        "account": "test-account",
        "identifier": "test-identifier",
        "expiration_days": 3,
    }

    external_resource_rds_logs.signature(
        kwargs={**task_args, "action": mock_action},
        task_id=action_id,
    ).apply()

    mock_rds_logs_run.assert_called_once()
    mock_action.set_status.assert_called_once_with(ActionStatus.RUNNING)
    mock_action.set_final_state.assert_called_once_with(
        status=ActionStatus.FAILURE,
        result="RDS logs retrieval failed!",
        task_args=task_args,
    )
