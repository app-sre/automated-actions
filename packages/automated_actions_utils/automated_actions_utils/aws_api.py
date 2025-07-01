import logging
from abc import ABC, abstractmethod
from typing import Any, Protocol

from automated_actions.config import settings
from boto3 import Session
from botocore.config import Config
from pydantic import BaseModel
from types_boto3_rds.type_defs import EventTypeDef

from automated_actions_utils.vault_client import SecretFieldNotFoundError, VaultClient

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
        self.rds_client = self.session.client("rds", config=self.config)

    def __enter__(self) -> "AWSApi":
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
