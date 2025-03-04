from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.task_schema_out import TaskSchemaOut
from ...types import Response


def _get_kwargs(
    pk: str,
) -> dict[str, Any]:
    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": f"/api/v1/tasks/{pk}",
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> HTTPValidationError | TaskSchemaOut | None:
    if response.status_code == 200:
        response_200 = TaskSchemaOut.from_dict(response.json())

        return response_200
    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[HTTPValidationError | TaskSchemaOut]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    pk: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[HTTPValidationError | TaskSchemaOut]:
    """Task Detail

     Retrieve an task.

    Args:
        pk (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, TaskSchemaOut]]
    """

    kwargs = _get_kwargs(
        pk=pk,
    )

    with client as _client:
        response = _client.request(
            **kwargs,
        )

    return _build_response(client=client, response=response)


def sync(
    pk: str,
    *,
    client: AuthenticatedClient | Client,
) -> HTTPValidationError | TaskSchemaOut | None:
    """Task Detail

     Retrieve an task.

    Args:
        pk (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, TaskSchemaOut]
    """

    return sync_detailed(
        pk=pk,
        client=client,
    ).parsed


async def asyncio_detailed(
    pk: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[HTTPValidationError | TaskSchemaOut]:
    """Task Detail

     Retrieve an task.

    Args:
        pk (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, TaskSchemaOut]]
    """

    kwargs = _get_kwargs(
        pk=pk,
    )

    async with client as _client:
        response = await _client.request(
            **kwargs,
        )

    return _build_response(client=client, response=response)


async def asyncio(
    pk: str,
    *,
    client: AuthenticatedClient | Client,
) -> HTTPValidationError | TaskSchemaOut | None:
    """Task Detail

     Retrieve an task.

    Args:
        pk (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, TaskSchemaOut]
    """

    return (
        await asyncio_detailed(
            pk=pk,
            client=client,
        )
    ).parsed


from typing import Annotated

import typer
from rich import print as rich_print

app = typer.Typer()


@app.command(help="Retrieve an task.")
def task_detail(
    ctx: typer.Context,
    pk: Annotated[
        str,
        typer.Option(
            help="""
            
        """
        ),
    ],
) -> None:
    rich_print(sync(pk=pk, client=ctx.obj["client"]))
