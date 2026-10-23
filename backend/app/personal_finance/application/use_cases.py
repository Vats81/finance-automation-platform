"""Personal workspaces: income, budgets, and the monthly money view.

Spending is not stored here: it is the workspace's ordinary expenses, so the
receipt/bill scanner, CSV import and backups all work for personal use unchanged.
Cross-context (expenses + income + budgets), so it takes the concrete AppUnitOfWork.
"""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.domain.entities import Business
from app.business.domain.exceptions import BusinessNotFoundException
from app.business.domain.value_objects import BusinessKind
from app.expenses.domain.value_objects import ExpenseStatus
from app.personal_finance.application.ports import BudgetRecord, IncomeRecord
from app.personal_finance.domain import rules
from app.personal_finance.domain.exceptions import (
    BudgetNotFoundException,
    IncomeAlreadyVoidException,
    IncomeNotFoundException,
    PersonalWorkspaceRequiredException,
)

_ZERO = Decimal("0.00")
_SCAN_LIMIT = 10_000


async def require_personal(uow: AppUnitOfWork, business_id: uuid.UUID) -> Business:
    business = await uow.businesses.get_by_id(business_id)
    if business is None:
        raise BusinessNotFoundException(f"Business {business_id} not found")
    if business.kind != BusinessKind.PERSONAL:
        raise PersonalWorkspaceRequiredException(
            "Income and budgets are for personal workspaces. A business records sales and expenses instead."
        )
    return business


# ------------------------------------------------------------------ income


async def record_income(
    uow: AppUnitOfWork,
    *,
    business_id: uuid.UUID,
    income_date: date,
    source: str,
    category: str,
    amount: Decimal,
    notes: str | None,
) -> IncomeRecord:
    await require_personal(uow, business_id)
    record = await uow.personal.add_income(
        business_id=business_id,
        income_date=income_date,
        source=rules.clean_text(source, field="Source", max_length=200) or "",
        category=rules.clean_text(category, field="Category", max_length=100) or "",
        amount=rules.positive_amount(amount, field="Amount"),
        notes=rules.clean_text(notes, field="Notes", max_length=2000, required=False),
    )
    await uow.commit()
    return record


async def list_income(
    uow: AppUnitOfWork, *, business_id: uuid.UUID, offset: int, limit: int
) -> tuple[list[IncomeRecord], int]:
    await require_personal(uow, business_id)
    return await uow.personal.list_incomes(business_id, offset=offset, limit=limit)


async def void_income(uow: AppUnitOfWork, *, business_id: uuid.UUID, income_id: uuid.UUID) -> IncomeRecord:
    await require_personal(uow, business_id)
    current = await uow.personal.get_income(business_id, income_id)
    if current is None:
        raise IncomeNotFoundException(f"Income {income_id} not found")
    if current.status == "void":
        raise IncomeAlreadyVoidException("This income is already void.")
    voided = await uow.personal.void_income(business_id, income_id)
    assert voided is not None
    await uow.commit()
    return voided


# ----------------------------------------------------------------- budgets


async def set_budget(
    uow: AppUnitOfWork, *, business_id: uuid.UUID, category: str, monthly_limit: Decimal
) -> BudgetRecord:
    await require_personal(uow, business_id)
    cleaned = rules.clean_text(category, field="Category", max_length=100) or ""
    budget = await uow.personal.upsert_budget(
        business_id=business_id,
        category=cleaned,
        category_key=rules.category_key(cleaned),
        monthly_limit=rules.positive_amount(monthly_limit, field="Monthly limit"),
    )
    await uow.commit()
    return budget


async def remove_budget(uow: AppUnitOfWork, *, business_id: uuid.UUID, budget_id: uuid.UUID) -> None:
    await require_personal(uow, business_id)
    if not await uow.personal.delete_budget(business_id, budget_id):
        raise BudgetNotFoundException(f"Budget {budget_id} not found")
    await uow.commit()


# ----------------------------------------------------------------- summary


@dataclass(frozen=True)
class CategorySpend:
    category: str
    amount: Decimal
    share: Decimal  # of total spending, 0-1


@dataclass(frozen=True)
class BudgetProgress:
    budget: BudgetRecord
    spent: Decimal
    remaining: Decimal
    percent_used: Decimal
    status: str  # ok | near | over


@dataclass(frozen=True)
class PersonalSummary:
    period_start: date
    period_end: date
    income: Decimal
    spending: Decimal
    saved: Decimal
    savings_rate: Decimal | None
    spending_by_category: list[CategorySpend]
    budgets: list[BudgetProgress]


async def personal_summary(
    uow: AppUnitOfWork, *, business_id: uuid.UUID, year: int, month: int
) -> PersonalSummary:
    await require_personal(uow, business_id)
    start, end = rules.month_bounds(year, month)

    income = sum((i.amount for i in await uow.personal.list_incomes_between(business_id, start, end)), _ZERO)

    expenses, _ = await uow.expenses.list_for_business(business_id, offset=0, limit=_SCAN_LIMIT)
    by_key: dict[str, tuple[str, Decimal]] = {}
    for expense in expenses:
        if expense.status == ExpenseStatus.VOID or not (start <= expense.expense_date <= end):
            continue
        key = rules.category_key(expense.category)
        label, running = by_key.get(key, (" ".join(expense.category.split()), _ZERO))
        by_key[key] = (label, running + expense.total_amount.amount)
    spending = sum((amount for _, amount in by_key.values()), _ZERO)

    categories = [
        CategorySpend(
            category=label,
            amount=amount,
            share=(amount / spending).quantize(Decimal("0.0001")) if spending > 0 else _ZERO,
        )
        for label, amount in sorted(by_key.values(), key=lambda item: item[1], reverse=True)
    ]

    progress: list[BudgetProgress] = []
    for budget in await uow.personal.list_budgets(business_id):
        spent = by_key.get(rules.category_key(budget.category), ("", _ZERO))[1]
        progress.append(
            BudgetProgress(
                budget=budget,
                spent=spent,
                remaining=budget.monthly_limit - spent,
                percent_used=(spent / budget.monthly_limit * 100).quantize(Decimal("0.1")),
                status=rules.budget_status(spent, budget.monthly_limit),
            )
        )

    saved = income - spending
    return PersonalSummary(
        period_start=start,
        period_end=end,
        income=income.quantize(Decimal("0.01")),
        spending=spending.quantize(Decimal("0.01")),
        saved=saved.quantize(Decimal("0.01")),
        savings_rate=(saved / income).quantize(Decimal("0.0001")) if income > 0 else None,
        spending_by_category=categories,
        budgets=progress,
    )
