from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.task_schema_out import TaskSchemaOut
from ...models.task_status import TaskStatus
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    status: None | TaskStatus | Unset = TaskStatus.RUNNING,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    json_status: None | Unset | str
    if isinstance(status, Unset):
        json_status = UNSET
    elif isinstance(status, TaskStatus):
        json_status = status.value
    else:
        json_status = status
    params["status"] = json_status

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/tasks",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> HTTPValidationError | list["TaskSchemaOut"] | None:
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in _response_200:
            response_200_item = TaskSchemaOut.from_dict(response_200_item_data)

            response_200.append(response_200_item)

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
) -> Response[HTTPValidationError | list["TaskSchemaOut"]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    status: None | TaskStatus | Unset = TaskStatus.RUNNING,
) -> Response[HTTPValidationError | list["TaskSchemaOut"]]:
    """Task List

     List all user tasks.

    Args:
        status (Union[None, TaskStatus, Unset]):  Default: TaskStatus.RUNNING.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, list['TaskSchemaOut']]]
    """

    kwargs = _get_kwargs(
        status=status,
    )

    with client as _client:
        response = _client.request(
            **kwargs,
        )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    status: None | TaskStatus | Unset = TaskStatus.RUNNING,
) -> HTTPValidationError | list["TaskSchemaOut"] | None:
    """Task List

     List all user tasks.

    Args:
        status (Union[None, TaskStatus, Unset]):  Default: TaskStatus.RUNNING.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, list['TaskSchemaOut']]
    """

    return sync_detailed(
        client=client,
        status=status,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    status: None | TaskStatus | Unset = TaskStatus.RUNNING,
) -> Response[HTTPValidationError | list["TaskSchemaOut"]]:
    """Task List

     List all user tasks.

    Args:
        status (Union[None, TaskStatus, Unset]):  Default: TaskStatus.RUNNING.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, list['TaskSchemaOut']]]
    """

    kwargs = _get_kwargs(
        status=status,
    )

    async with client as _client:
        response = await _client.request(
            **kwargs,
        )

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    status: None | TaskStatus | Unset = TaskStatus.RUNNING,
) -> HTTPValidationError | list["TaskSchemaOut"] | None:
    """Task List

     List all user tasks.

    Args:
        status (Union[None, TaskStatus, Unset]):  Default: TaskStatus.RUNNING.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, list['TaskSchemaOut']]
    """

    return (
        await asyncio_detailed(
            client=client,
            status=status,
        )
    ).parsed


from typing import Annotated

import typer

app = typer.Typer()


@app.command(help="List all user tasks.")
def task_list(
    ctx: typer.Context,
    status: Annotated[None | TaskStatus, typer.Option(help="")] = TaskStatus.RUNNING,
) -> None:
    result = sync(status=status, client=ctx.obj["client"])
    if "console" in ctx.obj:
        ctx.obj["console"].print(result)
