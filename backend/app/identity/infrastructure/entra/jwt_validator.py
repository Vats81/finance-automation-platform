import base64
import json
import logging
from dataclasses import dataclass

from jose import JWTError, jwt

from app.config.settings import Settings
from app.identity.domain.exceptions import InvalidTokenException
from app.identity.infrastructure.entra.jwks_cache import JwksCache

logger = logging.getLogger(__name__)

_DEV_TOKEN_PREFIX = "dev."


@dataclass(frozen=True)
class EntraClaims:
    entra_object_id: str
    email: str
    display_name: str


class EntraJwtValidator:
    """Validates bearer JWTs issued by Microsoft Entra ID against its JWKS.

    FastAPI is a pure OAuth2 resource server: it never initiates the
    interactive login/redirect flow (that happens in the Next.js frontend
    via MSAL.js) — it only verifies a token that arrives on `Authorization:
    Bearer <token>` and extracts the `oid`/`email`/`name` claims used for
    JIT user provisioning.

    In local development (`AUTH_DEV_MODE=true`, only permitted when
    `APP_ENV=local`), a `dev.<base64-json>` token format is accepted without
    signature verification, so the platform is runnable end-to-end without a
    real Entra tenant registration. This path is refused outside `local`.
    """

    def __init__(self, settings: Settings, jwks_cache: JwksCache) -> None:
        self._settings = settings
        self._jwks_cache = jwks_cache

    async def validate(self, token: str) -> EntraClaims:
        if self._settings.auth_dev_mode and self._settings.is_local and token.startswith(_DEV_TOKEN_PREFIX):
            return self._validate_dev_token(token)
        return await self._validate_entra_token(token)

    def _validate_dev_token(self, token: str) -> EntraClaims:
        try:
            encoded = token[len(_DEV_TOKEN_PREFIX) :]
            padded = encoded + "=" * (-len(encoded) % 4)
            claims = json.loads(base64.urlsafe_b64decode(padded))
            return EntraClaims(
                entra_object_id=claims["oid"],
                email=claims["email"],
                display_name=claims.get("name", claims["email"]),
            )
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            raise InvalidTokenException("Malformed dev-mode token") from exc

    async def _validate_entra_token(self, token: str) -> EntraClaims:
        try:
            jwks = await self._jwks_cache.get_jwks()
            unverified_header = jwt.get_unverified_header(token)
            key = next((k for k in jwks["keys"] if k["kid"] == unverified_header.get("kid")), None)
            if key is None:
                raise InvalidTokenException("No matching JWKS key for token")

            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self._settings.entra_api_client_id,
                issuer=self._settings.entra_issuer,
            )
            return EntraClaims(
                entra_object_id=claims["oid"],
                email=claims.get("email") or claims.get("preferred_username", ""),
                display_name=claims.get("name", ""),
            )
        except JWTError as exc:
            logger.warning("JWT validation failed: %s", exc)
            raise InvalidTokenException("Invalid or expired token") from exc
        except KeyError as exc:
            raise InvalidTokenException(f"Token missing required claim: {exc}") from exc
