import uuid

from jose import JWTError, jwt

from app.config.settings import Settings
from app.identity.domain.exceptions import InvalidTokenException


class LocalTokenValidator:
    """Validates platform-issued bearer JWTs (see token_issuer.py) and
    returns the carried user id. Used exclusively by the SMB Finance
    Manager product's `get_current_local_user` dependency — the
    AP-automation product's `get_current_user`/EntraJwtValidator path is
    untouched.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def validate(self, token: str) -> uuid.UUID:
        try:
            claims = jwt.decode(token, self._settings.jwt_secret_key, algorithms=["HS256"])
            return uuid.UUID(claims["sub"])
        except (JWTError, KeyError, ValueError) as exc:
            raise InvalidTokenException("Invalid or expired token") from exc
