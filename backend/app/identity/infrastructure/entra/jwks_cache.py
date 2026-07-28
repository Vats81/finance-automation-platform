import json
import logging

import httpx
import redis.asyncio as redis

logger = logging.getLogger(__name__)

_CACHE_KEY = "entra:jwks"
_CACHE_TTL_SECONDS = 24 * 60 * 60


class JwksCache:
    """Redis-backed cache for Entra ID's JWKS document, so every request
    doesn't round-trip to login.microsoftonline.com to validate a token.
    """

    def __init__(self, redis_url: str, jwks_uri: str) -> None:
        self._redis_url = redis_url
        self._jwks_uri = jwks_uri

    async def get_jwks(self) -> dict:
        client = redis.from_url(self._redis_url)
        try:
            cached = await client.get(_CACHE_KEY)
            if cached:
                return json.loads(cached)

            async with httpx.AsyncClient(timeout=5.0) as http_client:
                response = await http_client.get(self._jwks_uri)
                response.raise_for_status()
                jwks = response.json()

            await client.set(_CACHE_KEY, json.dumps(jwks), ex=_CACHE_TTL_SECONDS)
            return jwks
        finally:
            await client.aclose()
