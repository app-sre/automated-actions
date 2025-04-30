import logging
import re
from collections.abc import Iterable
from datetime import UTC
from datetime import datetime as dt
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
    iss: str  # issuer
    exp: int  # expiration time
    iat: int  # issued at


class UserModelProtocol(Protocol):
    username: str

    @classmethod
    def load(cls, username: str, name: str, email: str) -> Self: ...

    def dump(self) -> BaseModel: ...

    def set_allowed_actions(self, allowed_actions: Iterable[str]) -> None: ...


class OpenIDConnect[UserModel: UserModelProtocol]:
    def __init__(
        self,
        issuer: str,
        client_id: str,
        client_secret: str,
        session_secret: str,
        session_timeout_secs: int,
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
        self.session_timeout_secs = session_timeout_secs

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
            except Exception:
                log.exception("Access token cannot be loaded or is outdated")
                raise enforce_login from None

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
        """Keycloak callback."""
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
            key="session",
            value=session_token,
            secure=self.enforce_https,
            expires=self.session_timeout_secs,
        )
        return response

    @staticmethod
    def logout(response: Response) -> Response:
        response = RedirectResponse(url="/")
        response.delete_cookie("session")
        return response

    def get_user_info(self, access_token: str) -> UserModel:
        # Check against the userinfo endpoint
        response = httpx.get(
            self.userinfo_endpoint,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=5,
        )
        response.raise_for_status()
        token = AccessToken(
            **jwt.decode(
                access_token,
                options={
                    # no further verification needed because we verify the token via the userinfo endpoint
                    "verify_signature": False,
                    "require": ["exp", "iat", "iss"],
                },
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
            f"{opa_host.rstrip('/')}/v1/data/{package_name.replace('.', '/')}"
        )
        self.skip_endpoints = [re.compile(skip) for skip in skip_endpoints or []]

    def should_skip_endpoint(self, endpoint: str) -> bool:
        return any(skip.match(endpoint) for skip in self.skip_endpoints)

    @staticmethod
    def get_opa_result(opa_decision: httpx.Response) -> bool | dict | list | None:
        if opa_decision.status_code != status.HTTP_200_OK:
            log.error(f"Returned with status {opa_decision.status_code}.")
            return False
        try:
            return opa_decision.json().get("result")
        except JSONDecodeError:
            log.exception("Unable to decode OPA response.")
            return False

    async def user_is_authorized(
        self, user: UserModel, obj: str, params: dict[str, str]
    ) -> bool:
        """Check if user is authorized to access endpoint."""
        data = {"input": user.dump().model_dump()}
        data["input"]["obj"] = obj
        data["input"]["params"] = params

        async with httpx.AsyncClient() as client:
            opa_decision = await client.post(
                f"{self.opa_url}/allow", json=data, timeout=5
            )

        result = self.get_opa_result(opa_decision)
        if not isinstance(result, bool):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OPA returned unexpected result",
            )
        return result

    async def user_objects(self, user: UserModel) -> list[str]:
        """Get objects for the user."""
        async with httpx.AsyncClient() as client:
            opa_decision = await client.post(
                f"{self.opa_url}/objects",
                json={
                    "input": {
                        "username": user.username,
                    }
                },
                timeout=5,
            )

        result = self.get_opa_result(opa_decision)
        if not isinstance(result, list):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OPA returned unexpected result",
            )
        return result

    async def __call__(self, request: Request, user: UserModel) -> None:
        # allow endpoints without authorization
        if self.should_skip_endpoint(request.url.path):
            return

        # check if user is authorized to access endpoint
        if not await self.user_is_authorized(
            user, obj=request["route"].operation_id, params=request.path_params
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized"
            )

        # get user allowed_actions
        allowed_actions = await self.user_objects(user)
        user.set_allowed_actions(allowed_actions)


class BearerTokenAuth[UserModel: UserModelProtocol]:
    def __init__(self, issuer: str, secret: str, user_model: type[UserModel]) -> None:
        self.issuer = issuer
        self.secret = secret
        self.user_model = user_model

    async def __call__(self, request: Request) -> UserModel | None:
        if authorization := request.headers.get("Authorization"):
            # check if the authorization header is a bearer token
            if not authorization.startswith("Bearer "):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authorization header.",
                    headers={"WWW-Authenticate": "Bearer"},
                ) from None

            # extract the token from the header
            token = authorization.split(" ")[1]
            try:
                return self.get_user_info(token)
            except Exception:
                log.exception("Access token cannot be loaded or is not valid anymore")

        return None

    def get_user_info(self, encoded_token: str) -> UserModel:
        token = AccessToken(
            **jwt.decode(
                encoded_token,
                self.secret,
                algorithms="HS256",
                options={
                    "require": ["exp", "iat", "iss"],
                    "verify_exp": True,
                    "verify_iss": True,
                },
                issuer=self.issuer,
            )
        )
        return self.user_model.load(
            username=token.preferred_username,
            name=token.name,
            email=token.email,
        )

    def create_token(self, username: str, name: str, email: str, expiration: dt) -> str:
        return jwt.encode(
            {
                "preferred_username": username,
                "name": name,
                "email": email,
                "iss": self.issuer,
                "exp": expiration,
                "iat": dt.now(tz=UTC),
            },
            self.secret,
            algorithm="HS256",
        )
