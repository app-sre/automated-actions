from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from boto3 import Session
from botocore.config import Config
from pydantic import BaseModel

if TYPE_CHECKING:
    from mypy_boto3_rds import RDSClient


import logging

from automated_actions.config import settings
from automated_actions.utils.vault_client import (
    SecretFieldNotFoundError,
    VaultClient,
    VaultSecret,
)

log = logging.getLogger(__name__)


class AWSCredentials(ABC):
    @abstractmethod
    def build_session(self) -> Session:
        """Get an AWS session using the credentials."""


class AWSStaticCredentials(BaseModel, AWSCredentials):
    """Represents AWS credentials that are static and can be used to create a session."""

    access_key_id: str
    secret_access_key: str
    region: str

    def build_session(self) -> Session:
        return Session(
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            region_name=self.region,
        )


def get_aws_credentials(vault_secret: VaultSecret, region: str) -> AWSCredentials:
    """Get AWS credentials for the given account name."""
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
    """An AWS API client."""

    def __init__(self, credentials: AWSCredentials, region: str | None) -> None:
        self.session = credentials.build_session()
        self.config = Config(region_name=region)

    @property
    def rds_client(self) -> "RDSClient":
        """Gets a boto client"""
        return self.session.client("rds", config=self.config)

    def reboot_rds_instance(self, identifier: str, *, force_failover: bool) -> None:
        """Reboot an RDS instance."""
        log.info(f"Rebooting RDS instance {identifier}")
        self.rds_client.reboot_db_instance(
            DBInstanceIdentifier=identifier, ForceFailover=force_failover
        )
