import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.business.application.commands.register_business import (
    RegisterBusinessCommand,
    RegisterBusinessUseCase,
)
from app.business.domain.exceptions import BusinessNotFoundException
from app.dashboard.application.send_report_email import SendReportEmailCommand, SendReportEmailUseCase
from app.sales.application.commands.create_sale import (
    CreateSaleCommand,
    CreateSaleLineItemInput,
    CreateSaleUseCase,
)
from tests.fakes.fake_ports import FakeEmailSender
from tests.fakes.fake_unit_of_work import FakeUnitOfWork


async def test_sends_email_with_pdf_attachment() -> None:
    uow = FakeUnitOfWork()
    email_sender = FakeEmailSender()
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

    await SendReportEmailUseCase(uow, email_sender).execute(
        SendReportEmailCommand(
            business_id=business.id,
            recipient_email="owner@example.com",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
        )
    )

    assert len(email_sender.sent) == 1
    sent = email_sender.sent[0]
    assert sent["to"] == "owner@example.com"
    assert "Jane's Diner Supplies" in sent["subject"]
    assert len(sent["attachments"]) == 1
    assert sent["attachments"][0].content.startswith(b"%PDF-")
    assert sent["attachments"][0].content_type == "application/pdf"


async def test_raises_for_unknown_business() -> None:
    uow = FakeUnitOfWork()
    email_sender = FakeEmailSender()

    with pytest.raises(BusinessNotFoundException):
        await SendReportEmailUseCase(uow, email_sender).execute(
            SendReportEmailCommand(
                business_id=uuid.uuid4(),
                recipient_email="owner@example.com",
                start_date=date(2026, 7, 1),
                end_date=date(2026, 7, 31),
            )
        )

    assert email_sender.sent == []
