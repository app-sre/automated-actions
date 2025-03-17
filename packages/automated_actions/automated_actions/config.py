from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # pydantic config
    model_config = {"env_prefix": "aa_"}

    # app config
    debug: bool = False
    root_path: str = ""

    # fastapi auth config
    api_keys: list[str] = []

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

    # AuthZ
    opa_host: str = "http://opa:8181"

    # worker metrics config
    worker_metrics_port: int = 8000


settings = Settings()
