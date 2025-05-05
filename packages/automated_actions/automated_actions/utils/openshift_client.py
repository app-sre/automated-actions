from datetime import UTC, datetime
from enum import StrEnum

from kubernetes.client import (
    ApiClient,
    Configuration,
)
from kubernetes.dynamic.exceptions import NotFoundError
from kubernetes.dynamic.resource import ResourceInstance
from openshift.dynamic import DynamicClient

SUPPORTED_POD_OWNERS = {"ReplicaSet", "StatefulSet"}


class OpenshiftClientResourceNotFoundError(Exception):
    pass


class OpenshiftClientPodDeletionNotSupportedError(Exception):
    pass


class RollingRestartResource(StrEnum):
    deployment = "Deployment"
    statefulset = "StatefulSet"
    daemonset = "DaemonSet"


class OpenshiftClient:
    def __init__(self, server_url: str, token: str, retries: int = 5) -> None:
        configuration = Configuration(
            host=server_url, api_key={"authorization": f"Bearer {token}"}
        )
        configuration.retries = retries
        self.dyn_client = DynamicClient(ApiClient(configuration=configuration))

    # https://kubernetes.io/docs/reference/labels-annotations-taints/#kubectl-k8s-io-restart-at
    def rolling_restart(
        self, kind: RollingRestartResource, name: str, namespace: str
    ) -> ResourceInstance:
        api = self.dyn_client.resources.get(api_version="apps/v1", kind=str(kind))

        patch_body = {
            "spec": {
                "template": {
                    "metadata": {
                        "annotations": {
                            "kubectl.kubernetes.io/restartedAt": datetime.now(
                                UTC
                            ).isoformat()
                        }
                    }
                }
            }
        }

        try:
            res = api.patch(namespace=namespace, name=name, body=patch_body)
        except NotFoundError as err:
            raise OpenshiftClientResourceNotFoundError(
                f"{kind} {name} does not exist in namespace {namespace}"
            ) from err

        return res

    def delete_pod_from_replicated_resource(
        self, name: str, namespace: str
    ) -> ResourceInstance:
        api = self.dyn_client.resources.get(api_version="v1", kind="Pod")

        try:
            pod = api.get(name=name, namespace=namespace)
        except NotFoundError as err:
            raise OpenshiftClientResourceNotFoundError(
                f"Pod {name} does not exist in namespace {namespace}"
            ) from err

        has_pod_proper_owner = False
        if owner_references := pod["metadata"].get("ownerReferences"):
            for reference in owner_references:
                if reference.get("kind") in SUPPORTED_POD_OWNERS:
                    has_pod_proper_owner = True
                    break

        if not has_pod_proper_owner:
            raise OpenshiftClientPodDeletionNotSupportedError(
                f"Pod '{name}' in namespace '{namespace}' cannot be deleted as "
                f"it does not belong to a {', '.join(sorted(SUPPORTED_POD_OWNERS))}."
            )

        return api.delete(name=name, namespace=namespace)
