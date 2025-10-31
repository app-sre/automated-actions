import logging

from automated_actions_utils.cluster_connection import get_cluster_connection_data
from automated_actions_utils.openshift_client import (
    OpenshiftClient,
    RollingRestartResource,
)

from automated_actions.celery.app import app
from automated_actions.celery.automated_action_task import AutomatedActionTask
from automated_actions.config import settings
from automated_actions.db.models import Action

log = logging.getLogger(__name__)


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
        log.info(
            f"Restarting OpenShift workload {self.kind} {self.name} in namespace {self.namespace}"
        )
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
    cluster_connection = get_cluster_connection_data(cluster, settings)
    oc = OpenshiftClient(
        server_url=cluster_connection.url, token=cluster_connection.token
    )
    OpenshiftWorkloadRestart(oc, namespace, kind, name).run()


class OpenshiftWorkloadDelete:
    def __init__(
        self,
        oc: OpenshiftClient,
        namespace: str,
        api_version: str,
        kind: str,
        name: str,
    ) -> None:
        self.oc = oc
        self.namespace = namespace
        self.name = name
        self.api_version = api_version
        self.kind = kind

    def run(self) -> None:
        log.info(
            f"Deleting OpenShift workload {self.api_version}/{self.kind} {self.name} in namespace {self.namespace}"
        )
        self.oc.delete(
            namespace=self.namespace,
            api_version=self.api_version,
            kind=self.kind,
            name=self.name,
        )


@app.task(base=AutomatedActionTask)
def openshift_workload_delete(
    cluster: str,
    namespace: str,
    api_version: str,
    kind: str,
    name: str,
    action: Action,  # noqa: ARG001
) -> None:
    cluster_connection = get_cluster_connection_data(cluster, settings)
    oc = OpenshiftClient(
        server_url=cluster_connection.url, token=cluster_connection.token
    )
    OpenshiftWorkloadDelete(oc, namespace, api_version, kind, name).run()


class OpenshiftTriggerCronjob:
    def __init__(
        self,
        action: Action,
        oc: OpenshiftClient,
        namespace: str,
        cronjob: str,
    ) -> None:
        self.action = action
        self.oc = oc
        self.namespace = namespace
        self.cronjob = cronjob

    def run(self) -> None:
        log.info(
            f"Triggering OpenShift cronjob {self.cronjob} in namespace {self.namespace}"
        )
        self.oc.trigger_cronjob(
            namespace=self.namespace,
            cronjob=self.cronjob,
            annotations={
                "automated-actions.action_id": str(self.action.action_id),
            },
        )


@app.task(base=AutomatedActionTask)
def openshift_trigger_cronjob(
    cluster: str, namespace: str, cronjob: str, action: Action
) -> None:
    cluster_connection = get_cluster_connection_data(cluster, settings)
    oc = OpenshiftClient(
        server_url=cluster_connection.url, token=cluster_connection.token
    )
    OpenshiftTriggerCronjob(action, oc, namespace, cronjob).run()
