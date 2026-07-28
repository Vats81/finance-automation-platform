import uuid

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.data_import.application.dtos import ImportRowError, ImportSummary
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


def _mapped_value(raw_row: dict[str, str], column_mapping: dict[str, str], field: str) -> str | None:
    header = column_mapping.get(field)
    if not header:
        return None
    value = raw_row.get(header)
    return value.strip() if value else None


class ImportVendorsUseCase:
    """Orchestrates CreateBusinessVendorUseCase (vendors/application/commands/
    create_business_vendor.py) per CSV row — see data_import module's design
    note in the Slice 7 plan.
    """

    def __init__(self, uow: AppUnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self, *, business_id: uuid.UUID, rows: list[dict[str, str]], column_mapping: dict[str, str]
    ) -> ImportSummary:
        existing, _ = await self._uow.vendors.list_for_business(business_id, offset=0, limit=10_000)
        existing_names = {v.legal_name.strip().lower() for v in existing}

        created = 0
        skipped_duplicates = 0
        errors: list[ImportRowError] = []

        for row_number, raw_row in enumerate(rows, start=1):
            values = {field: _mapped_value(raw_row, column_mapping, field) for field in REQUIRED_FIELDS}
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
                    country=_mapped_value(raw_row, column_mapping, "country") or "US",
                )
                await CreateBusinessVendorUseCase(self._uow).execute(command)
                existing_names.add(legal_name.lower())
                created += 1
            except DomainException as exc:
                errors.append(ImportRowError(row_number=row_number, message=exc.message))

        return ImportSummary(
            total_rows=len(rows), created=created, skipped_duplicates=skipped_duplicates, errors=errors
        )
