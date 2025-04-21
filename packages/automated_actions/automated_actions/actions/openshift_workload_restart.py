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
