import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.business.application.commands.register_business import (
    RegisterBusinessCommand,
    RegisterBusinessUseCase,
)
from app.business.domain.exceptions import BusinessNotFoundException
from app.dashboard.application.send_report_whatsapp import (
    SendReportWhatsAppCommand,
    SendReportWhatsAppUseCase,
)
from app.expenses.application.commands.create_expense import CreateExpenseCommand, CreateExpenseUseCase
from app.expenses.domain.value_objects import PaymentMethod
from app.sales.application.commands.create_sale import (
    CreateSaleCommand,
    CreateSaleLineItemInput,
    CreateSaleUseCase,
)
from tests.fakes.fake_ports import FakeWhatsAppSender
from tests.fakes.fake_unit_of_work import FakeUnitOfWork


async def test_sends_whatsapp_summary_with_correct_totals() -> None:
    uow = FakeUnitOfWork()
    whatsapp_sender = FakeWhatsAppSender()
    owner_id = uuid.uuid4()
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=owner_id, name="Jane's Diner Supplies")
    )
    await CreateSaleUseCase(uow).execute(
        CreateSaleCommand(
            business_id=business.id,
            invoice_number="INV-1",
            invoice_date=date(2026, 7, 20),
            line_items=[
                CreateSaleLineItemInput(
                    line_number=1, description="Widget", quantity=Decimal("1"), unit_price=Decimal("500")
                )
            ],
        )
    )
    await CreateExpenseUseCase(uow).execute(
        CreateExpenseCommand(
            business_id=business.id,
            expense_date=date(2026, 7, 18),
            category="Rent",
            description="Office rent",
            amount=Decimal("150"),
            payment_method=PaymentMethod.BANK_TRANSFER,
        )
    )

    await SendReportWhatsAppUseCase(uow, whatsapp_sender).execute(
        SendReportWhatsAppCommand(
            business_id=business.id,
            recipient_phone="+15551234567",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
        )
    )

    assert len(whatsapp_sender.sent) == 1
    sent = whatsapp_sender.sent[0]
    assert sent["to"] == "+15551234567"
    assert "Jane's Diner Supplies" in sent["message"]
    assert "$500.00" in sent["message"]
    assert "$150.00" in sent["message"]
    assert "$350.00" in sent["message"]
    assert "/app/reports" in sent["message"]


async def test_raises_for_unknown_business() -> None:
    uow = FakeUnitOfWork()
    whatsapp_sender = FakeWhatsAppSender()

    with pytest.raises(BusinessNotFoundException):
        await SendReportWhatsAppUseCase(uow, whatsapp_sender).execute(
            SendReportWhatsAppCommand(
                business_id=uuid.uuid4(),
                recipient_phone="+15551234567",
                start_date=date(2026, 7, 1),
                end_date=date(2026, 7, 31),
            )
        )

    assert whatsapp_sender.sent == []
