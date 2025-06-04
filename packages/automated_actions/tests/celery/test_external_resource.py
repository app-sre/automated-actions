import uuid
from unittest.mock import Mock

import pytest
from automated_actions_utils.aws_api import AWSApi, AWSStaticCredentials
from automated_actions_utils.external_resource import (
    AwsAccount,
    ExternalResource,
    VaultSecret,
)
from pytest_mock import MockerFixture

from automated_actions.celery.external_resource.tasks import (
    ExternalResourceRDSReboot,
    external_resource_rds_reboot,
)
from automated_actions.db.models import Action, ActionStatus


@pytest.fixture
def mock_aws(mocker: MockerFixture) -> Mock:
    return mocker.Mock(spec=AWSApi)


@pytest.fixture
def mock_action(mocker: MockerFixture) -> Mock:
    return mocker.Mock(spec=Action)


@pytest.fixture
def rds() -> ExternalResource:
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
    )


@pytest.mark.parametrize("force_failover", [True, False])
def test_external_resource_rds_reboot_run(
    mock_aws: Mock, rds: ExternalResource, *, force_failover: bool
) -> None:
    automated_action = ExternalResourceRDSReboot(aws_api=mock_aws, rds=rds)

    automated_action.run(force_failover=force_failover)

    mock_aws.reboot_rds_instance.assert_called_once_with(
        identifier=rds.identifier, force_failover=force_failover
    )


def test_external_resource_rds_reboot_task(
    mocker: MockerFixture, mock_action: Mock, rds: ExternalResource
) -> None:
    mocker.patch(
        "automated_actions.celery.external_resource.tasks.get_external_resource",
        return_value=rds,
    )
    mocker.patch(
        "automated_actions.celery.external_resource.tasks.get_aws_credentials",
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
    mocker: MockerFixture, mock_action: Mock, rds: ExternalResource
) -> None:
    mocker.patch(
        "automated_actions.celery.external_resource.tasks.get_external_resource",
        return_value=rds,
    )
    mocker.patch(
        "automated_actions.celery.external_resource.tasks.get_aws_credentials",
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
