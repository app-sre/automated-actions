import os
from pathlib import Path

import hvac
import hvac.exceptions
from hvac.api.auth_methods import Kubernetes


class SecretNotFoundError(Exception):
    pass


class SecretAccessForbiddenError(Exception):
    pass


class SecretVersionIsNoneError(Exception):
    pass


class SecretVersionNotFoundError(Exception):
    pass


class SecretFieldNotFoundError(Exception):
    pass


class VaultClientMissingArgsError(Exception):
    pass


VERSION_1 = 1
VERSION_2 = 2
SECRET_VERSION_LATEST = "LATEST"  # noqa: S105


class VaultClient:
    """A class representing a Vault client. Allows read operations."""

    def __init__(
        self,
        server_url: str | None = None,
        role_id: str | None = None,
        secret_id: str | None = None,
        kube_auth_role: str | None = None,
        kube_auth_mount: str | None = None,
        hvac_client: type[hvac.Client] = hvac.Client,
    ) -> None:
        self._client = hvac_client(url=server_url)

        if role_id is not None and secret_id is not None:
            self._client.auth.approle.login(
                role_id=role_id,
                secret_id=secret_id,
            )
        elif kube_auth_role is not None and kube_auth_mount is not None:
            kube_sa_token_path = os.environ.get(
                "KUBE_SA_TOKEN_PATH",
                "/var/run/secrets/kubernetes.io/serviceaccount/token",
            )
            jwt = Path(kube_sa_token_path).read_text(encoding="locale")
            Kubernetes(self._client.adapter).login(
                role=kube_auth_role, jwt=jwt, mount_point=kube_auth_mount
            )
        else:
            raise VaultClientMissingArgsError(
                "Either role_id/secret_id or kube_auth_role/kube_auth_mount must be "
                "provided"
            )

    def read_secret(self, path: str, version: str | None = None) -> dict:
        """Returns a value of a key in a Vault secret."""
        mount_point, read_path = self._split_secret_path(path)
        kv_version = self._get_mount_version(mount_point)

        data = None
        if kv_version == VERSION_2:
            data, _ = self._read_secret_v2(mount_point, read_path, version=version)
        else:
            data = self._read_secret_v1(mount_point, read_path)

        if data is None:
            raise SecretNotFoundError

        return data

    def _read_secret_v2(
        self, mount_point: str, read_path: str, version: str | None
    ) -> tuple[dict, str]:
        if version is None:
            raise SecretVersionIsNoneError(
                f"version can not be null for secret with path '{read_path}' under "
                f"{mount_point} mount_point."
            )

        if version == SECRET_VERSION_LATEST:
            # https://github.com/hvac/hvac/blob/
            # ec048ded30d21c13c21cfa950d148c8bfc1467b0/
            # hvac/api/secrets_engines/kv_v2.py#L85
            version = None
        try:
            secret = self._client.secrets.kv.v2.read_secret_version(
                mount_point=mount_point,
                path=read_path,
                version=version,
            )
        except hvac.exceptions.InvalidPath:
            msg = f"version '{version}' not found for secret with path '{mount_point}/{read_path}'."
            raise SecretVersionNotFoundError(msg) from None
        except hvac.exceptions.Forbidden:
            msg = f"permission denied accessing secret '{mount_point}/{read_path}'"
            raise SecretAccessForbiddenError(msg) from None
        if secret is None or "data" not in secret or "data" not in secret["data"]:
            raise SecretNotFoundError(f"{mount_point}/{read_path}")

        data = secret["data"]["data"]
        secret_version = secret["data"]["metadata"]["version"]
        return data, secret_version

    def _read_secret_v1(self, mount_point: str, read_path: str) -> dict:
        try:
            secret = self._client.secrets.kv.v1.read_secret(
                mount_point=mount_point, path=read_path
            )
        except hvac.exceptions.Forbidden:
            msg = f"permission denied accessing secret '{mount_point}/{read_path}'"
            raise SecretAccessForbiddenError(msg) from None

        if secret is None or "data" not in secret:
            raise SecretNotFoundError(f"{mount_point}/{read_path}")

        return secret["data"]

    @staticmethod
    def _split_secret_path(path: str) -> tuple[str, str]:
        path_split = path.split("/")
        mount_point = path_split[0]
        read_path = "/".join(path_split[1:])

        return mount_point, read_path

    def _get_mount_version(self, mount_point: str) -> int:
        try:
            self._client.secrets.kv.v2.read_configuration(mount_point)
            version = VERSION_2
        except hvac.exceptions.Forbidden:
            version = VERSION_1

        return version
