import logging

from pydantic import BaseModel

from automated_actions.config import settings
from automated_actions.gql_definitions.tasks.external_resources_namespaces import (
    NamespaceTerraformProviderResourceAWSV1,
    NamespaceTerraformResourceRDSV1,
)
from automated_actions.gql_definitions.tasks.external_resources_namespaces import (
    query as external_resources_namespaces,
)
from automated_actions.utils.gql_client import GQLClient

log = logging.getLogger(__name__)


class ExternalResourceAppInterfaceError(Exception):
    """Exception raised when an external resource is not found in app-interface."""


class VaultSecret(BaseModel):
    path: str
    field: str
    version: int | None
    q_format: str | None


class AwsAccount(BaseModel):
    name: str
    automation_token: VaultSecret
    region: str


class ExternalResource(BaseModel):
    identifier: str
    region: str | None
    account: AwsAccount


def get_external_resource(account: str, identifier: str) -> ExternalResource:
    """Get external resource information from app-interface."""
    gql_client = GQLClient(
        url=settings.qontract_server_url, token=settings.qontract_server_token
    )
    namespaces = external_resources_namespaces(gql_client.query).namespaces

    if not namespaces:
        raise ExternalResourceAppInterfaceError(
            "No external resources found in app-interface."
        )

    for namespace in namespaces:
        for er in namespace.external_resources or []:
            if not isinstance(er, NamespaceTerraformProviderResourceAWSV1):
                continue
            if er.provisioner.name == account:
                for r in er.resources:
                    if r.identifier != identifier:
                        continue
                    if isinstance(r, NamespaceTerraformResourceRDSV1):
                        return ExternalResource(
                            identifier=identifier,
                            region=r.region,
                            account=AwsAccount(
                                name=account,
                                automation_token=VaultSecret(
                                    path=er.provisioner.automation_token.path,
                                    field=er.provisioner.automation_token.field,
                                    version=er.provisioner.automation_token.version,
                                    q_format=er.provisioner.automation_token.q_format,
                                ),
                                region=er.provisioner.resources_default_region,
                            ),
                        )

    raise ExternalResourceAppInterfaceError(
        f"External resource {identifier} not found in account {account}."
    )
