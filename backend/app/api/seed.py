from fastapi import APIRouter, Depends, HTTPException

from app.bootstrap.container import get_clock, get_container, get_password_hasher
from app.config.settings import Settings, get_settings
from app.shared.application.ports import IClock, IPasswordHasher
from app.shared.application.seed_demo_data import run_seed

router = APIRouter(tags=["internal"])


@router.get("/internal/seed-demo-users")
async def seed_demo_users(
    secret: str,
    settings: Settings = Depends(get_settings),
    password_hasher: IPasswordHasher = Depends(get_password_hasher),
    clock: IClock = Depends(get_clock),
) -> dict[str, list[str]]:
    """One-time endpoint for creating the demo/test accounts on hosts with
    no shell access (e.g. Render's free tier). Disabled by default — only
    reachable once SEED_SECRET is set to a non-empty value, and only with
    the matching secret. Safe to leave deployed: idempotent, and trivial to
    lock back down by blanking SEED_SECRET again.
    """
    if not settings.seed_secret or secret != settings.seed_secret:
        raise HTTPException(status_code=403, detail="Invalid or missing secret")

    container = get_container()
    return await run_seed(container.session_factory, password_hasher, clock)
