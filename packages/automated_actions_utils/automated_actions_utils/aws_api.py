from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Generator, Iterable
from typing import TYPE_CHECKING, Any, Protocol, Self

from automated_actions.config import settings
from boto3 import Session
from botocore.config import Config
from pydantic import BaseModel
from zipstream import ZIP_DEFLATED, ZipStream

from automated_actions_utils.vault_client import SecretFieldNotFoundError, VaultClient

if TYPE_CHECKING:
    from types_boto3_rds.client import RDSClient
    from types_boto3_rds.type_defs import EventTypeDef
    from types_boto3_s3.client import S3Client
    from types_boto3_s3.type_defs import CompletedPartTypeDef


log = logging.getLogger(__name__)


class VaultSecret(Protocol):
    path: str
    version: int | None


class AWSCredentials(ABC):
    @abstractmethod
    def build_session(self) -> Session:
        """Builds and returns a boto3 Session using the implemented credentials."""


class AWSStaticCredentials(BaseModel, AWSCredentials):
    """Represents static AWS credentials consisting of an access key ID, secret access key, and region."""

    access_key_id: str
    secret_access_key: str
    region: str

    def build_session(self) -> Session:
        """Builds and returns a boto3 Session using static credentials."""
        return Session(
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            region_name=self.region,
        )


class LogStream(BaseModel):
    """Represents a log stream for RDS logs."""

    name: str
    content: Generator[bytes, None, None]


def get_aws_credentials(vault_secret: VaultSecret, region: str) -> AWSCredentials:
    """Retrieves AWS credentials from Vault and returns them as an AWSCredentials object.

    Args:
        vault_secret: The VaultSecret object containing path and version information.
        region: The AWS region for the credentials.

    Returns:
        An AWSStaticCredentials object populated with credentials from Vault.

    Raises:
        SecretFieldNotFoundError: If 'aws_access_key_id' or 'aws_secret_access_key'
                                  are not found in the secret.
    """
    vault_client = VaultClient(
        server_url=settings.vault_server_url,
        role_id=settings.vault_role_id,
        secret_id=settings.vault_secret_id,
        kube_auth_role=settings.vault_kube_auth_role,
        kube_auth_mount=settings.vault_kube_auth_mount,
    )

    secret = vault_client.read_secret(
        path=vault_secret.path,
        version=str(vault_secret.version),
    )

    if "aws_access_key_id" not in secret or "aws_secret_access_key" not in secret:
        raise SecretFieldNotFoundError(
            f"aws_access_key_id or aws_secret_access_key not found in secret {vault_secret.path}"
        )

    return AWSStaticCredentials(
        access_key_id=secret["aws_access_key_id"],
        secret_access_key=secret["aws_secret_access_key"],
        region=region,
    )


