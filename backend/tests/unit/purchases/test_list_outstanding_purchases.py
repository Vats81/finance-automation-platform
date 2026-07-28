import uuid
from datetime import date
from decimal import Decimal

from app.purchases.application.commands.create_purchase import (
    CreatePurchaseCommand,
    CreatePurchaseLineItemInput,
    CreatePurchaseUseCase,
)
from app.purchases.application.commands.record_payment import (
    RecordPurchasePaymentCommand,
    RecordPurchasePaymentUseCase,
)
from app.purchases.application.commands.void_purchase import VoidPurchaseCommand, VoidPurchaseUseCase
from app.purchases.application.queries.list_outstanding_purchases import (
    ListOutstandingPurchasesQuery,
    ListOutstandingPurchasesUseCase,
)
from tests.fakes.fake_unit_of_work import FakeUnitOfWork


def make_create_command(business_id: uuid.UUID, **overrides) -> CreatePurchaseCommand:
    defaults = dict(
        business_id=business_id,
        purchase_number="PO-001",
        vendor_id=uuid.uuid4(),
        purchase_date=date(2026, 1, 1),
        line_items=[
            CreatePurchaseLineItemInput(
                line_number=1, description="Raw materials", quantity=Decimal("1"), unit_cost=Decimal("100")
            )
        ],
    )
    defaults.update(overrides)
    return CreatePurchaseCommand(**defaults)


async def test_outstanding_excludes_paid_and_void_but_includes_unpaid_and_partial() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()

    unpaid = await CreatePurchaseUseCase(uow).execute(
        make_create_command(business_id, purchase_number="UNPAID")
    )
    partial = await CreatePurchaseUseCase(uow).execute(
        make_create_command(business_id, purchase_number="PARTIAL")
    )
    await RecordPurchasePaymentUseCase(uow).execute(
        RecordPurchasePaymentCommand(business_id=business_id, purchase_id=partial.id, amount=Decimal("40"))
    )
    paid = await CreatePurchaseUseCase(uow).execute(make_create_command(business_id, purchase_number="PAID"))
    await RecordPurchasePaymentUseCase(uow).execute(
        RecordPurchasePaymentCommand(business_id=business_id, purchase_id=paid.id, amount=Decimal("100"))
    )
    voided = await CreatePurchaseUseCase(uow).execute(
        make_create_command(business_id, purchase_number="VOIDED")
    )
    await VoidPurchaseUseCase(uow).execute(
        VoidPurchaseCommand(business_id=business_id, purchase_id=voided.id)
    )

    outstanding = await ListOutstandingPurchasesUseCase(uow).execute(
        ListOutstandingPurchasesQuery(business_id=business_id)
    )

    purchase_numbers = {purchase.purchase_number for purchase in outstanding}
    assert purchase_numbers == {"UNPAID", "PARTIAL"}
    assert unpaid.id in {p.id for p in outstanding}


async def test_outstanding_is_scoped_per_business() -> None:
    uow = FakeUnitOfWork()
    business_a = uuid.uuid4()
    business_b = uuid.uuid4()
    await CreatePurchaseUseCase(uow).execute(make_create_command(business_a, purchase_number="A-1"))
    await CreatePurchaseUseCase(uow).execute(make_create_command(business_b, purchase_number="B-1"))

    outstanding = await ListOutstandingPurchasesUseCase(uow).execute(
        ListOutstandingPurchasesQuery(business_id=business_a)
    )

    assert [p.purchase_number for p in outstanding] == ["A-1"]


async def test_outstanding_sorts_by_due_date_with_nulls_last() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()

    await CreatePurchaseUseCase(uow).execute(
        make_create_command(business_id, purchase_number="NO-DUE-DATE", due_date=None)
    )
    await CreatePurchaseUseCase(uow).execute(
        make_create_command(business_id, purchase_number="LATER", due_date=date(2026, 6, 1))
    )
    await CreatePurchaseUseCase(uow).execute(
        make_create_command(business_id, purchase_number="SOONER", due_date=date(2026, 2, 1))
    )

    outstanding = await ListOutstandingPurchasesUseCase(uow).execute(
        ListOutstandingPurchasesQuery(business_id=business_id)
    )

    assert [p.purchase_number for p in outstanding] == ["SOONER", "LATER", "NO-DUE-DATE"]
