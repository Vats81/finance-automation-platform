from fastapi import APIRouter, Depends

from app.config.settings import Settings, get_settings
from app.identity.api.dependencies import get_current_local_user
from app.identity.domain.entities import User
from app.integrations.api.schemas import IntegrationsStatusResponse
from app.integrations.application.queries.get_integration_status import GetIntegrationStatusUseCase

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("/status", response_model=IntegrationsStatusResponse)
async def get_integrations_status(
    _actor: User = Depends(get_current_local_user),
    settings: Settings = Depends(get_settings),
) -> IntegrationsStatusResponse:
    status = GetIntegrationStatusUseCase(settings).execute()
    return IntegrationsStatusResponse.from_domain(status)
