from enum import Enum


class OpenshiftWorkloadRestartKind(str, Enum):
    DAEMONSET = "DaemonSet"
    DEPLOYMENT = "Deployment"
    POD = "Pod"
    STATEFULSET = "StatefulSet"

    def __str__(self) -> str:
        return str(self.value)
