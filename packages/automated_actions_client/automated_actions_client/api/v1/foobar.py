from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...types import UNSET, Response, Unset


def _get_kwargs(
    pk: str,
    *,
    q: None | Unset | str = UNSET,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    json_q: None | Unset | str
    if isinstance(q, Unset):
        json_q = UNSET
    else:
        json_q = q
    params["q"] = json_q

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": f"/api/v1/foobar/{pk}",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Any | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = response.json()
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
) -> Response[Any | HTTPValidationError]:
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
    q: None | Unset | str = UNSET,
) -> Response[Any | HTTPValidationError]:
    """Run Foobar

     Run a foobar action

    Args:
        pk (str):
        q (Union[None, Unset, str]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, HTTPValidationError]]
    """

    kwargs = _get_kwargs(
        pk=pk,
        q=q,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    pk: str,
    *,
    client: AuthenticatedClient | Client,
    q: None | Unset | str = UNSET,
) -> Any | HTTPValidationError | None:
    """Run Foobar

     Run a foobar action

    Args:
        pk (str):
        q (Union[None, Unset, str]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, HTTPValidationError]
    """

    return sync_detailed(
        pk=pk,
        client=client,
        q=q,
    ).parsed


async def asyncio_detailed(
    pk: str,
    *,
    client: AuthenticatedClient | Client,
    q: None | Unset | str = UNSET,
) -> Response[Any | HTTPValidationError]:
    """Run Foobar

     Run a foobar action

    Args:
        pk (str):
        q (Union[None, Unset, str]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[Any, HTTPValidationError]]
    """

    kwargs = _get_kwargs(
        pk=pk,
        q=q,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    pk: str,
    *,
    client: AuthenticatedClient | Client,
    q: None | Unset | str = UNSET,
) -> Any | HTTPValidationError | None:
    """Run Foobar

     Run a foobar action

    Args:
        pk (str):
        q (Union[None, Unset, str]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[Any, HTTPValidationError]
    """

    return (
        await asyncio_detailed(
            pk=pk,
            client=client,
            q=q,
        )
    ).parsed


from typing import Annotated

import typer
from rich import print as rich_print

app = typer.Typer()


@app.command(help="Run a foobar action")
def foobar(
    ctx: typer.Context,
    pk: Annotated[
        str,
        typer.Option(
            help="""
            
        """
        ),
    ],
    q: Annotated[
        None | str,
        typer.Option(
            help="""
        
    """
        ),
    ] = None,
) -> None:
    rich_print(sync(pk=pk, q=q, client=ctx.obj["client"]))
