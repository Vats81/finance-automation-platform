import uuid

from fastapi import APIRouter, Depends

from app.ai_assistant.api.schemas import AskAssistantRequest, AskAssistantResponse, InsightsResponse
from app.ai_assistant.application.ask_assistant import AskAssistantCommand, AskAssistantUseCase
from app.ai_assistant.application.generate_insights import GenerateInsightsCommand, GenerateInsightsUseCase
from app.bootstrap.container import get_ai_client, get_clock, get_uow
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.api.dependencies import require_business_role
from app.identity.domain.entities import User
from app.shared.application.ports import IAiClient, IClock

router = APIRouter(prefix="/businesses/{business_id}/ai-assistant", tags=["ai-assistant"])


@router.post("/ask", response_model=AskAssistantResponse)
async def ask_assistant(
    business_id: uuid.UUID,
    body: AskAssistantRequest,
    # Read-only despite being a POST — a JSON body is needed for the
    # question/history, but no business data is mutated, so any active
    # member may ask (same reasoning as the GET dashboard endpoints).
    _actor: User = Depends(require_business_role()),
    uow: AppUnitOfWork = Depends(get_uow),
    ai_client: IAiClient = Depends(get_ai_client),
) -> AskAssistantResponse:
    result = await AskAssistantUseCase(uow, ai_client).execute(
        AskAssistantCommand(business_id=business_id, question=body.question, history=body.history)
    )
    return AskAssistantResponse.from_domain(result)


@router.get("/insights", response_model=InsightsResponse)
async def get_insights(
    business_id: uuid.UUID,
    _actor: User = Depends(require_business_role()),
    uow: AppUnitOfWork = Depends(get_uow),
    ai_client: IAiClient = Depends(get_ai_client),
    clock: IClock = Depends(get_clock),
) -> InsightsResponse:
    result = await GenerateInsightsUseCase(uow, ai_client, clock).execute(
        GenerateInsightsCommand(business_id=business_id)
    )
    return InsightsResponse.from_domain(result)
