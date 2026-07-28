import uuid

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.customers.application.commands.create_customer import CreateCustomerCommand, CreateCustomerUseCase
from app.data_import.application.dtos import ImportRowError, ImportSummary
from app.shared.domain.exceptions import DomainException

CANONICAL_FIELDS = [
    "name",
    "phone",
    "email",
    "street",
    "city",
    "state",
    "postal_code",
    "country",
    "gst_number",
]
REQUIRED_FIELDS = ["name"]


def _mapped_value(raw_row: dict[str, str], column_mapping: dict[str, str], field: str) -> str | None:
    header = column_mapping.get(field)
    if not header:
        return None
    value = raw_row.get(header)
    return value.strip() if value else None


class ImportCustomersUseCase:
    """Orchestrates the existing CreateCustomerUseCase (customers/application/
    commands/create_customer.py) per CSV row — see data_import module's
    design note in the Slice 7 plan for why this bypasses the usual
    domain/infrastructure layers (no new aggregate here, pure orchestration).
    """

    def __init__(self, uow: AppUnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self, *, business_id: uuid.UUID, rows: list[dict[str, str]], column_mapping: dict[str, str]
    ) -> ImportSummary:
        existing, _ = await self._uow.customers.list_for_business(business_id, offset=0, limit=10_000)
        existing_names = {c.name.strip().lower() for c in existing}

        created = 0
        skipped_duplicates = 0
        errors: list[ImportRowError] = []

        for row_number, raw_row in enumerate(rows, start=1):
            name = _mapped_value(raw_row, column_mapping, "name")
            if not name:
                errors.append(ImportRowError(row_number=row_number, message="Missing required field: name"))
                continue
            if name.lower() in existing_names:
                skipped_duplicates += 1
                continue

            try:
                command = CreateCustomerCommand(
                    business_id=business_id,
                    name=name,
                    phone=_mapped_value(raw_row, column_mapping, "phone"),
                    email=_mapped_value(raw_row, column_mapping, "email"),
                    street=_mapped_value(raw_row, column_mapping, "street"),
                    city=_mapped_value(raw_row, column_mapping, "city"),
                    state=_mapped_value(raw_row, column_mapping, "state"),
                    postal_code=_mapped_value(raw_row, column_mapping, "postal_code"),
                    country=_mapped_value(raw_row, column_mapping, "country") or "US",
                    gst_number=_mapped_value(raw_row, column_mapping, "gst_number"),
                )
                await CreateCustomerUseCase(self._uow).execute(command)
                existing_names.add(name.lower())
                created += 1
            except DomainException as exc:
                errors.append(ImportRowError(row_number=row_number, message=exc.message))

        return ImportSummary(
            total_rows=len(rows), created=created, skipped_duplicates=skipped_duplicates, errors=errors
        )
