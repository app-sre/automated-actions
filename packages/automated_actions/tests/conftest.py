# ruff: noqa: S105
import os

os.environ["AA_OIDC_CLIENT_ID"] = "test_client_id"
os.environ["AA_OIDC_CLIENT_SECRET"] = "test_client_secret"
os.environ["AA_SESSION_SECRET"] = "test_session_secret"
os.environ["AA_TOKEN_SECRET"] = "test_token_secret"
