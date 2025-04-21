from typing import Any

from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport


class GQLClient:
    def __init__(self, url: str, retries: int = 3, token: str | None = None) -> None:
        req_headers = None
        if token:
            req_headers = {"Authorization": token}

        transport = RequestsHTTPTransport(url=url, retries=retries, headers=req_headers)
        self.client = Client(transport=transport)

    def query(self, query: str, variables: dict | None = None) -> dict[str, Any] | None:
        result = self.client.execute(
            gql(query), variables, get_execution_result=True
        ).formatted

        if "data" in result:
            return result["data"]

        return None
