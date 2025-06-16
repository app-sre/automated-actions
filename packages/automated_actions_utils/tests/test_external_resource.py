from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from automated_actions_utils.external_resource import (
    AwsAccount,
    ExternalResource,
    ExternalResourceAppInterfaceError,
    ExternalResourceProvider,
    VaultSecret,
    get_external_resource,
)


@pytest.fixture(autouse=True)
def mock_gql_client(mocker: MockerFixture) -> MagicMock:
    """Mocks the GQLClient and its query method for testing."""
    m = mocker.patch("automated_actions_utils.external_resource.GQLClient")
    m.return_value.query.return_value = {
        "namespaces": [
            {
                "name": "test-namespace",
                "delete": None,
                "externalResources": [
                    {
                        "provider": "aws",
                        "provisioner": {
                            "name": "test-account",
                            "automationToken": {
                                "path": "wherever/test-account",
                                "field": "all",
                                "version": None,
                                "format": None,
                            },
                            "resourcesDefaultRegion": "us-east-1",
                        },
                        "resources": [
                            {
                                "provider": "rds",
                                "identifier": "test-rds",
                                "region": None,
                                "delete": None,
                                "output_resource_name": "test-rds-output-resource-name",
                            },
                        ],
                    }
                ],
                "cluster": {
                    "name": "test-cluster",
                },
            },
            {
                "name": "another-namespace",
                "delete": None,
                "externalResources": [
                    {
                        "provider": "aws",
                        "provisioner": {
                            "name": "test-account",
                            "automationToken": {
                                "path": "wherever/test-account",
                                "field": "all",
                                "version": None,
                                "format": None,
                            },
                            "resourcesDefaultRegion": "us-east-1",
                        },
                        "resources": [
                            {
                                "provider": "elasticache",
                                "identifier": "test-elasticache",
                                "output_resource_name": "test-elasticache-output-resource-name",
                            },
                        ],
                    }
                ],
                "cluster": {
                    "name": "test-cluster",
                },
            },
        ]
    }
    return m


def test_get_external_resource_success(mock_gql_client: MagicMock) -> None:
    """Tests successful retrieval of an external resource."""
    result = get_external_resource(
        account="test-account",
        identifier="test-rds",
        provider=ExternalResourceProvider.RDS,
    )
    assert result == ExternalResource(
        identifier="test-rds",
        region=None,
        account=AwsAccount(
            name="test-account",
            automation_token=VaultSecret(
                path="wherever/test-account", field="all", version=None, q_format=None
            ),
            region="us-east-1",
        ),
        cluster="test-cluster",
        namespace="test-namespace",
        output_resource_name="test-rds-output-resource-name",
    )
    mock_gql_client.return_value.query.assert_called_once()


def test_get_external_resource_success_elasticache(mock_gql_client: MagicMock) -> None:
    """Tests successful retrieval of an external resource."""
    result = get_external_resource(
        account="test-account",
        identifier="test-elasticache",
        provider=ExternalResourceProvider.ELASTICACHE,
    )
    assert result == ExternalResource(
        identifier="test-elasticache",
        region=None,
        account=AwsAccount(
            name="test-account",
            automation_token=VaultSecret(
                path="wherever/test-account", field="all", version=None, q_format=None
            ),
            region="us-east-1",
        ),
        cluster="test-cluster",
        namespace="another-namespace",
        output_resource_name="test-elasticache-output-resource-name",
    )
    mock_gql_client.return_value.query.assert_called_once()


def test_get_external_resource_missing(mock_gql_client: MagicMock) -> None:
    """Tests retrieval of a non-existent external resource."""
    with pytest.raises(ExternalResourceAppInterfaceError):
        get_external_resource(
            account="test-account",
            identifier="does-not-exist",
            provider=ExternalResourceProvider.RDS,
        )

    mock_gql_client.return_value.query.assert_called_once()


def test_get_external_resource_no_namespaces(mock_gql_client: MagicMock) -> None:
    """Tests retrieval when no namespaces are returned from app-interface."""
    mock_gql_client.return_value.query.return_value = {"namespaces": []}
    with pytest.raises(ExternalResourceAppInterfaceError):
        get_external_resource(
            account="test-account",
            identifier="does-not-exist",
            provider=ExternalResourceProvider.RDS,
        )

    mock_gql_client.return_value.query.assert_called_once()
