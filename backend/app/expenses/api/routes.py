import uuid

from fastapi import APIRouter, Depends, Request, UploadFile

from app.api.rate_limit import limiter
from app.bootstrap.container import get_ai_client, get_uow
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.api.dependencies import require_business_role
from app.business.domain.value_objects import BusinessRole
from app.config.settings import get_settings
from app.expenses.api.schemas import (
    CreateExpenseRequest,
    ExpenseResponse,
    PagedExpensesResponse,
    ScannedReceiptResponse,
    UpdateExpenseRequest,
)
from app.expenses.application.commands.create_expense import CreateExpenseCommand, CreateExpenseUseCase
from app.expenses.application.commands.update_expense import UpdateExpenseCommand, UpdateExpenseUseCase
from app.expenses.application.commands.void_expense import VoidExpenseCommand, VoidExpenseUseCase
from app.expenses.application.queries.get_expense import GetExpenseQuery, GetExpenseUseCase
from app.expenses.application.queries.list_expenses import ListExpensesQuery, ListExpensesUseCase
from app.expenses.application.scan_receipt import ScanReceiptCommand, ScanReceiptUseCase
from app.identity.domain.entities import User
from app.shared.application.pagination import PageRequest
from app.shared.application.ports import IAiClient

router = APIRouter(prefix="/businesses/{business_id}/expenses", tags=["expenses"])

settings = get_settings()

_can_write = (BusinessRole.OWNER, BusinessRole.ADMIN, BusinessRole.ACCOUNTANT)


@router.post("", response_model=ExpenseResponse, status_code=201)
@limiter.limit(settings.rate_limit_write)
async def create_expense(
    request: Request,
    business_id: uuid.UUID,
    body: CreateExpenseRequest,
    _actor: User = Depends(require_business_role(*_can_write)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> ExpenseResponse:
    use_case = CreateExpenseUseCase(uow)
    expense = await use_case.execute(
        CreateExpenseCommand(
            business_id=business_id,
            expense_date=body.expense_date,
            category=body.category,
            description=body.description,
            amount=body.amount,
            payment_method=body.payment_method,
            vendor_id=body.vendor_id,
            tax=body.tax,
            is_recurring=body.is_recurring,
            notes=body.notes,
        )
    )
    return ExpenseResponse.from_domain(expense)


@router.post("/scan-receipt", response_model=ScannedReceiptResponse)
@limiter.limit(settings.rate_limit_write)
async def scan_receipt(
    request: Request,
    business_id: uuid.UUID,
    file: UploadFile,
    _actor: User = Depends(require_business_role(*_can_write)),
    ai_client: IAiClient = Depends(get_ai_client),
) -> ScannedReceiptResponse:
    content = await file.read()
    use_case = ScanReceiptUseCase(ai_client)
    data = await use_case.execute(
        ScanReceiptCommand(content_type=file.content_type or "", image_bytes=content)
    )
    return ScannedReceiptResponse.from_domain(data)


@router.get("", response_model=PagedExpensesResponse)
async def list_expenses(
    business_id: uuid.UUID,
    offset: int = 0,
    limit: int = 50,
    _actor: User = Depends(require_business_role()),
    uow: AppUnitOfWork = Depends(get_uow),
) -> PagedExpensesResponse:
    use_case = ListExpensesUseCase(uow)
    page = await use_case.execute(
        ListExpensesQuery(business_id=business_id, page=PageRequest(offset=offset, limit=limit))
    )
    return PagedExpensesResponse(
        items=[ExpenseResponse.from_domain(e) for e in page.items],
        total=page.total,
        offset=page.offset,
        limit=page.limit,
    )


@router.get("/{expense_id}", response_model=ExpenseResponse)
async def get_expense(
    business_id: uuid.UUID,
    expense_id: uuid.UUID,
    _actor: User = Depends(require_business_role()),
    uow: AppUnitOfWork = Depends(get_uow),
) -> ExpenseResponse:
    use_case = GetExpenseUseCase(uow)
    expense = await use_case.execute(GetExpenseQuery(business_id=business_id, expense_id=expense_id))
    return ExpenseResponse.from_domain(expense)


@router.patch("/{expense_id}", response_model=ExpenseResponse)
@limiter.limit(settings.rate_limit_write)
async def update_expense(
    request: Request,
    business_id: uuid.UUID,
    expense_id: uuid.UUID,
    body: UpdateExpenseRequest,
    _actor: User = Depends(require_business_role(*_can_write)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> ExpenseResponse:
    use_case = UpdateExpenseUseCase(uow)
    expense = await use_case.execute(
        UpdateExpenseCommand(
            business_id=business_id,
            expense_id=expense_id,
            category=body.category,
            description=body.description,
            amount=body.amount,
            tax=body.tax,
            payment_method=body.payment_method,
            is_recurring=body.is_recurring,
            notes=body.notes,
        )
    )
    return ExpenseResponse.from_domain(expense)


@router.post("/{expense_id}/void", response_model=ExpenseResponse)
@limiter.limit(settings.rate_limit_write)
async def void_expense(
    request: Request,
    business_id: uuid.UUID,
    expense_id: uuid.UUID,
    _actor: User = Depends(require_business_role(*_can_write)),
    uow: AppUnitOfWork = Depends(get_uow),
) -> ExpenseResponse:
    use_case = VoidExpenseUseCase(uow)
    expense = await use_case.execute(VoidExpenseCommand(business_id=business_id, expense_id=expense_id))
    return ExpenseResponse.from_domain(expense)
