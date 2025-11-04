import http
import logging
import time
from datetime import UTC, datetime
from enum import StrEnum

from kubernetes.client import (
    ApiClient as K8sApiClient,
)
from kubernetes.client import (
    ApiException,
    BatchV1Api,
    Configuration,
    V1Container,
    V1CronJob,
    V1EnvVar,
    V1EnvVarSource,
    V1Job,
    V1JobSpec,
    V1ObjectMeta,
    V1PodSpec,
    V1PodTemplateSpec,
    V1SecretKeySelector,
)
from kubernetes.dynamic.exceptions import NotFoundError
from kubernetes.dynamic.resource import ResourceInstance
from openshift.dynamic import DynamicClient
from pydantic import BaseModel
from sretoolbox.utils.k8s import unique_job_name

SUPPORTED_POD_OWNERS = {"ReplicaSet", "StatefulSet"}
log = logging.getLogger(__name__)


class OpenshiftClientResourceNotFoundError(Exception):
    pass


class OpenshiftClientPodDeletionNotSupportedError(Exception):
    pass


class PodError(Exception):
    """Custom exception for pod-related errors."""


class RollingRestartResource(StrEnum):
    deployment = "Deployment"
    statefulset = "StatefulSet"
    daemonset = "DaemonSet"


class SecretKeyRef(BaseModel):
    secret: str
    key: str
    optional: bool = True


def job_builder(
    image: str,
    command: list[str],
    args: list[str] | None = None,
    job_name: str = "temp-job",
    backoff_limit: int = 4,
    annotations: dict[str, str] | None = None,
    env: dict[str, str] | None = None,
    env_secrets: dict[str, SecretKeyRef] | None = None,
    auto_cleanup_after_seconds: int | None = 3600,
) -> V1Job:
    """Builds a Kubernetes Job definition."""
    env_vars = []
    for key, value in (env or {}).items():
        env_vars.append(V1EnvVar(name=key, value=value))

    for key, secret_ref in (env_secrets or {}).items():
        env_vars.append(
            V1EnvVar(
                name=key,
                value_from=V1EnvVarSource(
                    secret_key_ref=V1SecretKeySelector(
                        name=secret_ref.secret,
                        key=secret_ref.key,
                        optional=secret_ref.optional,
                    )
                ),
            )
        )

    container = V1Container(
        name="default",
        image=image,
        command=command,
        args=args or [],
        env=env_vars,
    )

    pod_spec = V1PodSpec(
        restart_policy="Never",
        containers=[container],
    )

    template = V1PodTemplateSpec(
        metadata=V1ObjectMeta(
            labels={"app": "automated-actions"},
        ),
        spec=pod_spec,
    )

    job_spec = V1JobSpec(
        template=template,
        backoff_limit=backoff_limit,
        ttl_seconds_after_finished=auto_cleanup_after_seconds,
    )

    return V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=V1ObjectMeta(
            name=unique_job_name(job_name),
            annotations=annotations,
        ),
        spec=job_spec,
    )


class OpenshiftClient:
    def __init__(self, server_url: str, token: str, retries: int = 5) -> None:
        configuration = Configuration(
            host=server_url, api_key={"authorization": f"Bearer {token}"}
        )
        configuration.retries = retries
        self.k8s_api_client = K8sApiClient(configuration=configuration)
        self.dyn_client = DynamicClient(self.k8s_api_client)
        self.batch_v1 = BatchV1Api(api_client=self.k8s_api_client)

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

    def delete(
        self, namespace: str, api_version: str, kind: str, name: str
    ) -> ResourceInstance:
        """Delete a resource in the specified namespace."""
        api = self.dyn_client.resources.get(api_version=api_version, kind=kind)
        return api.delete(name=name, namespace=namespace)

    def job_wait(
        self,
        job_name: str,
        namespace: str,
        timeout_seconds: int,
        check_interval: int = 5,
    ) -> None:
        """Wait for a Kubernetes Job to complete."""
        start_time = time.time()

        while True:
            if time.time() - start_time > timeout_seconds:
                raise TimeoutError(f"Timeout waiting for Job '{job_name}' to complete.")

            try:
                job: V1Job = self.batch_v1.read_namespaced_job(
                    name=job_name, namespace=namespace
                )
            except ApiException as err:
                if err.status == http.HTTPStatus.NOT_FOUND:
                    log.debug(f"Job '{job_name}' not found yet, retrying...")
                    time.sleep(check_interval)
                    continue
                raise

            if not job.status:
                log.debug(f"Job '{job_name}' has no status yet, retrying...")
                time.sleep(check_interval)
                continue

            if (
                hasattr(job.status, "succeeded")
                and job.status.succeeded is not None
                and job.status.succeeded >= 1
            ):
                log.debug(f"Job '{job_name}' completed successfully.")
                return

            if (
                hasattr(job.status, "failed")
                and job.status.failed is not None
                and job.status.failed > job.spec.backoffLimit
            ):
                raise PodError(
                    f"Job '{job_name}' failed with {job.status.failed} failures. Check logs for details."
                )

            log.debug(f"Job '{job_name}' still running...")
            time.sleep(check_interval)

    def run_job(
        self,
        namespace: str,
        job: V1Job,
        *,
        wait_for_completion: bool = True,
    ) -> None:
        """Run a Kubernetes Job and optionally wait for its completion."""
        log.info(f"Creating Job '{job.metadata.name}' in namespace '{namespace}'")
        self.batch_v1.create_namespaced_job(
            namespace=namespace,
            body=self.k8s_api_client.sanitize_for_serialization(job),
        )
        if wait_for_completion:
            self.job_wait(
                job_name=job.metadata.name, namespace=namespace, timeout_seconds=10 * 60
            )

    def trigger_cronjob(
        self, namespace: str, cronjob: str, annotations: dict[str, str] | None = None
    ) -> None:
        try:
            k8s_cronjob: V1CronJob = self.batch_v1.read_namespaced_cron_job(
                name=cronjob, namespace=namespace
            )
        except ApiException as err:
            if err.status == http.HTTPStatus.NOT_FOUND:
                raise OpenshiftClientResourceNotFoundError(
                    f"CronJob {cronjob} does not exist in namespace {namespace}"
                ) from err
            raise

        # make mypy happy
        assert k8s_cronjob.spec is not None
        assert k8s_cronjob.spec.job_template is not None

        job = V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=V1ObjectMeta(
                name=unique_job_name(f"aa-triggered-{cronjob}"),
                annotations=annotations,
            ),
            spec=k8s_cronjob.spec.job_template.spec,
        )
        self.run_job(namespace=namespace, job=job, wait_for_completion=False)
