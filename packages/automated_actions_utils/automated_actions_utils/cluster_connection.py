import logging
from dataclasses import dataclass

from automated_actions.config import Settings

from automated_actions_utils.gql_client import GQLClient
from automated_actions_utils.gql_definitions.tasks.clusters import (
    query as clusters_query,
)
from automated_actions_utils.vault_client import SecretFieldNotFoundError, VaultClient

log = logging.getLogger(__name__)


class ClusterMissingInAppInterfaceError(Exception):
    pass


class MissingAppInterfaceClusterAutomationTokenError(Exception):
    pass


@dataclass
class ClusterConnectionData:
    url: str
    token: str


def get_cluster_connection_data(
    cluster_name: str, settings: Settings
) -> ClusterConnectionData:
    gql_client = GQLClient(
        url=settings.qontract_server_url, token=settings.qontract_server_token
    )
    cluster_data = clusters_query(
        gql_client.query, variables={"filter": {"name": cluster_name}}
    )

    if not cluster_data.cluster:
        raise ClusterMissingInAppInterfaceError(
            f"cluster '{cluster_name}' missing in app-interface"
        )

    vault_client = VaultClient(
        server_url=settings.vault_server_url,
        role_id=settings.vault_role_id,
        secret_id=settings.vault_secret_id,
        kube_auth_role=settings.vault_kube_auth_role,
        kube_auth_mount=settings.vault_kube_auth_mount,
    )

    cluster = cluster_data.cluster[0]

    if cluster.automation_token is None:
        raise MissingAppInterfaceClusterAutomationTokenError(
            f"No automationToken for cluster {cluster_name}"
        )

    token = vault_client.read_secret(
        path=cluster.automation_token.path,
        version=str(cluster.automation_token.version),
    ).get(cluster.automation_token.field)

    if not token:
        raise SecretFieldNotFoundError(
            f"{cluster.automation_token.field} not found in secret {cluster.automation_token.path}"
        )

    return ClusterConnectionData(url=cluster.server_url, token=token)
