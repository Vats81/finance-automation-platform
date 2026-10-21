import uuid

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.customers.application.commands.create_customer import CreateCustomerCommand, CreateCustomerUseCase
from app.data_import.application.dtos import ImportRowError, ImportSummary, ProgressCallback
from app.data_import.application.row_validation import length_error, mapped_value, unexpected_row_failure
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
_MAX_LENGTHS = {
    "name": 255,
    "phone": 32,
    "email": 320,
    "street": 255,
    "city": 120,
    "state": 120,
    "postal_code": 20,
    "country": 2,
    "gst_number": 30,
}


class ImportCustomersUseCase:
    """Orchestrates the existing CreateCustomerUseCase (customers/application/
    commands/create_customer.py) per CSV row — see data_import module's
    design note in the Slice 7 plan for why this bypasses the usual
    domain/infrastructure layers (no new aggregate here, pure orchestration).
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
        existing, _ = await self._uow.customers.list_for_business(business_id, offset=0, limit=10_000)
        existing_names = {c.name.strip().lower() for c in existing}

        created = 0
        skipped_duplicates = 0
        errors: list[ImportRowError] = []

        for row_number, raw_row in enumerate(rows, start=1):
            if on_progress:
                on_progress(row_number - 1, len(rows))
            name = mapped_value(raw_row, column_mapping, "name")
            if not name:
                errors.append(ImportRowError(row_number=row_number, message="Missing required field: name"))
                continue
            if name.lower() in existing_names:
                skipped_duplicates += 1
                continue

            values = {field: mapped_value(raw_row, column_mapping, field) for field in CANONICAL_FIELDS}
            too_long = length_error(values, _MAX_LENGTHS)
            if too_long:
                errors.append(ImportRowError(row_number=row_number, message=too_long))
                continue

            try:
                command = CreateCustomerCommand(
                    business_id=business_id,
                    name=name,
                    phone=values["phone"],
                    email=values["email"],
                    street=values["street"],
                    city=values["city"],
                    state=values["state"],
                    postal_code=values["postal_code"],
                    country=values["country"] or "US",
                    gst_number=values["gst_number"],
                )
                await CreateCustomerUseCase(self._uow).execute(command)
                existing_names.add(name.lower())
                created += 1
            except DomainException as exc:
                errors.append(ImportRowError(row_number=row_number, message=exc.message))
            except Exception as exc:  # noqa: BLE001 - one bad row must not abort the import
                errors.append(await unexpected_row_failure(self._uow, row_number, exc))

        if on_progress:
            on_progress(len(rows), len(rows))

        return ImportSummary(
            total_rows=len(rows), created=created, skipped_duplicates=skipped_duplicates, errors=errors
        )
