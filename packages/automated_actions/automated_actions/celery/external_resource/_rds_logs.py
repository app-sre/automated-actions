import logging

from automated_actions_utils.aws_api import (
    AWSApi,
    AWSStaticCredentials,
    LogStream,
    get_aws_credentials,
)
from automated_actions_utils.external_resource import (
    ExternalResource,
    ExternalResourceProvider,
    get_external_resource,
)

from automated_actions.celery.app import app
from automated_actions.celery.automated_action_task import AutomatedActionTask
from automated_actions.config import settings
from automated_actions.db.models import Action

log = logging.getLogger(__name__)


class ExternalResourceRDSLogs:
    """Class to handle RDS logs retrieval."""

    def __init__(
        self, aws_api: AWSApi, rds: ExternalResource, s3_bucket: str, s3_prefix: str
    ) -> None:
        self.aws_api = aws_api
        self.rds = rds
        self.s3_bucket = s3_bucket
        self.s3_prefix = s3_prefix

    def run(
        self,
        target_aws_api: AWSApi,
        expiration_days: int,
        s3_file_name: str | None = None,
    ) -> str | None:
        """Retrieve RDS logs and upload them to S3 as a zip file."""
        s3_key = (
            s3_file_name
            or f"{self.s3_prefix}/{self.rds.account.name}-{self.rds.identifier}.zip"
        )
        # append .zip to the filename if not present
        if not s3_key.endswith(".zip"):
            s3_key += ".zip"

        log.info(
            f"Saving RDS logs for {self.rds.account.name}/{self.rds.identifier} to S3 {self.s3_bucket}/{s3_key}"
        )
        log_streams = [
            LogStream(
                name=log_file,
                content=self.aws_api.stream_rds_log(
                    identifier=self.rds.identifier, log_file=log_file
                ),
            )
            for log_file in self.aws_api.list_rds_logs(self.rds.identifier)
        ]
        if not log_streams:
            log.warning(
                f"No logs found for RDS {self.rds.identifier} in account {self.rds.account.name}"
            )
            return None
        self.aws_api.stream_rds_logs_to_s3_zip(
            log_streams=log_streams,
            bucket=self.s3_bucket,
            s3_key=s3_key,
            target_aws_api=target_aws_api,
        )
        return self.aws_api.generate_s3_download_url(
            bucket=self.s3_bucket,
            s3_key=s3_key,
            expiration_secs=expiration_days * 24 * 3600,
        )


@app.task(base=AutomatedActionTask)
def external_resource_rds_logs(
    account: str,
    identifier: str,
    expiration_days: int,
    action: Action,  # noqa: ARG001
    s3_file_name: str | None = None,
) -> str:
    rds = get_external_resource(
        account=account, identifier=identifier, provider=ExternalResourceProvider.RDS
    )
    rds_account_credentials = get_aws_credentials(
        vault_secret=rds.account.automation_token, region=rds.account.region
    )

    log_account_credentials = AWSStaticCredentials(
        access_key_id=settings.external_resource_rds_logs.access_key_id,
        secret_access_key=settings.external_resource_rds_logs.secret_access_key,
        region=settings.external_resource_rds_logs.region,
    )

    with (
        AWSApi(credentials=rds_account_credentials, region=rds.region) as aws_api,
        AWSApi(
            credentials=log_account_credentials,
            s3_endpoint_url=settings.external_resource_rds_logs.s3_url,
        ) as log_aws_api,
    ):
        url = ExternalResourceRDSLogs(
            aws_api=aws_api,
            rds=rds,
            s3_bucket=settings.external_resource_rds_logs.bucket,
            s3_prefix=settings.external_resource_rds_logs.prefix,
        ).run(
            target_aws_api=log_aws_api,
            expiration_days=expiration_days,
            s3_file_name=s3_file_name,
        )

    if not url:
        return "No logs found or no logs available for download."

    return f"Download the RDS logs from the following URL: {url}. This link will expire in {expiration_days} days."
