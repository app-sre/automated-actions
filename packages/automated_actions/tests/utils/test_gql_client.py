import pytest
from requests_mock import Mocker

from automated_actions.utils.gql_client import GQLClient


@pytest.fixture
def gql(requests_mock: Mocker) -> GQLClient:
    requests_mock.post(
        "http://example.com/graphql",
        json={"data": {"test": "test"}},
    )
    return GQLClient(url="http://example.com/graphql", token="test_token")  # noqa: S106


def test_gql_client_query(gql: GQLClient) -> None:
    query = """
    query {
        test
    }
    """
    result = gql.query(query)
    assert result == {"test": "test"}
