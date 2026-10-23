"""Small pure rules for personal workspaces (income, budgets, the month view)."""

import calendar
from datetime import date
from decimal import Decimal

from app.shared.domain.exceptions import ValidationException
from app.shared.domain.value_objects import MAX_MONEY_AMOUNT

BUDGET_WARNING_RATIO = Decimal("0.8")


def clean_text(value: str | None, *, field: str, max_length: int, required: bool = True) -> str | None:
    cleaned = " ".join((value or "").split())
    if not cleaned:
        if required:
            raise ValidationException(f"{field} is required")
        return None
    if len(cleaned) > max_length:
        raise ValidationException(f"{field} is too long ({max_length} characters maximum)")
    return cleaned


def category_key(category: str) -> str:
    """Budgets and spending match on the category name ignoring case and spacing."""
    return " ".join(category.split()).lower()


def positive_amount(value: Decimal, *, field: str) -> Decimal:
    if not value.is_finite() or value <= 0:
        raise ValidationException(f"{field} must be greater than zero")
    if value > MAX_MONEY_AMOUNT:
        raise ValidationException(f"{field} is too large")
    return value.quantize(Decimal("0.01"))


def month_bounds(year: int, month: int) -> tuple[date, date]:
    if not 1 <= month <= 12:
        raise ValidationException("month must be between 1 and 12")
    return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])


def budget_status(spent: Decimal, limit: Decimal) -> str:
    """ok / near (80% or more of the limit) / over (past it)."""
    if spent > limit:
        return "over"
    if limit > 0 and spent >= limit * BUDGET_WARNING_RATIO:
        return "near"
    return "ok"
