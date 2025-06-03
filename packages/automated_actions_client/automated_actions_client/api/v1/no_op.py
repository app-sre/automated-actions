from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.action_schema_out import ActionSchemaOut
from ...types import Response


def _get_kwargs() -> dict[str, Any]:
    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v1/no-op",
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ActionSchemaOut | None:
    if response.status_code == 202:
        response_202 = ActionSchemaOut.from_dict(response.json())

        return response_202
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[ActionSchemaOut]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[ActionSchemaOut]:
    """No Op

     Initiates a no-operation action.

    This action performs no actual operation but can be used for testing.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ActionSchemaOut]
    """

    kwargs = _get_kwargs()

    with client as _client:
        response = _client.request(
            **kwargs,
        )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
) -> ActionSchemaOut | None:
    """No Op

     Initiates a no-operation action.

    This action performs no actual operation but can be used for testing.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ActionSchemaOut
    """

    return sync_detailed(
        client=client,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
) -> Response[ActionSchemaOut]:
    """No Op

     Initiates a no-operation action.

    This action performs no actual operation but can be used for testing.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ActionSchemaOut]
    """

    kwargs = _get_kwargs()

    async with client as _client:
        response = await _client.request(
            **kwargs,
        )

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
) -> ActionSchemaOut | None:
    """No Op

     Initiates a no-operation action.

    This action performs no actual operation but can be used for testing.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ActionSchemaOut
    """

    return (
        await asyncio_detailed(
            client=client,
        )
    ).parsed


import typer

app = typer.Typer()


@app.command(
    help="""Initiates a no-operation action.

This action performs no actual operation but can be used for testing."""
)
def no_op(
    ctx: typer.Context,
) -> None:
    result = sync(client=ctx.obj["client"])
    if "formatter" in ctx.obj and result:
        output: Any = result
        if isinstance(result, list):
            output = [
                item.to_dict() if hasattr(item, "to_dict") else item for item in result
            ]
        elif hasattr(result, "to_dict"):
            output = result.to_dict()
        ctx.obj["formatter"](output)
