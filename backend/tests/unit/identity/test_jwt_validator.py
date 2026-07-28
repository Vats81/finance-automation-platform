import base64
import json

import pytest

from app.config.settings import Settings
from app.identity.domain.exceptions import InvalidTokenException
from app.identity.infrastructure.entra.jwks_cache import JwksCache
from app.identity.infrastructure.entra.jwt_validator import EntraJwtValidator


def make_dev_token(**claims: str) -> str:
    payload = {"oid": "oid-1", "email": "dev@example.com", "name": "Dev User", **claims}
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"dev.{encoded}"


def make_validator(*, auth_dev_mode: bool = True, app_env: str = "local") -> EntraJwtValidator:
    settings = Settings(_env_file=None, APP_ENV=app_env, AUTH_DEV_MODE=auth_dev_mode)
    return EntraJwtValidator(settings, JwksCache(settings.redis_url, settings.entra_jwks_uri))


async def test_dev_token_is_accepted_in_local_dev_mode() -> None:
    validator = make_validator()
    token = make_dev_token()

    claims = await validator.validate(token)

    assert claims.entra_object_id == "oid-1"
    assert claims.email == "dev@example.com"
    assert claims.display_name == "Dev User"


async def test_malformed_dev_token_raises_invalid_token() -> None:
    validator = make_validator()

    with pytest.raises(InvalidTokenException):
        await validator.validate("dev.not-valid-base64-json!!!")


def test_settings_reject_dev_mode_outside_local() -> None:
    with pytest.raises(ValueError):
        Settings(_env_file=None, APP_ENV="production", AUTH_DEV_MODE=True)
