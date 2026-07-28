import uuid
from datetime import datetime, timedelta, timezone

from jose import jwt

from app.config.settings import Settings


class LocalTokenIssuer:
    """Mints platform-issued bearer JWTs for self-serve (LOCAL) auth users —
    the SMB Finance Manager product's own login, as opposed to Entra ID's
    tokens which EntraJwtValidator validates for the AP-automation product.
    HS256 with a server-side secret (settings.jwt_secret_key); reuses
    python-jose, already a dependency for Entra JWKS validation.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def issue(self, *, user_id: uuid.UUID) -> tuple[str, datetime]:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=self._settings.jwt_access_token_ttl_days)
        claims = {"sub": str(user_id), "iat": now, "exp": expires_at}
        token = jwt.encode(claims, self._settings.jwt_secret_key, algorithm="HS256")
        return token, expires_at
