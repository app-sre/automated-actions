from pydantic_settings import BaseSettings


class ExternalResourceElastiCacheConfig(BaseSettings):
    """Configuration for the external resource elasticache related actions."""

    image: str = "quay.io/app-sre/debug-container"
    image_tag: str = "latest"
    memory_request: str = "128Mi"
    memory_limit: str = "1Gi"
    cpu_request: str = "100m"
    cpu_limit: str = "1"
    flush_command: list[str] = ["bash"]
    flush_command_args: list[str] = ["-c", 'echo "FLUSHALL" | redis-cli-ext']
    # ERv2 connection secret mapping
    env_secret_mappings: dict[str, str] = {
        "REDISCLI_HOST": "db.endpoint",
        "REDISCLI_PORT": "db.port",
        "REDISCLI_AUTH": "db.auth_token",
    }


class ExternalResourceRdsLogsConfig(BaseSettings):
    """Configuration for the external resource RDS logs related actions."""

    s3_url: str = "http://s3.localhost.localstack.cloud:4566"
    access_key_id: str = "localstack"
    secret_access_key: str = "localstack"  # noqa: S105
    region: str = "us-east-1"
    bucket: str = "automated-actions"
    prefix: str = "rds-logs"


class Settings(BaseSettings):
    # pydantic config
    model_config = {
        "env_prefix": "aa_",
        "env_nested_delimiter": "__",
    }

    # app config
    debug: bool = False
    url: str = "http://localhost:8080"
    root_path: str = ""
    environment: str

    # worker config
    broker_url: str = "sqs://localhost:4566"
    sqs_url: str = "http://localhost:4566/000000000000/automated-actions"
    broker_aws_region: str = "us-east-1"
    broker_aws_access_key_id: str = "localstack"
    broker_aws_secret_access_key: str = "localstack"  # noqa: S105
    retries: int | None = None
    retry_delay: int = 10

    # db config
    dynamodb_url: str = "http://localhost:4566"
    dynamodb_aws_region: str = "us-east-1"
    dynamodb_aws_access_key_id: str = "localstack"
    dynamodb_aws_secret_access_key: str = "localstack"  # noqa: S105

    # OIDC config
    oidc_issuer: str = "https://auth.redhat.com/auth/realms/EmployeeIDP"
    oidc_client_id: str
    oidc_client_secret: str
    session_secret: str
    session_timeout_secs: int = 3600
    token_secret: str

    # AuthZ
    opa_host: str = "http://opa:8181"

    # worker metrics config
    worker_metrics_port: int = 8000

    # qontract-server
    qontract_server_url: str = "http://localhost:4000/graphql"
    qontract_server_token: str | None = None

    # vault
    vault_server_url: str = "http://localhost:8200"
    vault_role_id: str | None = None
    vault_secret_id: str | None = None
    vault_kube_auth_role: str | None = None
    vault_kube_auth_mount: str | None = None

    # external resources - ElastiCache
    external_resource_elasticache: ExternalResourceElastiCacheConfig = (
        ExternalResourceElastiCacheConfig()
    )
    external_resource_rds_logs: ExternalResourceRdsLogsConfig = (
        ExternalResourceRdsLogsConfig()
    )


settings = Settings()
