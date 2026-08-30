import uuid

from fastapi import APIRouter, Depends, Request

from app.api.rate_limit import limiter
from app.bootstrap.container import get_uow
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.api.dependencies import require_business_role
from app.business.api.schemas import (
    BusinessResponse,
    ChangePlanRequest,
    CompleteOnboardingRequest,
    MyBusinessResponse,
    RegisterBusinessRequest,
)
from app.business.application.commands.change_business_plan import (
    ChangeBusinessPlanCommand,
    ChangeBusinessPlanUseCase,
)
from app.business.application.commands.complete_onboarding import (
    CompleteOnboardingCommand,
    CompleteOnboardingUseCase,
)
from app.business.application.commands.register_business import (
    RegisterBusinessCommand,
    RegisterBusinessUseCase,
)
from app.business.application.queries.get_business import GetBusinessQuery, GetBusinessUseCase
from app.business.application.queries.list_my_businesses import (
    ListMyBusinessesQuery,
    ListMyBusinessesUseCase,
)
from app.business.domain.value_objects import BusinessRole
from app.config.settings import get_settings
from app.identity.api.dependencies import get_current_local_user
from app.identity.domain.entities import User

router = APIRouter(prefix="/businesses", tags=["business"])

settings = get_settings()


@router.post("", response_model=BusinessResponse, status_code=201)
@limiter.limit(settings.rate_limit_write)
async def register_business(
    request: Request,
    body: RegisterBusinessRequest,
    actor: User = Depends(get_current_local_user),
    uow: AppUnitOfWork = Depends(get_uow),
) -> BusinessResponse:
    use_case = RegisterBusinessUseCase(uow)
    business = await use_case.execute(RegisterBusinessCommand(owner_user_id=actor.id, name=body.name))
    return BusinessResponse.from_domain(business)


@router.get("", response_model=list[MyBusinessResponse])
async def list_my_businesses(
    actor: User = Depends(get_current_local_user),
    uow: AppUnitOfWork = Depends(get_uow),
) -> list[MyBusinessResponse]:
    use_case = ListMyBusinessesUseCase(uow)
    views = await use_case.execute(ListMyBusinessesQuery(user_id=actor.id))
    return [MyBusinessResponse.from_domain(v) for v in views]


@router.get("/{business_id}", response_model=BusinessResponse)
async def get_business(
    business_id: uuid.UUID,
    _actor: User = Depends(require_business_role()),
    uow: AppUnitOfWork = Depends(get_uow),
) -> BusinessResponse:
    use_case = GetBusinessUseCase(uow)
    business = await use_case.execute(GetBusinessQuery(business_id=business_id))
    return BusinessResponse.from_domain(business)


@router.patch("/{business_id}/onboarding", response_model=BusinessResponse)
@limiter.limit(settings.rate_limit_write)
async def complete_onboarding(
    request: Request,
    business_id: uuid.UUID,
    body: CompleteOnboardingRequest,
    _actor: User = Depends(require_business_role(BusinessRole.OWNER, BusinessRole.ADMIN)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> BusinessResponse:
    use_case = CompleteOnboardingUseCase(uow)
    business = await use_case.execute(
        CompleteOnboardingCommand(
            business_id=business_id,
            business_type=body.business_type,
            industry=body.industry,
            country=body.country,
            currency=body.currency,
            financial_year_start_month=body.financial_year_start_month,
            gst_registered=body.gst_registered,
            business_size=body.business_size,
            number_of_branches=body.number_of_branches,
            whatsapp_number=body.whatsapp_number,
            contact_email=body.contact_email,
        )
    )
    return BusinessResponse.from_domain(business)


@router.patch("/{business_id}/plan", response_model=BusinessResponse)
@limiter.limit(settings.rate_limit_write)
async def change_business_plan(
    request: Request,
    business_id: uuid.UUID,
    body: ChangePlanRequest,
    _actor: User = Depends(require_business_role(BusinessRole.OWNER)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> BusinessResponse:
    use_case = ChangeBusinessPlanUseCase(uow, settings)
    business = await use_case.execute(ChangeBusinessPlanCommand(business_id=business_id, plan=body.plan))
    return BusinessResponse.from_domain(business)
