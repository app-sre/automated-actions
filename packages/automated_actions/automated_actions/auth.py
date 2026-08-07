import logging
import re
import secrets
from datetime import UTC
from datetime import datetime as dt
from json import JSONDecodeError
from typing import TYPE_CHECKING, Any, Protocol, Self
from urllib.parse import quote, urlsplit

import httpx2
import jwt
from fastapi import APIRouter, HTTPException, Request, Response, status
from itsdangerous import URLSafeTimedSerializer
from pydantic import BaseModel
from starlette.responses import RedirectResponse

if TYPE_CHECKING:
    from collections.abc import Iterable

log = logging.getLogger(__name__)

# How long a /login -> /callback round trip may take before the signed OIDC
# state (and its matching cookie) is considered expired.
OIDC_STATE_MAX_AGE_SECS = 600


def _is_safe_next_url(next_url: str) -> bool:
    r"""Only allow same-origin relative paths as post-login redirect targets.

    Rejects absolute URLs and protocol-relative URLs (`//evil.com`) to prevent
    open redirects. Backslashes are rejected too: some browsers normalize a
    leading `/\` into `//`, turning it into a protocol-relative URL that
    `urlsplit` alone would not catch.
    """
    if not next_url.startswith("/") or next_url.startswith("//"):
        return False
    if "\\" in next_url:
        return False
    parsed = urlsplit(next_url)
    return not parsed.scheme and not parsed.netloc


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
        *,
        issuer: str,
        client_id: str,
        client_secret: str,
        session_secret: str,
        session_timeout_secs: int,
        authorization_endpoint: str,
        token_endpoint: str,
        userinfo_endpoint: str,
        scope: str = "openid email profile",
        enforce_https: bool = True,
        user_model: type[UserModel],
    ) -> None:
        self.issuer = issuer
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self.enforce_https = enforce_https
        self.user_model = user_model

        self.authorization_endpoint = authorization_endpoint
        self.token_endpoint = token_endpoint
        self.userinfo_endpoint = userinfo_endpoint

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
            "/logout",
            self.logout,
            methods=["GET"],
            include_in_schema=False,
        )

        self.session_serializer = URLSafeTimedSerializer(session_secret)
        self.session_timeout_secs = session_timeout_secs
        # Separate salt so a leaked/forged state token can't be replayed as a
        # session token (or vice versa) even though both share session_secret.
        self.state_serializer = URLSafeTimedSerializer(
            session_secret, salt="oidc-state"
        )

    @classmethod
    async def create(
        cls,
        *,
        issuer: str,
        client_id: str,
        client_secret: str,
        session_secret: str,
        session_timeout_secs: int,
        scope: str = "openid email profile",
        enforce_https: bool = True,
        user_model: type[UserModel],
    ) -> OpenIDConnect[UserModel]:
        async with httpx2.AsyncClient() as client:
            res = await client.get(
                issuer.rstrip("/") + "/.well-known/openid-configuration", timeout=5
            )
        res.raise_for_status()
        endpoints: dict[str, str] = res.json()

        return cls(
            issuer=issuer,
            client_id=client_id,
            client_secret=client_secret,
            session_secret=session_secret,
            session_timeout_secs=session_timeout_secs,
            authorization_endpoint=endpoints["authorization_endpoint"],
            token_endpoint=endpoints["token_endpoint"],
            userinfo_endpoint=endpoints["userinfo_endpoint"],
            scope=scope,
            enforce_https=enforce_https,
            user_model=user_model,
        )

    async def __call__(self, request: Request) -> UserModel:
        next_url = request.url.path
        if request.url.query:
            next_url += f"?{request.url.query}"
        enforce_login = HTTPException(
            status_code=307,
            detail="Not authenticated",
            headers={
                "Location": str(request.url_for("login"))
                + f"?next_url={quote(next_url)}"
            },
        )
        session_token = request.cookies.get("session")
        if session_token:
            # already authenticated
            try:
                access_token = self.session_serializer.loads(
                    session_token, max_age=self.session_timeout_secs
                )
                return self.get_user_info(access_token)
            except Exception:
                log.exception("Access token cannot be loaded or is outdated")
                raise enforce_login from None

        raise enforce_login

    def login(self, request: Request, next_url: str = "") -> Response:
        safe_next_url = next_url if _is_safe_next_url(next_url) else "/"
        state_token = self.state_serializer.dumps({
            "nonce": secrets.token_urlsafe(16),
            "next_url": safe_next_url,
        })
        auth_url = (
            f"{self.authorization_endpoint}?response_type=code"
            f"&scope={quote(self.scope)}"
            f"&client_id={quote(self.client_id)}"
            f"&redirect_uri={quote(str(request.url_for('callback')), safe='')}"
            f"&state={quote(state_token)}"
        )
        response = RedirectResponse(auth_url)
        # Double-submit cookie: callback() only accepts a state that matches
        # this cookie, binding the callback to the browser that started this
        # specific login (RFC 6749 section 10.12 login-CSRF protection).
        response.set_cookie(
            key="oidc_state",
            value=state_token,
            secure=self.enforce_https,
            httponly=True,
            samesite="lax",
            max_age=OIDC_STATE_MAX_AGE_SECS,
        )
        return response

    async def callback(self, request: Request, code: str, state: str) -> Response:
        """Keycloak callback."""
        state_cookie = request.cookies.get("oidc_state")
        if not state_cookie or state_cookie != state:
            raise HTTPException(status_code=400, detail="Invalid or missing state")
        try:
            state_data = self.state_serializer.loads(
                state, max_age=OIDC_STATE_MAX_AGE_SECS
            )
        except Exception as e:
            raise HTTPException(
                status_code=400, detail="Invalid or expired state"
            ) from e

        next_url = state_data.get("next_url", "/")
        if not _is_safe_next_url(next_url):
            next_url = "/"

        async with httpx2.AsyncClient() as client:
            token_response = await client.post(
                self.token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": str(request.url_for("callback")),
                },
                auth=(self.client_id, self.client_secret),
            )

        if not httpx2.codes.is_success(token_response.status_code):
            raise HTTPException(status_code=400, detail="Token request failed")

        token_data = token_response.json()
        session_token = self.session_serializer.dumps(token_data["access_token"])
        response = RedirectResponse(url=next_url)
        response.delete_cookie("oidc_state")
        response.set_cookie(
            key="session",
            value=session_token,
            secure=self.enforce_https,
            httponly=True,
            samesite="lax",
            expires=self.session_timeout_secs,
        )
        return response

    @staticmethod
    def logout() -> Response:
        response = RedirectResponse(url="/")
        response.delete_cookie("session")
        return response

    def get_user_info(self, access_token: str) -> UserModel:
        # Check against the userinfo endpoint
        response = httpx2.get(
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

    async def query_opa(
        self, user: UserModel, obj: str, params: dict[str, str]
    ) -> dict:
        """Query OPA data endpoint for authorization and other decisions."""
        data = {"input": user.dump().model_dump()}
        data["input"]["obj"] = obj
        data["input"]["params"] = params

        async with httpx2.AsyncClient() as client:
            opa_decision = await client.post(f"{self.opa_url}", json=data, timeout=5)

        if opa_decision.status_code != status.HTTP_200_OK:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"OPA returned unexpected http status code: {opa_decision.status_code}",
            )

        try:
            return opa_decision.json().get("result")
        except JSONDecodeError as e:
            log.exception("Unable to decode OPA response.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OPA returned unexpected result",
            ) from e

    @staticmethod
    def user_is_authorized(opa_data: dict[str, Any]) -> None:
        """Check if user is authorized to access endpoint."""
        if not opa_data.get("authorized"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized"
            )

    @staticmethod
    def user_is_within_rate_limits(opa_data: dict[str, Any]) -> None:
        """Check if user is still in the rate limits."""
        if not opa_data.get("within_rate_limits"):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Action rate limit exceeded!",
            )

    async def __call__(
        self,
        request: Request,
        user: UserModel,
        extra_params: dict[str, str] | None = None,
    ) -> None:
        # allow endpoints without authorization
        if self.should_skip_endpoint(request.url.path):
            return

        # check if user is authorized to access endpoint
        params = request.path_params.copy()
        params.update(request.query_params)
        if extra_params:
            params.update(extra_params)
        opa_data = await self.query_opa(
            user, obj=request["route"].operation_id, params=params
        )
        self.user_is_authorized(opa_data)
        self.user_is_within_rate_limits(opa_data)
        user.set_allowed_actions(allowed_actions=opa_data.get("objects", []))


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
