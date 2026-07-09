import logging
from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any, Protocol, Self

from automated_actions.config import settings
from boto3 import Session
from botocore.config import Config
from pydantic import BaseModel
from types_boto3_rds.client import RDSClient
from types_boto3_rds.type_defs import EventTypeDef

from automated_actions_utils.vault_client import SecretFieldNotFoundError, VaultClient

log = logging.getLogger(__name__)


class RdsInstanceStatus(StrEnum):
    """Known RDS DB instance statuses."""

    AVAILABLE = "available"
    BACKING_UP = "backing-up"
    CREATING = "creating"
    DELETING = "deleting"
    FAILED = "failed"
    INACCESSIBLE_ENCRYPTION_CREDENTIALS = "inaccessible-encryption-credentials"
    INACCESSIBLE_ENCRYPTION_CREDENTIALS_RECOVERABLE = (
        "inaccessible-encryption-credentials-recoverable"
    )
    INCOMPATIBLE_NETWORK = "incompatible-network"
    INCOMPATIBLE_OPTION_GROUP = "incompatible-option-group"
    INCOMPATIBLE_PARAMETERS = "incompatible-parameters"
    INCOMPATIBLE_RESTORE = "incompatible-restore"
    MAINTENANCE = "maintenance"
    MODIFYING = "modifying"
    REBOOTING = "rebooting"
    RESTORE_ERROR = "restore-error"
    STARTING = "starting"
    STOPPED = "stopped"
    STOPPING = "stopping"
    STORAGE_FULL = "storage-full"
    STORAGE_OPTIMIZATION = "storage-optimization"
    UPGRADING = "upgrading"


RDS_TERMINAL_ERROR_STATES = frozenset({
    RdsInstanceStatus.FAILED,
    RdsInstanceStatus.INCOMPATIBLE_NETWORK,
    RdsInstanceStatus.INCOMPATIBLE_OPTION_GROUP,
    RdsInstanceStatus.INCOMPATIBLE_PARAMETERS,
    RdsInstanceStatus.INCOMPATIBLE_RESTORE,
    RdsInstanceStatus.INACCESSIBLE_ENCRYPTION_CREDENTIALS,
    RdsInstanceStatus.INACCESSIBLE_ENCRYPTION_CREDENTIALS_RECOVERABLE,
    RdsInstanceStatus.RESTORE_ERROR,
    RdsInstanceStatus.STORAGE_FULL,
})


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

    def __init__(self, credentials: AWSCredentials, region: str | None) -> None:
        self.session = credentials.build_session()
        self.config = Config(
            region_name=region,
            retries={
                "max_attempts": 5,
                "mode": "standard",
            },
        )
        self.rds_client: RDSClient = self.session.client("rds", config=self.config)

    def __enter__(self) -> Self:
        """Enables the use of the AWSApi instance in a context manager."""
        return self

    def __exit__(self, *args: object, **kwargs: Any) -> None:
        """Handles cleanup when exiting the context manager."""
        self.rds_client.close()

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

    def start_rds_instance(self, identifier: str) -> None:
        """Starts a stopped RDS database instance.

        Args:
            identifier: The DB instance identifier.
        """
        log.info(f"Starting RDS instance {identifier}")
        self.rds_client.start_db_instance(DBInstanceIdentifier=identifier)

    def stop_rds_instance(self, identifier: str) -> None:
        """Stops a running RDS database instance.

        Args:
            identifier: The DB instance identifier.
        """
        log.info(f"Stopping RDS instance {identifier}")
        self.rds_client.stop_db_instance(DBInstanceIdentifier=identifier)

    def get_rds_instance_status(self, identifier: str) -> RdsInstanceStatus:
        """Returns the current status of an RDS instance.

        Args:
            identifier: The DB instance identifier.

        Returns:
            The RdsInstanceStatus enum value.
        """
        response = self.rds_client.describe_db_instances(
            DBInstanceIdentifier=identifier
        )
        return RdsInstanceStatus(response["DBInstances"][0]["DBInstanceStatus"])

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
