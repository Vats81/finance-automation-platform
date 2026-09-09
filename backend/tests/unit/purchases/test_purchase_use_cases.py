import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.purchases.application.commands.create_purchase import (
    CreatePurchaseCommand,
    CreatePurchaseLineItemInput,
    CreatePurchaseUseCase,
)
from app.purchases.application.commands.record_payment import (
    RecordPurchasePaymentCommand,
    RecordPurchasePaymentUseCase,
)
from app.purchases.application.commands.update_purchase import (
    UpdatePurchaseCommand,
    UpdatePurchaseLineItemInput,
    UpdatePurchaseUseCase,
)
from app.purchases.application.commands.void_purchase import VoidPurchaseCommand, VoidPurchaseUseCase
from app.purchases.application.queries.get_purchase import GetPurchaseQuery, GetPurchaseUseCase
from app.purchases.application.queries.list_purchases import ListPurchasesQuery, ListPurchasesUseCase
from app.purchases.domain.exceptions import PurchaseNotFoundException
from app.purchases.domain.value_objects import PurchasePaymentStatus
from app.shared.application.pagination import PageRequest
from tests.fakes.fake_unit_of_work import FakeUnitOfWork


def make_create_command(business_id: uuid.UUID, **overrides) -> CreatePurchaseCommand:
    defaults = dict(
        business_id=business_id,
        purchase_number="PO-001",
        vendor_id=uuid.uuid4(),
        purchase_date=date(2026, 1, 1),
        line_items=[
            CreatePurchaseLineItemInput(
                line_number=1, description="Raw materials", quantity=Decimal("10"), unit_cost=Decimal("5")
            )
        ],
    )
    defaults.update(overrides)
    return CreatePurchaseCommand(**defaults)


async def test_create_and_get_purchase() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()

    created = await CreatePurchaseUseCase(uow).execute(make_create_command(business_id))

    fetched = await GetPurchaseUseCase(uow).execute(
        GetPurchaseQuery(business_id=business_id, purchase_id=created.id)
    )
    assert fetched.purchase_number == "PO-001"
    assert fetched.total_amount.amount == Decimal("50.00")


async def test_get_purchase_from_wrong_business_raises() -> None:
    uow = FakeUnitOfWork()
    purchase = await CreatePurchaseUseCase(uow).execute(make_create_command(uuid.uuid4()))

    with pytest.raises(PurchaseNotFoundException):
        await GetPurchaseUseCase(uow).execute(
            GetPurchaseQuery(business_id=uuid.uuid4(), purchase_id=purchase.id)
        )


async def test_list_purchases_is_scoped_per_business() -> None:
    uow = FakeUnitOfWork()
    business_a = uuid.uuid4()
    business_b = uuid.uuid4()
    await CreatePurchaseUseCase(uow).execute(make_create_command(business_a, purchase_number="A-1"))
    await CreatePurchaseUseCase(uow).execute(make_create_command(business_b, purchase_number="B-1"))

    page = await ListPurchasesUseCase(uow).execute(
        ListPurchasesQuery(business_id=business_a, page=PageRequest())
    )

    assert page.total == 1
    assert page.items[0].purchase_number == "A-1"


async def test_record_payment_use_case_updates_payment_status() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    purchase = await CreatePurchaseUseCase(uow).execute(make_create_command(business_id))

    updated = await RecordPurchasePaymentUseCase(uow).execute(
        RecordPurchasePaymentCommand(business_id=business_id, purchase_id=purchase.id, amount=Decimal("50"))
    )

    assert updated.payment_status == PurchasePaymentStatus.PAID


async def test_void_purchase_use_case() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    purchase = await CreatePurchaseUseCase(uow).execute(make_create_command(business_id))

    voided = await VoidPurchaseUseCase(uow).execute(
        VoidPurchaseCommand(business_id=business_id, purchase_id=purchase.id)
    )

    assert voided.status.value == "void"


async def test_update_purchase_use_case_changes_fields_and_recomputes_total() -> None:
    uow = FakeUnitOfWork()
    business_id = uuid.uuid4()
    purchase = await CreatePurchaseUseCase(uow).execute(make_create_command(business_id))
    new_vendor_id = uuid.uuid4()

    updated = await UpdatePurchaseUseCase(uow).execute(
        UpdatePurchaseCommand(
            business_id=business_id,
            purchase_id=purchase.id,
            purchase_number="PO-002",
            vendor_id=new_vendor_id,
            purchase_date=date(2026, 2, 1),
            line_items=[
                UpdatePurchaseLineItemInput(
                    line_number=1, description="New materials", quantity=Decimal("4"), unit_cost=Decimal("2")
                )
            ],
        )
    )

    assert updated.purchase_number == "PO-002"
    assert updated.vendor_id == new_vendor_id
    assert updated.total_amount.amount == Decimal("8.00")

    refetched = await GetPurchaseUseCase(uow).execute(
        GetPurchaseQuery(business_id=business_id, purchase_id=purchase.id)
    )
    assert refetched.purchase_number == "PO-002"
