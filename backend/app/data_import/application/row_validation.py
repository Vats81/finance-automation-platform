import logging
from collections.abc import Mapping
from decimal import Decimal

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.data_import.application.dtos import ImportRowError
from app.shared.domain.exceptions import ValidationException
from app.shared.domain.value_objects import MAX_MONEY_AMOUNT

logger = logging.getLogger(__name__)

MAX_AMOUNT = MAX_MONEY_AMOUNT


def mapped_value(raw_row: dict[str, str], column_mapping: dict[str, str], field: str) -> str | None:
    header = column_mapping.get(field)
    if not header:
        return None
    value = raw_row.get(header)
    return value.strip() if value else None


def length_error(values: Mapping[str, str | None], limits: Mapping[str, int]) -> str | None:
    """Row-level message for the first value longer than its column allows, so
    an over-long cell is reported against its row instead of failing at insert.
    """
    for field, limit in limits.items():
        value = values.get(field)
        if value is not None and len(value) > limit:
            return f"{field} is too long ({len(value)} characters; the maximum is {limit})"
    return None


def parse_amount(raw: str | None, field: str, *, default: Decimal | None = None) -> Decimal:
    """Decimal for a money/quantity cell: finite, not negative, not absurdly
    large. Raises ValidationException (reported as a row error).
    """
    if not raw:
        if default is None:
            raise ValidationException(f"{field} is required")
        return default
    value = Decimal(raw)  # InvalidOperation is reported by the caller as a bad value
    if not value.is_finite():
        raise ValidationException(f"{field} must be a number")
    if value < 0:
        raise ValidationException(f"{field} cannot be negative")
    if value > MAX_AMOUNT:
        raise ValidationException(f"{field} is too large")
    return value


async def unexpected_row_failure(uow: AppUnitOfWork, row_number: int, exc: Exception) -> ImportRowError:
    """Safety net for anything a row's own validation missed (e.g. a database
    error). The session is unusable until rolled back, so do that, then report
    the row and carry on — one bad row must not abort or 500 the whole import.
    """
    logger.exception("Import row %s failed unexpectedly", row_number, exc_info=exc)
    await uow.rollback()
    return ImportRowError(row_number=row_number, message="This row could not be saved. Check its values.")
