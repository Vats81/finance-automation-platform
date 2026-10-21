import uuid

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.data_import.application.dtos import ImportRowError, ImportSummary, ProgressCallback
from app.data_import.application.row_validation import length_error, mapped_value, unexpected_row_failure
from app.shared.domain.exceptions import DomainException
from app.vendors.application.commands.create_business_vendor import (
    CreateBusinessVendorCommand,
    CreateBusinessVendorUseCase,
)

CANONICAL_FIELDS = [
    "legal_name",
    "contact_email",
    "tax_id",
    "street",
    "city",
    "state",
    "postal_code",
    "country",
]
REQUIRED_FIELDS = ["legal_name", "contact_email", "tax_id", "street", "city", "state", "postal_code"]
_MAX_LENGTHS = {
    "legal_name": 255,
    "contact_email": 320,
    "tax_id": 20,
    "street": 255,
    "city": 120,
    "state": 120,
    "postal_code": 20,
    "country": 2,
}


class ImportVendorsUseCase:
    """Orchestrates CreateBusinessVendorUseCase (vendors/application/commands/
    create_business_vendor.py) per CSV row — see data_import module's design
    note in the Slice 7 plan.
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
        existing, _ = await self._uow.vendors.list_for_business(business_id, offset=0, limit=10_000)
        existing_names = {v.legal_name.strip().lower() for v in existing}

        created = 0
        skipped_duplicates = 0
        errors: list[ImportRowError] = []

        for row_number, raw_row in enumerate(rows, start=1):
            if on_progress:
                on_progress(row_number - 1, len(rows))
            values = {field: mapped_value(raw_row, column_mapping, field) for field in REQUIRED_FIELDS}
            missing = [field for field in REQUIRED_FIELDS if not values[field]]
            if missing:
                errors.append(
                    ImportRowError(
                        row_number=row_number, message=f"Missing required field(s): {', '.join(missing)}"
                    )
                )
                continue

            legal_name = values["legal_name"] or ""
            if legal_name.lower() in existing_names:
                skipped_duplicates += 1
                continue

            country = mapped_value(raw_row, column_mapping, "country")
            too_long = length_error({**values, "country": country}, _MAX_LENGTHS)
            if too_long:
                errors.append(ImportRowError(row_number=row_number, message=too_long))
                continue

            try:
                command = CreateBusinessVendorCommand(
                    business_id=business_id,
                    legal_name=legal_name,
                    contact_email=values["contact_email"] or "",
                    tax_id=values["tax_id"] or "",
                    street=values["street"] or "",
                    city=values["city"] or "",
                    state=values["state"] or "",
                    postal_code=values["postal_code"] or "",
                    country=country or "US",
                )
                await CreateBusinessVendorUseCase(self._uow).execute(command)
                existing_names.add(legal_name.lower())
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
