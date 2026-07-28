import uuid
from decimal import Decimal, InvalidOperation

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.data_import.application.dtos import ImportRowError, ImportSummary
from app.inventory.application.commands.create_product import CreateProductCommand, CreateProductUseCase
from app.shared.domain.exceptions import DomainException

CANONICAL_FIELDS = [
    "name",
    "sku",
    "category",
    "selling_price",
    "purchase_cost",
    "current_quantity",
    "minimum_stock_level",
    "reorder_quantity",
    "unit_of_measurement",
]
REQUIRED_FIELDS = ["name", "sku", "selling_price", "purchase_cost"]


def _mapped_value(raw_row: dict[str, str], column_mapping: dict[str, str], field: str) -> str | None:
    header = column_mapping.get(field)
    if not header:
        return None
    value = raw_row.get(header)
    return value.strip() if value else None


def _parse_decimal(value: str | None, default: Decimal) -> Decimal:
    if not value:
        return default
    return Decimal(value)


class ImportProductsUseCase:
    """Orchestrates CreateProductUseCase (inventory/application/commands/
    create_product.py) per CSV row — see data_import module's design note in
    the Slice 7 plan.
    """

    def __init__(self, uow: AppUnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self, *, business_id: uuid.UUID, rows: list[dict[str, str]], column_mapping: dict[str, str]
    ) -> ImportSummary:
        existing, _ = await self._uow.products.list_for_business(business_id, offset=0, limit=10_000)
        existing_skus = {p.sku.strip().lower() for p in existing}

        created = 0
        skipped_duplicates = 0
        errors: list[ImportRowError] = []

        for row_number, raw_row in enumerate(rows, start=1):
            name = _mapped_value(raw_row, column_mapping, "name")
            sku = _mapped_value(raw_row, column_mapping, "sku")
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

            assert sku is not None
            if sku.lower() in existing_skus:
                skipped_duplicates += 1
                continue

            try:
                command = CreateProductCommand(
                    business_id=business_id,
                    name=name or "",
                    sku=sku,
                    selling_price=Decimal(_mapped_value(raw_row, column_mapping, "selling_price") or "0"),
                    purchase_cost=Decimal(_mapped_value(raw_row, column_mapping, "purchase_cost") or "0"),
                    category=_mapped_value(raw_row, column_mapping, "category"),
                    current_quantity=_parse_decimal(
                        _mapped_value(raw_row, column_mapping, "current_quantity"), Decimal("0")
                    ),
                    minimum_stock_level=_parse_decimal(
                        _mapped_value(raw_row, column_mapping, "minimum_stock_level"), Decimal("0")
                    ),
                    reorder_quantity=_parse_decimal(
                        _mapped_value(raw_row, column_mapping, "reorder_quantity"), Decimal("0")
                    ),
                    unit_of_measurement=_mapped_value(raw_row, column_mapping, "unit_of_measurement")
                    or "unit",
                )
                await CreateProductUseCase(self._uow).execute(command)
                existing_skus.add(sku.lower())
                created += 1
            except DomainException as exc:
                errors.append(ImportRowError(row_number=row_number, message=exc.message))
            except (InvalidOperation, ValueError) as exc:
                errors.append(ImportRowError(row_number=row_number, message=f"Invalid number: {exc}"))

        return ImportSummary(
            total_rows=len(rows), created=created, skipped_duplicates=skipped_duplicates, errors=errors
        )
