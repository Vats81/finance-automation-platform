import uuid
from datetime import date
from decimal import Decimal, InvalidOperation

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.data_import.application.dtos import ImportRowError, ImportSummary
from app.expenses.application.commands.create_expense import CreateExpenseCommand, CreateExpenseUseCase
from app.expenses.domain.value_objects import PaymentMethod
from app.shared.domain.exceptions import DomainException

CANONICAL_FIELDS = [
    "expense_date",
    "category",
    "description",
    "amount",
    "tax",
    "payment_method",
    "is_recurring",
    "notes",
]
REQUIRED_FIELDS = ["expense_date", "category", "description", "amount", "payment_method"]

_TRUTHY = {"true", "yes", "1", "y"}


def _mapped_value(raw_row: dict[str, str], column_mapping: dict[str, str], field: str) -> str | None:
    header = column_mapping.get(field)
    if not header:
        return None
    value = raw_row.get(header)
    return value.strip() if value else None


class ImportExpensesUseCase:
    """Orchestrates CreateExpenseUseCase (expenses/application/commands/
    create_expense.py) per CSV row — see data_import module's design note in
    the Slice 7 plan. No natural dedup key for expenses, so every valid row
    is imported (no skipped_duplicates).
    """

    def __init__(self, uow: AppUnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self, *, business_id: uuid.UUID, rows: list[dict[str, str]], column_mapping: dict[str, str]
    ) -> ImportSummary:
        created = 0
        errors: list[ImportRowError] = []

        for row_number, raw_row in enumerate(rows, start=1):
            missing = [
                field
                for field in REQUIRED_FIELDS
                if not _mapped_value(raw_row, column_mapping, field)
            ]
            if missing:
                errors.append(
                    ImportRowError(
                        row_number=row_number, message=f"Missing required field(s): {', '.join(missing)}"
                    )
                )
                continue

            try:
                expense_date_raw = _mapped_value(raw_row, column_mapping, "expense_date") or ""
                payment_method_raw = _mapped_value(raw_row, column_mapping, "payment_method") or ""
                tax_raw = _mapped_value(raw_row, column_mapping, "tax")
                is_recurring_raw = _mapped_value(raw_row, column_mapping, "is_recurring")

                command = CreateExpenseCommand(
                    business_id=business_id,
                    expense_date=date.fromisoformat(expense_date_raw),
                    category=_mapped_value(raw_row, column_mapping, "category") or "",
                    description=_mapped_value(raw_row, column_mapping, "description") or "",
                    amount=Decimal(_mapped_value(raw_row, column_mapping, "amount") or "0"),
                    payment_method=PaymentMethod(payment_method_raw.lower()),
                    tax=Decimal(tax_raw) if tax_raw else None,
                    is_recurring=bool(is_recurring_raw and is_recurring_raw.lower() in _TRUTHY),
                    notes=_mapped_value(raw_row, column_mapping, "notes"),
                )
                await CreateExpenseUseCase(self._uow).execute(command)
                created += 1
            except DomainException as exc:
                errors.append(ImportRowError(row_number=row_number, message=exc.message))
            except (InvalidOperation, ValueError) as exc:
                errors.append(ImportRowError(row_number=row_number, message=f"Invalid value: {exc}"))

        return ImportSummary(total_rows=len(rows), created=created, skipped_duplicates=0, errors=errors)
