from typing import TYPE_CHECKING

from automated_actions_utils.cluster_connection import get_cluster_connection_data
from automated_actions_utils.openshift_client import (
    OpenshiftClient,
    SecretKeyRef,
    job_builder,
)

from automated_actions.celery.app import app
from automated_actions.celery.automated_action_task import AutomatedActionTask
from automated_actions.config import settings

if TYPE_CHECKING:
    from automated_actions.db.models import Action


class PayloadTrackerCreatePartition:
    def __init__(
        self,
        action: Action,
        oc: OpenshiftClient,
        namespace: str,
    ) -> None:
        self.action = action
        self.oc = oc
        self.namespace = namespace

    def run(
        self,
        image: str,
        date: str,
        secret_name: str,
        env_secret_mappings: dict[str, str],
    ) -> None:
        # `date` is validated as a calendar date by the API layer, so it is safe
        # to interpolate into the SQL statement. create_partition is idempotent
        # (CREATE TABLE / indexes IF NOT EXISTS), so re-runs are harmless.
        sql = (
            f"SELECT create_partition('{date}'::date, "
            f"'{date}'::date + INTERVAL '1 DAY');"
        )
        job = job_builder(
            image=image,
            command=["psql"],
            args=["-c", sql],
            job_name="create-partition",
            annotations={
                "automated-actions.action_id": str(self.action.action_id),
            },
            env_secrets={
                key: SecretKeyRef(
                    secret=secret_name,
                    key=value,
                )
                for key, value in env_secret_mappings.items()
            },
        )
        return self.oc.run_job(namespace=self.namespace, job=job)


@app.task(base=AutomatedActionTask)
def payload_tracker_create_partition(
    cluster: str,
    namespace: str,
    date: str,
    *,
    action: Action,
) -> None:
    cluster_connection = get_cluster_connection_data(cluster, settings)
    oc = OpenshiftClient(
        server_url=cluster_connection.url, token=cluster_connection.token
    )
    config = settings.payload_tracker_create_partition
    PayloadTrackerCreatePartition(
        action=action,
        oc=oc,
        namespace=namespace,
    ).run(
        image=f"{config.image}:{config.image_tag}",
        date=date,
        secret_name=config.db_secret_name,
        env_secret_mappings=config.env_secret_mappings,
    )
