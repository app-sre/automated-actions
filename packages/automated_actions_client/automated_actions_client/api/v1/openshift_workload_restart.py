from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.http_validation_error import HTTPValidationError
from ...models.task_schema_out import TaskSchemaOut
from ...types import Response


def _get_kwargs(
    cluster: str,
    namespace: str,
    kind: str,
    name: str,
) -> dict[str, Any]:
    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": f"/api/v1/openshift/workload-restart/{cluster}/{namespace}/{kind}/{name}",
    }

    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> HTTPValidationError | TaskSchemaOut | None:
    if response.status_code == 202:
        response_202 = TaskSchemaOut.from_dict(response.json())

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
) -> Response[HTTPValidationError | TaskSchemaOut]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    cluster: str,
    namespace: str,
    kind: str,
    name: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[HTTPValidationError | TaskSchemaOut]:
    """Openshift Workload Restart

     Restart an OpenShift workload.

    Args:
        cluster (str): OpenShift cluster name
        namespace (str): OpenShift namespace
        kind (str): OpenShift workload kind. e.g. Deployment or Pod
        name (str): OpenShift workload name

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, TaskSchemaOut]]
    """

    kwargs = _get_kwargs(
        cluster=cluster,
        namespace=namespace,
        kind=kind,
        name=name,
    )

    with client as _client:
        response = _client.request(
            **kwargs,
        )

    return _build_response(client=client, response=response)


def sync(
    cluster: str,
    namespace: str,
    kind: str,
    name: str,
    *,
    client: AuthenticatedClient | Client,
) -> HTTPValidationError | TaskSchemaOut | None:
    """Openshift Workload Restart

     Restart an OpenShift workload.

    Args:
        cluster (str): OpenShift cluster name
        namespace (str): OpenShift namespace
        kind (str): OpenShift workload kind. e.g. Deployment or Pod
        name (str): OpenShift workload name

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, TaskSchemaOut]
    """

    return sync_detailed(
        cluster=cluster,
        namespace=namespace,
        kind=kind,
        name=name,
        client=client,
    ).parsed


async def asyncio_detailed(
    cluster: str,
    namespace: str,
    kind: str,
    name: str,
    *,
    client: AuthenticatedClient | Client,
) -> Response[HTTPValidationError | TaskSchemaOut]:
    """Openshift Workload Restart

     Restart an OpenShift workload.

    Args:
        cluster (str): OpenShift cluster name
        namespace (str): OpenShift namespace
        kind (str): OpenShift workload kind. e.g. Deployment or Pod
        name (str): OpenShift workload name

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union[HTTPValidationError, TaskSchemaOut]]
    """

    kwargs = _get_kwargs(
        cluster=cluster,
        namespace=namespace,
        kind=kind,
        name=name,
    )

    async with client as _client:
        response = await _client.request(
            **kwargs,
        )

    return _build_response(client=client, response=response)


async def asyncio(
    cluster: str,
    namespace: str,
    kind: str,
    name: str,
    *,
    client: AuthenticatedClient | Client,
) -> HTTPValidationError | TaskSchemaOut | None:
    """Openshift Workload Restart

     Restart an OpenShift workload.

    Args:
        cluster (str): OpenShift cluster name
        namespace (str): OpenShift namespace
        kind (str): OpenShift workload kind. e.g. Deployment or Pod
        name (str): OpenShift workload name

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union[HTTPValidationError, TaskSchemaOut]
    """

    return (
        await asyncio_detailed(
            cluster=cluster,
            namespace=namespace,
            kind=kind,
            name=name,
            client=client,
        )
    ).parsed


from typing import Annotated

import typer

app = typer.Typer()


@app.command(help="Restart an OpenShift workload.")
def openshift_workload_restart(
    ctx: typer.Context,
    cluster: Annotated[
        str, typer.Option(help="OpenShift cluster name", show_default=False)
    ],
    namespace: Annotated[
        str, typer.Option(help="OpenShift namespace", show_default=False)
    ],
    kind: Annotated[
        str,
        typer.Option(
            help="OpenShift workload kind. e.g. Deployment or Pod", show_default=False
        ),
    ],
    name: Annotated[
        str, typer.Option(help="OpenShift workload name", show_default=False)
    ],
) -> None:
    result = sync(
        cluster=cluster,
        namespace=namespace,
        kind=kind,
        name=name,
        client=ctx.obj["client"],
    )
    if "console" in ctx.obj:
        ctx.obj["console"].print(result)
