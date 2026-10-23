import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from app.api.rate_limit import limiter
from app.bootstrap.container import get_uow
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.api.dependencies import require_business_role
from app.business.api.permissions import ANY_MEMBER, CAN_WRITE
from app.config.settings import get_settings
from app.identity.domain.entities import User
from app.personal_finance.application import use_cases
from app.personal_finance.application.ports import BudgetRecord, IncomeRecord

router = APIRouter(prefix="/businesses/{business_id}", tags=["personal-finance"])
settings = get_settings()


class RecordIncomeRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    income_date: date
    source: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=100)
    amount: Decimal = Field(gt=0)
    notes: str | None = Field(default=None, max_length=2000)


class IncomeResponse(BaseModel):
    id: uuid.UUID
    income_date: date
    source: str
    category: str
    amount: Decimal
    notes: str | None
    status: str
    created_at: datetime

    @classmethod
    def build(cls, r: IncomeRecord) -> "IncomeResponse":
        return cls(
            id=r.id,
            income_date=r.income_date,
            source=r.source,
            category=r.category,
            amount=r.amount,
            notes=r.notes,
            status=r.status,
            created_at=r.created_at,
        )


class PagedIncomeResponse(BaseModel):
    items: list[IncomeResponse]
    total: int
    offset: int
    limit: int


class SetBudgetRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    category: str = Field(min_length=1, max_length=100)
    monthly_limit: Decimal = Field(gt=0)


class BudgetResponse(BaseModel):
    id: uuid.UUID
    category: str
    monthly_limit: Decimal

    @classmethod
    def build(cls, b: BudgetRecord) -> "BudgetResponse":
        return cls(id=b.id, category=b.category, monthly_limit=b.monthly_limit)


class CategorySpendResponse(BaseModel):
    category: str
    amount: Decimal
    share: Decimal


class BudgetProgressResponse(BaseModel):
    id: uuid.UUID
    category: str
    monthly_limit: Decimal
    spent: Decimal
    remaining: Decimal
    percent_used: Decimal
    status: str


class PersonalSummaryResponse(BaseModel):
    period_start: date
    period_end: date
    income: Decimal
    spending: Decimal
    saved: Decimal
    savings_rate: Decimal | None
    spending_by_category: list[CategorySpendResponse]
    budgets: list[BudgetProgressResponse]


@router.post("/incomes", response_model=IncomeResponse, status_code=201)
@limiter.limit(settings.rate_limit_write)
async def record_income(
    request: Request,
    business_id: uuid.UUID,
    body: RecordIncomeRequest,
    _actor: User = Depends(require_business_role(*CAN_WRITE)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> IncomeResponse:
    record = await use_cases.record_income(
        uow,
        business_id=business_id,
        income_date=body.income_date,
        source=body.source,
        category=body.category,
        amount=body.amount,
        notes=body.notes,
    )
    return IncomeResponse.build(record)


@router.get("/incomes", response_model=PagedIncomeResponse)
async def list_income(
    business_id: uuid.UUID,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    _actor: User = Depends(require_business_role(*ANY_MEMBER)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> PagedIncomeResponse:
    items, total = await use_cases.list_income(uow, business_id=business_id, offset=offset, limit=limit)
    return PagedIncomeResponse(
        items=[IncomeResponse.build(i) for i in items], total=total, offset=offset, limit=limit
    )


@router.post("/incomes/{income_id}/void", response_model=IncomeResponse)
@limiter.limit(settings.rate_limit_write)
async def void_income(
    request: Request,
    business_id: uuid.UUID,
    income_id: uuid.UUID,
    _actor: User = Depends(require_business_role(*CAN_WRITE)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> IncomeResponse:
    return IncomeResponse.build(
        await use_cases.void_income(uow, business_id=business_id, income_id=income_id)
    )


@router.get("/budgets", response_model=list[BudgetResponse])
async def list_budgets(
    business_id: uuid.UUID,
    _actor: User = Depends(require_business_role(*ANY_MEMBER)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> list[BudgetResponse]:
    await use_cases.require_personal(uow, business_id)
    return [BudgetResponse.build(b) for b in await uow.personal.list_budgets(business_id)]


@router.put("/budgets", response_model=BudgetResponse)
@limiter.limit(settings.rate_limit_write)
async def set_budget(
    request: Request,
    business_id: uuid.UUID,
    body: SetBudgetRequest,
    _actor: User = Depends(require_business_role(*CAN_WRITE)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> BudgetResponse:
    """Creates the budget for a category, or updates its monthly limit."""
    return BudgetResponse.build(
        await use_cases.set_budget(
            uow, business_id=business_id, category=body.category, monthly_limit=body.monthly_limit
        )
    )


@router.delete("/budgets/{budget_id}", status_code=204)
@limiter.limit(settings.rate_limit_write)
async def remove_budget(
    request: Request,
    business_id: uuid.UUID,
    budget_id: uuid.UUID,
    _actor: User = Depends(require_business_role(*CAN_WRITE)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> Response:
    await use_cases.remove_budget(uow, business_id=business_id, budget_id=budget_id)
    return Response(status_code=204)


@router.get("/personal/summary", response_model=PersonalSummaryResponse)
async def personal_summary(
    business_id: uuid.UUID,
    year: int | None = Query(default=None, ge=2000, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
    _actor: User = Depends(require_business_role(*ANY_MEMBER)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> PersonalSummaryResponse:
    """One month of income, spending, what was saved, where the money went and how each
    budget is doing. Defaults to the current month.
    """
    today = datetime.now(timezone.utc).date()
    summary = await use_cases.personal_summary(
        uow, business_id=business_id, year=year or today.year, month=month or today.month
    )
    return PersonalSummaryResponse(
        period_start=summary.period_start,
        period_end=summary.period_end,
        income=summary.income,
        spending=summary.spending,
        saved=summary.saved,
        savings_rate=summary.savings_rate,
        spending_by_category=[
            CategorySpendResponse(category=c.category, amount=c.amount, share=c.share)
            for c in summary.spending_by_category
        ],
        budgets=[
            BudgetProgressResponse(
                id=b.budget.id,
                category=b.budget.category,
                monthly_limit=b.budget.monthly_limit,
                spent=b.spent,
                remaining=b.remaining,
                percent_used=b.percent_used,
                status=b.status,
            )
            for b in summary.budgets
        ],
    )
