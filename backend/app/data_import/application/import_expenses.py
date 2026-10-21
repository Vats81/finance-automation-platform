import uuid
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.data_import.application.dtos import ImportRowError, ImportSummary, ProgressCallback
from app.data_import.application.row_validation import (
    length_error,
    mapped_value,
    parse_amount,
    unexpected_row_failure,
)
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
_MAX_LENGTHS = {"category": 100, "description": 500, "notes": 2000}


def _fingerprint(
    expense_date: date, category: str, description: str, amount: Decimal, payment_method: PaymentMethod
) -> tuple[date, str, str, Decimal, PaymentMethod]:
    return (expense_date, category.strip().lower(), description.strip().lower(), amount, payment_method)


class ImportExpensesUseCase:
    """Orchestrates CreateExpenseUseCase (expenses/application/commands/
    create_expense.py) per CSV row — see data_import module's design note in
    the Slice 7 plan.

    Expenses have no natural unique key, so re-uploading the same file used to
    double every expense. Rows are now matched against what's already stored
    as a multiset on (date, category, description, amount, payment method): a
    row consumes one matching existing expense and is skipped as a duplicate,
    while genuinely repeated rows within one file (two identical coffees on
    the same day) are still imported the first time.
    """

    def __init__(self, uow: AppUnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self,
        *,
        business_id: uuid.UUID,
        rows: list[dict[str, str]],
        column_mapping: dict[str, str],
        on_progress: ProgressCallback | None = None,
    ) -> ImportSummary:
        existing, _ = await self._uow.expenses.list_for_business(business_id, offset=0, limit=10_000)
        remaining = Counter(
            _fingerprint(e.expense_date, e.category, e.description, e.amount.amount, e.payment_method)
            for e in existing
        )

        created = 0
        skipped_duplicates = 0
        errors: list[ImportRowError] = []

        for row_number, raw_row in enumerate(rows, start=1):
            if on_progress:
                on_progress(row_number - 1, len(rows))
            missing = [
                field
                for field in REQUIRED_FIELDS
                if not mapped_value(raw_row, column_mapping, field)
            ]
            if missing:
                errors.append(
                    ImportRowError(
                        row_number=row_number, message=f"Missing required field(s): {', '.join(missing)}"
                    )
                )
                continue

            category = mapped_value(raw_row, column_mapping, "category") or ""
            description = mapped_value(raw_row, column_mapping, "description") or ""
            notes = mapped_value(raw_row, column_mapping, "notes")
            too_long = length_error(
                {"category": category, "description": description, "notes": notes}, _MAX_LENGTHS
            )
            if too_long:
                errors.append(ImportRowError(row_number=row_number, message=too_long))
                continue

            try:
                expense_date = date.fromisoformat(mapped_value(raw_row, column_mapping, "expense_date") or "")
                payment_method_raw = mapped_value(raw_row, column_mapping, "payment_method") or ""
                payment_method = PaymentMethod(payment_method_raw.lower())
                amount = parse_amount(mapped_value(raw_row, column_mapping, "amount"), "amount")
                tax_raw = mapped_value(raw_row, column_mapping, "tax")
                tax = parse_amount(tax_raw, "tax") if tax_raw else None
                is_recurring_raw = mapped_value(raw_row, column_mapping, "is_recurring")

                cents_amount = amount.quantize(Decimal("0.01"))
                key = _fingerprint(expense_date, category, description, cents_amount, payment_method)
                if remaining[key] > 0:
                    remaining[key] -= 1
                    skipped_duplicates += 1
                    continue

                command = CreateExpenseCommand(
                    business_id=business_id,
                    expense_date=expense_date,
                    category=category,
                    description=description,
                    amount=amount,
                    payment_method=payment_method,
                    tax=tax,
                    is_recurring=bool(is_recurring_raw and is_recurring_raw.lower() in _TRUTHY),
                    notes=notes,
                )
                await CreateExpenseUseCase(self._uow).execute(command)
                created += 1
            except DomainException as exc:
                errors.append(ImportRowError(row_number=row_number, message=exc.message))
            except (InvalidOperation, ValueError) as exc:
                errors.append(ImportRowError(row_number=row_number, message=f"Invalid value: {exc}"))
            except Exception as exc:  # noqa: BLE001 - one bad row must not abort the import
                errors.append(await unexpected_row_failure(self._uow, row_number, exc))

        if on_progress:
            on_progress(len(rows), len(rows))

        return ImportSummary(
            total_rows=len(rows), created=created, skipped_duplicates=skipped_duplicates, errors=errors
        )
