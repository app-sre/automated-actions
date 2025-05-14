from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.action_schema_out import ActionSchemaOut
from ...models.action_status import ActionStatus
from ...models.http_validation_error import HTTPValidationError
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    status: ActionStatus | None | Unset = UNSET,
    action_user: None | Unset | str = UNSET,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    json_status: None | Unset | str
    if isinstance(status, Unset):
        json_status = UNSET
    elif isinstance(status, ActionStatus):
        json_status = status.value
    else:
        json_status = status
    params["status"] = json_status

    json_action_user: None | Unset | str
    if isinstance(action_user, Unset):
        json_action_user = UNSET
    else:
        json_action_user = action_user
    params["action_user"] = json_action_user

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/v1/actions",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> HTTPValidationError | list["ActionSchemaOut"] | None:
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in _response_200:
            response_200_item = ActionSchemaOut.from_dict(response_200_item_data)

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
) -> Response[HTTPValidationError | list["ActionSchemaOut"]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    status: ActionStatus | None | Unset = UNSET,
    action_user: None | Unset | str = UNSET,
) -> Response[HTTPValidationError | list["ActionSchemaOut"]]:
    """Action List

     List actions.

    Args:
        status (Union[ActionStatus, None, Unset]): Filter actions by their status
        action_user (Union[None, Unset, str]): Filter actions by username instead of the current
            authenticated user

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, list['ActionSchemaOut']]]
    """

    kwargs = _get_kwargs(
        status=status,
        action_user=action_user,
    )

    with client as _client:
        response = _client.request(
            **kwargs,
        )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient | Client,
    status: ActionStatus | None | Unset = UNSET,
    action_user: None | Unset | str = UNSET,
) -> HTTPValidationError | list["ActionSchemaOut"] | None:
    """Action List

     List actions.

    Args:
        status (Union[ActionStatus, None, Unset]): Filter actions by their status
        action_user (Union[None, Unset, str]): Filter actions by username instead of the current
            authenticated user

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, list['ActionSchemaOut']]
    """

    return sync_detailed(
        client=client,
        status=status,
        action_user=action_user,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    status: ActionStatus | None | Unset = UNSET,
    action_user: None | Unset | str = UNSET,
) -> Response[HTTPValidationError | list["ActionSchemaOut"]]:
    """Action List

     List actions.

    Args:
        status (Union[ActionStatus, None, Unset]): Filter actions by their status
        action_user (Union[None, Unset, str]): Filter actions by username instead of the current
            authenticated user

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, list['ActionSchemaOut']]]
    """

    kwargs = _get_kwargs(
        status=status,
        action_user=action_user,
    )

    async with client as _client:
        response = await _client.request(
            **kwargs,
        )

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    status: ActionStatus | None | Unset = UNSET,
    action_user: None | Unset | str = UNSET,
) -> HTTPValidationError | list["ActionSchemaOut"] | None:
    """Action List

     List actions.

    Args:
        status (Union[ActionStatus, None, Unset]): Filter actions by their status
        action_user (Union[None, Unset, str]): Filter actions by username instead of the current
            authenticated user

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, list['ActionSchemaOut']]
    """

    return (
        await asyncio_detailed(
            client=client,
            status=status,
            action_user=action_user,
        )
    ).parsed


from typing import Annotated

import typer

app = typer.Typer()


@app.command(help="List actions.")
def action_list(
    ctx: typer.Context,
    status: Annotated[
        ActionStatus | None, typer.Option(help="Filter actions by their status")
    ] = None,
    action_user: Annotated[
        None | str,
        typer.Option(
            help="Filter actions by username instead of the current authenticated user"
        ),
    ] = None,
) -> None:
    result = sync(status=status, action_user=action_user, client=ctx.obj["client"])
    if "formatter" in ctx.obj and result:
        output: Any = result
        if isinstance(result, list):
            output = [
                item.to_dict() if hasattr(item, "to_dict") else item for item in result
            ]
        elif hasattr(result, "to_dict"):
            output = result.to_dict()
        ctx.obj["formatter"](output)