class AWSApi:
    """A client for interacting with AWS services."""

    def __init__(
        self,
        credentials: AWSCredentials,
        region: str | None = None,
        s3_endpoint_url: str | None = None,
    ) -> None:
        self.session = credentials.build_session()
        self.config = Config(
            region_name=region,
            retries={
                "max_attempts": 5,
                "mode": "standard",
            },
        )
        self.rds_client: RDSClient = self.session.client("rds", config=self.config)
        self.s3_client: S3Client = self.session.client(
            "s3", config=self.config, endpoint_url=s3_endpoint_url
        )

    def __enter__(self) -> Self:
        """Enables the use of the AWSApi instance in a context manager."""
        return self

    def __exit__(self, *args: object, **kwargs: Any) -> None:
        """Handles cleanup when exiting the context manager."""
        self.rds_client.close()
        self.s3_client.close()

    @staticmethod
    def _upload_multipart_chunk(
        target_aws_api: AWSApi,
        bucket: str,
        s3_key: str,
        upload_id: str,
        part_number: int,
        data: bytes,
    ) -> CompletedPartTypeDef:
        """Uploads a single part for multipart upload and returns part info."""
        log.debug(f"Uploading part {part_number} ({len(data)} bytes)")
        part_response = target_aws_api.s3_client.upload_part(
            Bucket=bucket,
            Key=s3_key,
            PartNumber=part_number,
            UploadId=upload_id,
            Body=data,
        )
        return {
            "ETag": part_response["ETag"],
            "PartNumber": part_number,
        }

    def reboot_rds_instance(self, identifier: str, *, force_failover: bool) -> None:
        """Reboots a specified RDS database instance.

        Args:
            identifier: The DB instance identifier.
            force_failover: When true, the reboot is conducted through a MultiAZ failover.
                            Cannot be set to true if the instance is not configured for MultiAZ.
        """
        log.info(f"Rebooting RDS instance {identifier}")
        self.rds_client.reboot_db_instance(
            DBInstanceIdentifier=identifier, ForceFailover=force_failover
        )

    def rds_get_events(
        self,
        identifier: str,
        duration_min: int = 60,
    ) -> list[EventTypeDef]:
        """Retrieves events for a specified RDS instance.

        Args:
            identifier: The DB instance identifier.
            duration_min: The duration in minutes for which to retrieve events.

        Returns:
            A list of events.
        """
        events: list[EventTypeDef] = []
        log.info(f"Retrieving RDS events for {identifier}")
        paginator = self.rds_client.get_paginator("describe_events")
        for page in paginator.paginate(
            SourceIdentifier=identifier, SourceType="db-instance", Duration=duration_min
        ):
            events.extend(page.get("Events", []))
        return events

    def create_rds_snapshot(self, identifier: str, snapshot_identifier: str) -> None:
        """Creates a snapshot of a specified RDS instance.

        Args:
            identifier: The DB instance identifier.
            snapshot_identifier: The snapshot identifier.
        """
        log.info(
            f"Creating snapshot {snapshot_identifier} for RDS instance {identifier}"
        )
        self.rds_client.create_db_snapshot(
            DBInstanceIdentifier=identifier,
            DBSnapshotIdentifier=snapshot_identifier,
        )

    def list_rds_logs(self, identifier: str) -> list[str]:
        """Lists the log files for a specified RDS instance."""
        logs: list[str] = []
        log.info(f"Listing RDS logs for instance {identifier}")
        paginator = self.rds_client.get_paginator("describe_db_log_files")
        for page in paginator.paginate(DBInstanceIdentifier=identifier):
            logs.extend(
                log_file["LogFileName"]
                for log_file in page.get("DescribeDBLogFiles", [])
                if log_file["LogFileName"]
            )
        return logs

    def stream_rds_log(
        self, identifier: str, log_file: str
    ) -> Generator[bytes, None, None]:
        """Streams a specific RDS log file."""
        marker = "0"
        while True:
            response = self.rds_client.download_db_log_file_portion(
                DBInstanceIdentifier=identifier,
                LogFileName=log_file,
                Marker=marker,
            )
            if log_data_chunk := response.get("LogFileData"):
                yield log_data_chunk.encode("utf-8")

            if response["AdditionalDataPending"]:
                marker = response["Marker"]
            else:
                break

    def stream_rds_logs_to_s3_zip(
        self,
        log_streams: Iterable[LogStream],
        bucket: str,
        s3_key: str,
        target_aws_api: AWSApi | None = None,
    ) -> None:
        """Streams all RDS log files to a single zip file in an S3 bucket using multipart upload."""
        target_aws_api = target_aws_api or self

        # Create a zip stream for large files without loading everything into memory
        zip_stream = ZipStream(compress_type=ZIP_DEFLATED)
        for log_stream in log_streams:
            zip_stream.add(log_stream.content, arcname=log_stream.name)

        # Start multipart upload
        log.info(f"Starting multipart upload for {s3_key} to bucket {bucket}")
        create_response = target_aws_api.s3_client.create_multipart_upload(
            Bucket=bucket, Key=s3_key, ContentType="application/zip"
        )
        upload_id = create_response["UploadId"]

        try:
            parts = []
            part_number = 1
            chunk_size = 5 * 1024 * 1024  # 5MB minimum part size for S3
            buffer = b""

            # Stream zip data in chunks and upload as parts
            for chunk in zip_stream:
                buffer += chunk

                # Upload when buffer reaches chunk size
                while len(buffer) >= chunk_size:
                    part_data = buffer[:chunk_size]
                    buffer = buffer[chunk_size:]

                    part_info = self._upload_multipart_chunk(
                        target_aws_api,
                        bucket,
                        s3_key,
                        upload_id,
                        part_number,
                        part_data,
                    )
                    parts.append(part_info)
                    part_number += 1

            # Upload remaining buffer as final part (if any)
            if buffer:
                part_info = self._upload_multipart_chunk(
                    target_aws_api, bucket, s3_key, upload_id, part_number, buffer
                )
                parts.append(part_info)

            # Complete multipart upload
            target_aws_api.s3_client.complete_multipart_upload(
                Bucket=bucket,
                Key=s3_key,
                UploadId=upload_id,
                MultipartUpload={"Parts": parts},
            )
            log.info(f"Successfully completed multipart upload for {s3_key}")

        except:
            # Abort multipart upload on error
            log.exception("Error during multipart upload")
            target_aws_api.s3_client.abort_multipart_upload(
                Bucket=bucket, Key=s3_key, UploadId=upload_id
            )
            raise

    def generate_s3_download_url(
        self, bucket: str, s3_key: str, expiration_secs: int = 3600
    ) -> str:
        """Generate a pre-signed URL for downloading an object from S3."""
        return self.s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": s3_key},
            ExpiresIn=expiration_secs,
        )
