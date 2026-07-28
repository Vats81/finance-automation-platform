import json
import uuid
from datetime import date
from decimal import Decimal

from app.ai_assistant.application.tools import TOOL_HANDLERS
from app.business.application.commands.register_business import (
    RegisterBusinessCommand,
    RegisterBusinessUseCase,
)
from app.customers.application.commands.create_customer import CreateCustomerCommand, CreateCustomerUseCase
from app.expenses.application.commands.create_expense import CreateExpenseCommand, CreateExpenseUseCase
from app.expenses.domain.value_objects import PaymentMethod
from app.inventory.application.commands.create_product import CreateProductCommand, CreateProductUseCase
from app.purchases.application.commands.create_purchase import (
    CreatePurchaseCommand,
    CreatePurchaseLineItemInput,
    CreatePurchaseUseCase,
)
from app.sales.application.commands.create_sale import (
    CreateSaleCommand,
    CreateSaleLineItemInput,
    CreateSaleUseCase,
)
from app.vendors.application.commands.create_business_vendor import (
    CreateBusinessVendorCommand,
    CreateBusinessVendorUseCase,
)
from tests.fakes.fake_unit_of_work import FakeUnitOfWork


async def _make_business(uow: FakeUnitOfWork) -> uuid.UUID:
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=uuid.uuid4(), name="Jane's Diner Supplies")
    )
    return business.id


async def test_get_business_summary_tool() -> None:
    uow = FakeUnitOfWork()
    business_id = await _make_business(uow)
    await CreateSaleUseCase(uow).execute(
        CreateSaleCommand(
            business_id=business_id,
            invoice_number="INV-1",
            invoice_date=date(2026, 7, 20),
            line_items=[
                CreateSaleLineItemInput(
                    line_number=1, description="Widget", quantity=Decimal("1"), unit_price=Decimal("500")
                )
            ],
        )
    )

    result = await TOOL_HANDLERS["get_business_summary"](
        uow, business_id, start_date="2026-07-01", end_date="2026-07-31"
    )

    assert result["total_revenue"] == "500.00"


async def test_list_outstanding_sales_tool() -> None:
    uow = FakeUnitOfWork()
    business_id = await _make_business(uow)
    await CreateSaleUseCase(uow).execute(
        CreateSaleCommand(
            business_id=business_id,
            invoice_number="INV-1",
            invoice_date=date(2026, 7, 20),
            line_items=[
                CreateSaleLineItemInput(
                    line_number=1, description="Widget", quantity=Decimal("1"), unit_price=Decimal("500")
                )
            ],
        )
    )

    result = await TOOL_HANDLERS["list_outstanding_sales"](uow, business_id)

    assert len(result["sales"]) == 1
    assert result["sales"][0]["invoice_number"] == "INV-1"
    assert result["sales"][0]["outstanding_amount"] == "500.00"
    assert json.dumps(result)  # must be JSON-serializable


async def test_list_outstanding_purchases_tool() -> None:
    uow = FakeUnitOfWork()
    business_id = await _make_business(uow)
    vendor = await CreateBusinessVendorUseCase(uow).execute(
        CreateBusinessVendorCommand(
            business_id=business_id,
            legal_name="Acme Supplies",
            contact_email="ap@acme.example",
            tax_id="12-3456789",
            street="1 Main St",
            city="Springfield",
            state="IL",
            postal_code="62701",
        )
    )
    await CreatePurchaseUseCase(uow).execute(
        CreatePurchaseCommand(
            business_id=business_id,
            purchase_number="PO-1",
            vendor_id=vendor.id,
            purchase_date=date(2026, 7, 1),
            line_items=[
                CreatePurchaseLineItemInput(
                    line_number=1, description="Supplies", quantity=Decimal("1"), unit_cost=Decimal("200")
                )
            ],
        )
    )

    result = await TOOL_HANDLERS["list_outstanding_purchases"](uow, business_id)

    assert len(result["purchases"]) == 1
    assert result["purchases"][0]["purchase_number"] == "PO-1"
    assert result["purchases"][0]["outstanding_amount"] == "200.00"


async def test_list_low_stock_products_tool_filters_correctly() -> None:
    uow = FakeUnitOfWork()
    business_id = await _make_business(uow)
    await CreateProductUseCase(uow).execute(
        CreateProductCommand(
            business_id=business_id,
            name="Low Stock Widget",
            sku="LOW-1",
            selling_price=Decimal("10"),
            purchase_cost=Decimal("5"),
            current_quantity=Decimal("1"),
            minimum_stock_level=Decimal("5"),
        )
    )
    await CreateProductUseCase(uow).execute(
        CreateProductCommand(
            business_id=business_id,
            name="Plenty Widget",
            sku="OK-1",
            selling_price=Decimal("10"),
            purchase_cost=Decimal("5"),
            current_quantity=Decimal("100"),
            minimum_stock_level=Decimal("5"),
        )
    )

    result = await TOOL_HANDLERS["list_low_stock_products"](uow, business_id)

    assert len(result["products"]) == 1
    assert result["products"][0]["sku"] == "LOW-1"


async def test_list_recent_expenses_tool_sorts_and_limits() -> None:
    uow = FakeUnitOfWork()
    business_id = await _make_business(uow)
    for i, expense_date in enumerate([date(2026, 5, 1), date(2026, 7, 1), date(2026, 6, 1)]):
        await CreateExpenseUseCase(uow).execute(
            CreateExpenseCommand(
                business_id=business_id,
                expense_date=expense_date,
                category="Rent",
                description=f"Expense {i}",
                amount=Decimal("10"),
                payment_method=PaymentMethod.CASH,
            )
        )

    result = await TOOL_HANDLERS["list_recent_expenses"](uow, business_id, limit=2)

    assert len(result["expenses"]) == 2
    assert result["expenses"][0]["expense_date"] == "2026-07-01"
    assert result["expenses"][1]["expense_date"] == "2026-06-01"


async def test_list_customers_tool() -> None:
    uow = FakeUnitOfWork()
    business_id = await _make_business(uow)
    await CreateCustomerUseCase(uow).execute(
        CreateCustomerCommand(business_id=business_id, name="Jane's Diner", email="jane@example.com")
    )

    result = await TOOL_HANDLERS["list_customers"](uow, business_id)

    assert len(result["customers"]) == 1
    assert result["customers"][0]["name"] == "Jane's Diner"
