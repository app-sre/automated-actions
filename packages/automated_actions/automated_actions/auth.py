import logging
import re
from json import JSONDecodeError
from typing import Protocol, Self
from urllib.parse import quote

import httpx
import jwt
from fastapi import APIRouter, HTTPException, Request, Response, status
from itsdangerous import URLSafeTimedSerializer
from pydantic import BaseModel
from starlette.responses import RedirectResponse

log = logging.getLogger(__name__)


class AccessToken(BaseModel):
    name: str
    preferred_username: str
    email: str
    realm_access: dict[str, list[str]]


class UserModelProtocol(Protocol):
    @classmethod
    def load(cls, username: str, name: str, email: str) -> Self: ...

    def dump(self) -> BaseModel: ...


class OpenIDConnect[UserModel: UserModelProtocol]:
    def __init__(
        self,
        issuer: str,
        client_id: str,
        client_secret: str,
        session_secret: str,
        scope: str = "openid email profile",
        *,
        enforce_https: bool = True,
        user_model: type[UserModel],
    ) -> None:
        self.issuer = issuer
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self.enforce_https = enforce_https
        self.user_model = user_model

        res = httpx.get(
            self.issuer.rstrip("/") + "/.well-known/openid-configuration", timeout=5
        )
        res.raise_for_status()
        endpoints: dict[str, str] = res.json()

        self.authorization_endpoint = endpoints["authorization_endpoint"]
        self.token_endpoint = endpoints["token_endpoint"]
        self.userinfo_endpoint = endpoints["userinfo_endpoint"]

        self.router = APIRouter()
        self.router.add_api_route(
            "/login",
            self.login,
            name="login",
            methods=["GET"],
            include_in_schema=False,
        )
        self.router.add_api_route(
            "/callback",
            self.callback,
            name="callback",
            methods=["GET"],
            include_in_schema=False,
        )
        self.router.add_api_route(
            "/logout", self.logout, methods=["GET"], include_in_schema=False
        )

        self.session_serializer = URLSafeTimedSerializer(session_secret)

    async def __call__(self, request: Request) -> UserModel:
        enforce_login = HTTPException(
            status_code=307,
            detail="Not authenticated",
            headers={
                "Location": str(request.url_for("login"))
                + f"?next_url={quote(str(request.url))}"
            },
        )
        session_token = request.cookies.get("session")
        if session_token:
            # already authenticated
            try:
                access_token = self.session_serializer.loads(session_token)
                return self.get_user_info(access_token)
            except Exception:  # noqa: BLE001
                log.error("Access token cannot be loaded or is outdated")  # noqa: TRY400
                raise enforce_login from None

        if authorization := request.headers.get("Authorization"):
            # custom auth
            raise NotImplementedError(f"Custom auth not implemented: {authorization}")

        raise enforce_login

    def login(self, request: Request, next_url: str = "") -> Response:
        auth_url = (
            f"{self.authorization_endpoint}?response_type=code"
            f"&scope={quote(self.scope)}"
            f"&client_id={quote(self.client_id)}"
            f"&redirect_uri={quote(str(request.url_for('callback')), safe='')}"
            f"&state={quote(next_url)}"
        )
        return RedirectResponse(auth_url)

    async def callback(
        self, request: Request, response: Response, code: str, state: str
    ) -> Response:
        """Keycloak leitet nach Authentifizierung hierher zurück."""
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                self.token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": str(request.url_for("callback")),
                },
                auth=(self.client_id, self.client_secret),
            )

        if not httpx.codes.is_success(token_response.status_code):
            raise HTTPException(status_code=400, detail="Token request failed")

        token_data = token_response.json()
        session_token = self.session_serializer.dumps(token_data["access_token"])
        response = RedirectResponse(url=state)
        response.set_cookie(
            key="session", value=session_token, secure=self.enforce_https, expires=3600
        )
        return response

    @staticmethod
    def logout(response: Response) -> Response:
        response = RedirectResponse(url="/")
        response.delete_cookie("session")
        return response

    def get_user_info(self, access_token: str) -> UserModel:
        # Check if access token is still valid
        response = httpx.get(
            self.userinfo_endpoint,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=5,
        )
        response.raise_for_status()
        token = AccessToken(
            **jwt.decode(
                access_token,
                audience=self.client_id,
                options={"verify_signature": False},
            )
        )
        return self.user_model.load(
            username=token.preferred_username,
            name=token.name,
            email=token.email,
        )


class OPA[UserModel: UserModelProtocol]:
    def __init__(
        self,
        opa_host: str,
        skip_endpoints: list[str] | None = None,
        package_name: str = "authz",
    ) -> None:
        self.opa_url = (
            f"{opa_host.rstrip('/')}/v1/data/{package_name.replace('.', '/')}/allow"
        )
        self.skip_endpoints = [re.compile(skip) for skip in skip_endpoints or []]

    def should_skip_endpoint(self, endpoint: str) -> bool:
        return any(skip.match(endpoint) for skip in self.skip_endpoints)

    async def __call__(self, request: Request, user: UserModel) -> None:
        # allow endpoints without authorization
        if self.should_skip_endpoint(request.url.path):
            return

        data = {"input": user.dump().model_dump()}
        data["input"]["obj"] = request["route"].operation_id
        data["input"]["params"] = request.path_params
        async with httpx.AsyncClient() as client:
            # Call OPA
            opa_decision = await client.post(self.opa_url, json=data, timeout=5)

        if not self.check_opa_decision(opa_decision):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized"
            )

    @staticmethod
    def check_opa_decision(opa_decision: httpx.Response) -> bool:
        if opa_decision.status_code != status.HTTP_200_OK:
            log.error(f"Returned with status {opa_decision.status_code}.")
            return False
        try:
            return opa_decision.json().get("result", False)
        except JSONDecodeError:
            log.exception("Unable to decode OPA response.")
            return False
