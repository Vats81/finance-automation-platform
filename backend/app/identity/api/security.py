from fastapi.security import HTTPBearer

# `auto_error=True` makes FastAPI itself return 403 when the Authorization
# header is missing entirely; malformed/invalid *tokens* are handled by
# EntraJwtValidator and surface as our 401 InvalidTokenException instead.
bearer_scheme = HTTPBearer(auto_error=True)
