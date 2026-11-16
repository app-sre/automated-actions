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
    token_ref = (
        next(
            (
                entry.secret
                for entry in cluster.automation_tokens or []
                if entry.active and not entry.delete and entry.secret is not None
            ),
            None,
        )
        or cluster.automation_token
    )

    if token_ref is None:
        raise MissingAppInterfaceClusterAutomationTokenError(
            f"No automationToken for cluster {cluster_name}"
        )

    token = vault_client.read_secret(
        path=token_ref.path,
        version=str(token_ref.version),
    ).get(token_ref.field)

    if not token:
        raise SecretFieldNotFoundError(
            f"{token_ref.field} not found in secret {token_ref.path}"
        )

    return ClusterConnectionData(url=cluster.server_url, token=token)
