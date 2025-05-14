from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.action_schema_out import ActionSchemaOut
from ...models.http_validation_error import HTTPValidationError
from ...types import Response


def _get_kwargs(
    action_id: str,
) -> dict[str, Any]:
    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": f"/api/v1/actions/{action_id}",
    }

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
    action_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[ActionSchemaOut | HTTPValidationError]:
    """Action Cancel

     Cancel an action.

    Args:
        action_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ActionSchemaOut, HTTPValidationError]]
    """

    kwargs = _get_kwargs(
        action_id=action_id,
    )

    with client as _client:
        response = _client.request(
            **kwargs,
        )

    return _build_response(client=client, response=response)


def sync(
    action_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> ActionSchemaOut | HTTPValidationError | None:
    """Action Cancel

     Cancel an action.

    Args:
        action_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ActionSchemaOut, HTTPValidationError]
    """

    return sync_detailed(
        action_id=action_id,
        client=client,
    ).parsed


async def asyncio_detailed(
    action_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[ActionSchemaOut | HTTPValidationError]:
    """Action Cancel

     Cancel an action.

    Args:
        action_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[ActionSchemaOut, HTTPValidationError]]
    """

    kwargs = _get_kwargs(
        action_id=action_id,
    )

    async with client as _client:
        response = await _client.request(
            **kwargs,
        )

    return _build_response(client=client, response=response)


async def asyncio(
    action_id: str,
    *,
    client: AuthenticatedClient | Client,
) -> ActionSchemaOut | HTTPValidationError | None:
    """Action Cancel

     Cancel an action.

    Args:
        action_id (str):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[ActionSchemaOut, HTTPValidationError]
    """

    return (
        await asyncio_detailed(
            action_id=action_id,
            client=client,
        )
    ).parsed


from typing import Annotated

import typer

app = typer.Typer()


@app.command(help="Cancel an action.")
def action_cancel(
    ctx: typer.Context,
    action_id: Annotated[str, typer.Option(help="", show_default=False)],
) -> None:
    result = sync(action_id=action_id, client=ctx.obj["client"])
    if "formatter" in ctx.obj and result:
        output: Any = result
        if isinstance(result, list):
            output = [
                item.to_dict() if hasattr(item, "to_dict") else item for item in result
            ]
        elif hasattr(result, "to_dict"):
            output = result.to_dict()
        ctx.obj["formatter"](output)
