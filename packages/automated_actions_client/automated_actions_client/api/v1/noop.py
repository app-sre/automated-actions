from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.action_schema_out import ActionSchemaOut
from ...models.http_validation_error import HTTPValidationError
from ...models.noop_param import NoopParam
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    body: NoopParam,
    labels: None | Unset | list[str] = UNSET,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    params: dict[str, Any] = {}

    json_labels: None | Unset | list[str]
    if isinstance(labels, Unset):
        json_labels = UNSET
    elif isinstance(labels, list):
        json_labels = labels

    else:
        json_labels = labels
    params["labels"] = json_labels

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/v1/noop",
        "params": params,
    }

    _body = body.to_dict()

    _kwargs["json"] = _body
    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ActionSchemaOut | HTTPValidationError | None:
    if response.status_code == 202:
        response_202 = ActionSchemaOut.from_dict(response.json())

        return response_202
    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())

        return response_422
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[ActionSchemaOut | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: NoopParam,
    labels: None | Unset | list[str] = UNSET,
) -> Response[ActionSchemaOut | HTTPValidationError]:
    """Run Noop

     Run a noop action

    Args:
        labels (Union[None, Unset, list[str]]):
        body (NoopParam):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ActionSchemaOut, HTTPValidationError]]
    """

    kwargs = _get_kwargs(
        body=body,
        labels=labels,
    )

    with client as _client:
        response = _client.request(
            **kwargs,
        )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    body: NoopParam,
    labels: None | Unset | list[str] = UNSET,
) -> ActionSchemaOut | HTTPValidationError | None:
    """Run Noop

     Run a noop action

    Args:
        labels (Union[None, Unset, list[str]]):
        body (NoopParam):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ActionSchemaOut, HTTPValidationError]
    """

    return sync_detailed(
        client=client,
        body=body,
        labels=labels,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: NoopParam,
    labels: None | Unset | list[str] = UNSET,
) -> Response[ActionSchemaOut | HTTPValidationError]:
    """Run Noop

     Run a noop action

    Args:
        labels (Union[None, Unset, list[str]]):
        body (NoopParam):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ActionSchemaOut, HTTPValidationError]]
    """

    kwargs = _get_kwargs(
        body=body,
        labels=labels,
    )

    async with client as _client:
        response = await _client.request(
            **kwargs,
        )

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: NoopParam,
    labels: None | Unset | list[str] = UNSET,
) -> ActionSchemaOut | HTTPValidationError | None:
    """Run Noop

     Run a noop action

    Args:
        labels (Union[None, Unset, list[str]]):
        body (NoopParam):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ActionSchemaOut, HTTPValidationError]
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
            labels=labels,
        )
    ).parsed


from typing import Annotated

import typer

app = typer.Typer()


@app.command(help="Run a noop action")
def noop(
    ctx: typer.Context,
    alias: Annotated[str, typer.Option(help="")],
    description: Annotated[str, typer.Option(help="")] = "no description",
    labels: Annotated[None | list[str], typer.Option(help="")] = None,
) -> None:
    result = sync(
        labels=labels,
        body=NoopParam(
            alias=alias,
            description=description,
        ),
        client=ctx.obj["client"],
    )
    if "console" in ctx.obj:
        ctx.obj["console"].print(result)
