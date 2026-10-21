import uuid
from decimal import Decimal, InvalidOperation

from app.bootstrap.unit_of_work import AppUnitOfWork
from app.data_import.application.dtos import ImportRowError, ImportSummary, ProgressCallback
from app.data_import.application.row_validation import (
    length_error,
    mapped_value,
    parse_amount,
    unexpected_row_failure,
)
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
_MAX_LENGTHS = {"name": 255, "sku": 100, "category": 100, "unit_of_measurement": 30}


class ImportProductsUseCase:
    """Orchestrates CreateProductUseCase (inventory/application/commands/
    create_product.py) per CSV row — see data_import module's design note in
    the Slice 7 plan.
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
        existing, _ = await self._uow.products.list_for_business(business_id, offset=0, limit=10_000)
        existing_skus = {p.sku.strip().lower() for p in existing}

        created = 0
        skipped_duplicates = 0
        errors: list[ImportRowError] = []

        for row_number, raw_row in enumerate(rows, start=1):
            if on_progress:
                on_progress(row_number - 1, len(rows))
            name = mapped_value(raw_row, column_mapping, "name")
            sku = mapped_value(raw_row, column_mapping, "sku")
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

            assert sku is not None
            if sku.lower() in existing_skus:
                skipped_duplicates += 1
                continue

            category = mapped_value(raw_row, column_mapping, "category")
            unit = mapped_value(raw_row, column_mapping, "unit_of_measurement")
            too_long = length_error(
                {"name": name, "sku": sku, "category": category, "unit_of_measurement": unit}, _MAX_LENGTHS
            )
            if too_long:
                errors.append(ImportRowError(row_number=row_number, message=too_long))
                continue

            try:
                command = CreateProductCommand(
                    business_id=business_id,
                    name=name or "",
                    sku=sku,
                    selling_price=parse_amount(
                        mapped_value(raw_row, column_mapping, "selling_price"), "selling_price"
                    ),
                    purchase_cost=parse_amount(
                        mapped_value(raw_row, column_mapping, "purchase_cost"), "purchase_cost"
                    ),
                    category=category,
                    current_quantity=parse_amount(
                        mapped_value(raw_row, column_mapping, "current_quantity"),
                        "current_quantity",
                        default=Decimal("0"),
                    ),
                    minimum_stock_level=parse_amount(
                        mapped_value(raw_row, column_mapping, "minimum_stock_level"),
                        "minimum_stock_level",
                        default=Decimal("0"),
                    ),
                    reorder_quantity=parse_amount(
                        mapped_value(raw_row, column_mapping, "reorder_quantity"),
                        "reorder_quantity",
                        default=Decimal("0"),
                    ),
                    unit_of_measurement=unit or "unit",
                )
                await CreateProductUseCase(self._uow).execute(command)
                existing_skus.add(sku.lower())
                created += 1
            except DomainException as exc:
                errors.append(ImportRowError(row_number=row_number, message=exc.message))
            except (InvalidOperation, ValueError) as exc:
                errors.append(ImportRowError(row_number=row_number, message=f"Invalid number: {exc}"))
            except Exception as exc:  # noqa: BLE001 - one bad row must not abort the import
                errors.append(await unexpected_row_failure(self._uow, row_number, exc))

        if on_progress:
            on_progress(len(rows), len(rows))

        return ImportSummary(
            total_rows=len(rows), created=created, skipped_duplicates=skipped_duplicates, errors=errors
        )
