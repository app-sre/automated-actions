import re
from collections.abc import Callable

import pytest
import requests
from automated_actions_client import AuthenticatedClient
from automated_actions_client.api.actions import external_resource_rds_logs
from automated_actions_client.models.action_schema_out import ActionSchemaOut
from automated_actions_client.models.action_status import ActionStatus
from automated_actions_utils.aws_api import AWSApi, get_aws_credentials
from automated_actions_utils.external_resource import (
    ExternalResourceProvider,
    get_external_resource,
)

from tests.conftest import Config


@pytest.fixture
def aws_api(config: Config) -> AWSApi:
    rds = get_external_resource(
        account=config.external_resource_rds_logs.account,
        identifier=config.external_resource_rds_logs.identifier,
        provider=ExternalResourceProvider.RDS,
    )
    credentials = get_aws_credentials(
        vault_secret=rds.account.automation_token, region=rds.account.region
    )
    return AWSApi(credentials=credentials, region=rds.region)


@pytest.fixture(scope="session")
def action_id(aa_client: AuthenticatedClient, config: Config) -> str:
    """Trigger an RDS logs action and return the action id.

    We use a pytest fixture with session scope to avoid multiple actions being triggered
    in case of retry via the flaky mark
    """
    action = external_resource_rds_logs.sync(
        account=config.external_resource_rds_logs.account,
        identifier=config.external_resource_rds_logs.identifier,
        client=aa_client,
        expiration_days=3,
        s3_file_name=config.external_resource_rds_logs.s3_file_name,
    )
    assert isinstance(action, ActionSchemaOut)
    assert action.status == ActionStatus.PENDING
    assert not action.result
    return action.action_id


def test_external_resource_rds_logs(
    action_id: str,
    wait_for_action_success: Callable,
    aws_api: AWSApi,
    config: Config,
) -> None:
    """Test the RDS logs action retrieves logs and uploads them to S3."""
    # verify that RDS logs exist for the instance before running the action
    log_files = aws_api.list_rds_logs(config.external_resource_rds_logs.identifier)
    assert log_files, (
        f"No log files found for RDS instance {config.external_resource_rds_logs.identifier}"
    )

    # wait for the action to complete and assert it was successful
    action_result = wait_for_action_success(
        action_id=action_id,
        retries=config.external_resource_rds_logs.retries,
        sleep_time=config.external_resource_rds_logs.sleep_time,
    )

    # verify the action result contains a download URL
    assert "Download the RDS logs from the following URL:" in action_result.result
    assert "This link will expire in" in action_result.result

    # extract download URL and verify it's accessible via HTTP HEAD
    url_match = re.search(r"URL: (https?://[^\s]+)", action_result.result)
    assert url_match, "No download URL found in action result"
    download_url = url_match.group(1).rstrip(".")

    # verify the zip file is accessible without downloading it
    response = requests.head(download_url, timeout=30)
    assert response.status_code == requests.codes.OK, (
        f"Download URL is not accessible: {response.status_code}"
    )
