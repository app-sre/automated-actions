from automated_actions.celery.app import app
from automated_actions.celery.automated_action_task import AutomatedActionTask
from automated_actions.db.models import Action
from automated_actions.utils.cluster_connection import get_cluster_connection_data
from automated_actions.utils.openshift_client import (
    OpenshiftClient,
    RollingRestartResource,
)


class OpenshiftResourceKindNotSupportedError(Exception):
    pass


class OpenshiftWorkloadRestart:
    def __init__(
        self, oc: OpenshiftClient, namespace: str, kind: str, name: str
    ) -> None:
        self.oc = oc
        self.namespace = namespace
        self.name = name

        if kind not in RollingRestartResource and kind != "Pod":
            raise OpenshiftResourceKindNotSupportedError(f"kind '{kind}' not supported")

        self.kind = kind

    def run(self) -> None:
        if self.kind in RollingRestartResource:
            self.oc.rolling_restart(
                kind=RollingRestartResource(self.kind),
                name=self.name,
                namespace=self.namespace,
            )
        else:
            self.oc.delete_pod_from_replicated_resource(
                name=self.name, namespace=self.namespace
            )


@app.task(base=AutomatedActionTask)
def openshift_workload_restart(
    cluster: str,
    namespace: str,
    kind: str,
    name: str,
    action: Action,  # noqa: ARG001
) -> None:
    cluster_connection = get_cluster_connection_data(cluster)
    oc = OpenshiftClient(
        server_url=cluster_connection.url, token=cluster_connection.token
    )
    OpenshiftWorkloadRestart(oc, namespace, kind, name).run()
