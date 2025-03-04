from automated_actions.api.models import User
from automated_actions.auth import OpenIDConnect
from automated_actions.config import settings

oidc = OpenIDConnect[User](
    issuer=settings.oidc_issuer,
    client_id=settings.oidc_client_id,
    client_secret=settings.oidc_client_secret,
    session_secret=settings.session_secret,
    enforce_https=not settings.debug,
    user_model=User,
)
