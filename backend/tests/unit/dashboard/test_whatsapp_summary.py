"""The WhatsApp summary: what it says, who gets it when, and the scheduled send."""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.api.rate_limit import limiter
from app.bootstrap.app_factory import create_app
from app.bootstrap.container import get_clock, get_uow, get_whatsapp_sender
from app.business.application.commands.complete_onboarding import (
    CompleteOnboardingCommand,
    CompleteOnboardingUseCase,
)
from app.business.application.commands.register_business import (
    RegisterBusinessCommand,
    RegisterBusinessUseCase,
)
from app.business.domain.entities import Business
from app.customers.domain.entities import Customer
from app.dashboard.api.internal_routes import get_cron_secret
from app.dashboard.application.business_summary import (
    BuildBusinessSummaryUseCase,
    business_today,
    format_summary_message,
    period_range,
)
from app.dashboard.application.send_due_summaries import SendDueSummariesUseCase, summary_due
from app.expenses.application.commands.create_expense import CreateExpenseCommand, CreateExpenseUseCase
from app.expenses.domain.value_objects import PaymentMethod
from app.sales.application.commands.create_sale import (
    CreateSaleCommand,
    CreateSaleLineItemInput,
    CreateSaleUseCase,
)
from app.sales.application.commands.record_payment import RecordSalePaymentCommand, RecordSalePaymentUseCase
from app.shared.domain.exceptions import ValidationException
from app.shared.domain.phone import whatsapp_number
from tests.fakes.fake_ports import FakeClock, FakeWhatsAppSender
from tests.fakes.fake_unit_of_work import FakeUnitOfWork

# Tue 24 Nov 2026, 09:00 in India (03:30 UTC)
NOW = datetime(2026, 11, 24, 3, 30, tzinfo=timezone.utc)
TODAY = date(2026, 11, 24)
YESTERDAY = date(2026, 11, 23)


async def _business(uow: FakeUnitOfWork, **settings: object) -> Business:
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=uuid.uuid4(), name="Sharma Traders", currency="INR")
    )
    fields: dict = dict(whatsapp_number="9876543210", summary_frequency="daily")
    fields.update(settings)
    return await CompleteOnboardingUseCase(uow).execute(
        CompleteOnboardingCommand(business_id=business.id, **fields)
    )


async def _sale(uow: FakeUnitOfWork, business: Business, number: str, price: str, *, on: date, customer=None):
    return await CreateSaleUseCase(uow).execute(
        CreateSaleCommand(
            business_id=business.id,
            invoice_number=number,
            invoice_date=on,
            customer_id=customer,
            line_items=[
                CreateSaleLineItemInput(
                    line_number=1, description="Goods", quantity=Decimal("1"), unit_price=Decimal(price)
                )
            ],
        )
    )


async def _expense(uow: FakeUnitOfWork, business: Business, amount: str, *, on: date) -> None:
    await CreateExpenseUseCase(uow).execute(
        CreateExpenseCommand(
            business_id=business.id,
            expense_date=on,
            category="Rent",
            description="Shop",
            amount=Decimal(amount),
            payment_method=PaymentMethod.CASH,
        )
    )


def _customer(uow: FakeUnitOfWork, business: Business, name: str) -> uuid.UUID:
    customer = Customer.create(business_id=business.id, name=name)
    uow.customers.add(customer)
    return customer.id


# ------------------------------------------------------------------ small pieces


@pytest.mark.parametrize(
    ("raw", "currency", "expected"),
    [
        ("98765 43210", "INR", "+919876543210"),
        ("09876543210", "INR", "+919876543210"),
        ("919876543210", "INR", "+919876543210"),
        ("+91 98765-43210", "INR", "+919876543210"),
        ("+1 415 555 2671", "USD", "+14155552671"),
        ("4155552671", "USD", None),  # no country code and not a rupee business: cannot guess
        ("12345", "INR", None),
        ("", "INR", None),
        (None, "INR", None),
    ],
)
def test_phone_numbers_become_the_form_whatsapp_sending_needs(raw, currency, expected) -> None:
    assert whatsapp_number(raw, currency) == expected


def test_the_periods_cover_the_right_days() -> None:
    assert period_range("today", TODAY)[:2] == (TODAY, TODAY)
    assert period_range("yesterday", TODAY)[:2] == (YESTERDAY, YESTERDAY)
    start, end, label = period_range("week", TODAY)
    assert (start, end) == (date(2026, 11, 17), date(2026, 11, 23)) and "Last 7 days" in label


def test_a_rupee_business_goes_by_indian_time() -> None:
    # 20:00 UTC on the 23rd is already 01:30 on the 24th in India
    late = datetime(2026, 11, 23, 20, 0, tzinfo=timezone.utc)
    rupees = Business.register(owner_user_id=uuid.uuid4(), name="A", currency="INR")
    dollars = Business.register(owner_user_id=uuid.uuid4(), name="B", currency="USD")
    assert business_today(rupees, late) == TODAY
    assert business_today(dollars, late) == YESTERDAY


def test_only_known_frequencies_are_accepted() -> None:
    business = Business.register(owner_user_id=uuid.uuid4(), name="A")

    business.complete_onboarding(summary_frequency="weekly")
    assert business.summary_frequency == "weekly"
    with pytest.raises(ValidationException):
        business.complete_onboarding(summary_frequency="hourly")


def _due(frequency: str, today: date, last: date | None = None):
    business = Business.register(owner_user_id=uuid.uuid4(), name="A")
    business.summary_frequency = frequency
    business.summary_last_sent_on = last
    return summary_due(business, today)


def test_who_is_due_when() -> None:
    assert _due("off", TODAY) is None
    assert _due("daily", TODAY) == "yesterday"
    assert _due("daily", TODAY, last=YESTERDAY) == "yesterday"
    assert _due("daily", TODAY, last=TODAY) is None  # never twice in a day
    monday, tuesday, wednesday = date(2026, 11, 23), date(2026, 11, 24), date(2026, 11, 25)
    assert _due("weekly", monday) == "week"
    assert _due("weekly", tuesday) == "week"  # catches a missed Monday
    assert _due("weekly", wednesday) is None
    assert _due("weekly", tuesday, last=monday) is None  # already sent this week


# ------------------------------------------------------------------ the numbers and the text


async def test_the_summary_adds_up_a_day_and_lists_who_owes() -> None:
    uow = FakeUnitOfWork()
    business = await _business(uow)
    asha, ravi = _customer(uow, business, "Asha Stores"), _customer(uow, business, "Ravi")
    await _sale(uow, business, "INV-1", "1000", on=YESTERDAY, customer=asha)
    await _sale(uow, business, "INV-2", "500", on=YESTERDAY, customer=ravi)
    await _sale(uow, business, "INV-3", "9999", on=date(2026, 11, 1))  # another day: not in the day's sales
    await _expense(uow, business, "300", on=YESTERDAY)
    part = await _sale(uow, business, "INV-4", "400", on=date(2026, 11, 2), customer=ravi)
    await RecordSalePaymentUseCase(uow).execute(
        RecordSalePaymentCommand(business_id=business.id, sale_id=part.id, amount=Decimal("100"))
    )

    summary = await BuildBusinessSummaryUseCase(uow).execute(
        business_id=business.id, period="yesterday", today=TODAY
    )

    assert (summary.sales_total, summary.sales_count) == (Decimal("1500.00"), 2)
    assert summary.expenses_total == Decimal("300.00") and summary.profit == Decimal("1200.00")
    # Asha owes 1000, Ravi 500 + 300, and the 9999 sale has no customer
    assert [(d.name, d.amount) for d in summary.top_debtors] == [
        (None, Decimal("9999.00")),
        ("Asha Stores", Decimal("1000.00")),
        ("Ravi", Decimal("800.00")),
    ]
    assert summary.to_collect_total == Decimal("11799.00")


async def test_the_message_reads_well_for_a_rupee_business() -> None:
    uow = FakeUnitOfWork()
    business = await _business(uow)
    asha = _customer(uow, business, "Asha Stores")
    await _sale(uow, business, "INV-1", "12500", on=YESTERDAY, customer=asha)
    await _expense(uow, business, "3200", on=YESTERDAY)
    summary = await BuildBusinessSummaryUseCase(uow).execute(
        business_id=business.id, period="yesterday", today=TODAY
    )

    text = format_summary_message(summary, link="https://finverlo.com/app/dashboard")

    assert text.startswith("*Sharma Traders* - Yesterday (Mon 23 Nov)")
    assert "Sales: ₹12,500.00 (1 sale)" in text and "Expenses: ₹3,200.00" in text
    assert "Profit: ₹9,300.00" in text
    assert "To collect (udhaar): ₹12,500.00" in text and "- Asha Stores: ₹12,500.00" in text
    assert text.endswith("Open Finverlo: https://finverlo.com/app/dashboard")


async def test_a_loss_is_called_a_loss_and_no_debt_is_said_plainly() -> None:
    uow = FakeUnitOfWork()
    business = await _business(uow)
    await _expense(uow, business, "400", on=YESTERDAY)
    summary = await BuildBusinessSummaryUseCase(uow).execute(
        business_id=business.id, period="yesterday", today=TODAY
    )

    text = format_summary_message(summary, link="x")

    assert "Loss: ₹400.00" in text and "Nobody owes you anything right now." in text


# ------------------------------------------------------------------ the scheduled send


async def _run(uow: FakeUnitOfWork, sender: FakeWhatsAppSender, now: datetime = NOW):
    return await SendDueSummariesUseCase(uow, sender, app_link="https://finverlo.com/app/dashboard").execute(
        now
    )


async def test_a_due_summary_is_sent_once_and_remembered() -> None:
    uow, sender = FakeUnitOfWork(), FakeWhatsAppSender()
    business = await _business(uow)
    await _sale(uow, business, "INV-1", "100", on=YESTERDAY)

    first = await _run(uow, sender)
    second = await _run(uow, sender)

    assert (first.sent, first.skipped, first.failed) == (1, 0, 0)
    assert (second.sent, second.skipped) == (0, 1)
    assert [m["to"] for m in sender.sent] == ["+919876543210"]
    assert "Sales: ₹100.00" in sender.sent[0]["message"]
    stored = await uow.businesses.get_by_id(business.id)
    assert stored is not None and stored.summary_last_sent_on == TODAY


async def test_businesses_that_are_off_or_have_no_number_are_left_alone() -> None:
    uow, sender = FakeUnitOfWork(), FakeWhatsAppSender()
    await _business(uow, summary_frequency="off")
    await _business(uow, whatsapp_number="12345")

    result = await _run(uow, sender)

    assert result.sent == 0 and sender.sent == []


async def test_one_failing_business_does_not_stop_the_others() -> None:
    uow = FakeUnitOfWork()
    await _business(uow, whatsapp_number="9111111111")
    await _business(uow, whatsapp_number="9222222222")

    class Flaky(FakeWhatsAppSender):
        async def send(self, *, to: str, message: str) -> None:
            if to.endswith("9111111111"):
                raise RuntimeError("Twilio said no")
            await super().send(to=to, message=message)

    sender = Flaky()
    result = await _run(uow, sender)

    assert (result.sent, result.failed) == (1, 1)
    assert [m["to"] for m in sender.sent] == ["+919222222222"]


# ------------------------------------------------------------------ the scheduled endpoint


@pytest.fixture
def cron_client():
    limiter.enabled = False
    uow, sender = FakeUnitOfWork(), FakeWhatsAppSender()
    app = create_app()
    secret = {"value": "s3cret"}
    app.dependency_overrides[get_uow] = lambda: uow
    app.dependency_overrides[get_whatsapp_sender] = lambda: sender
    app.dependency_overrides[get_clock] = lambda: FakeClock(NOW)
    app.dependency_overrides[get_cron_secret] = lambda: secret["value"]
    yield TestClient(app, raise_server_exceptions=False), uow, sender, secret
    limiter.enabled = True


async def test_the_scheduled_endpoint_needs_the_secret(cron_client) -> None:
    client, uow, sender, secret = cron_client
    await _business(uow)
    url = "/api/v1/internal/summaries/send"

    assert client.post(url).status_code == 403
    assert client.post(url, headers={"X-Cron-Secret": "wrong"}).status_code == 403
    assert sender.sent == []

    ok = client.post(url, headers={"X-Cron-Secret": "s3cret"})
    assert ok.status_code == 200 and ok.json() == {"sent": 1, "skipped": 0, "failed": 0}
    assert len(sender.sent) == 1

    secret["value"] = ""  # not configured: the endpoint does not exist
    assert client.post(url, headers={"X-Cron-Secret": ""}).status_code == 404


async def test_the_message_can_be_written_in_hindi() -> None:
    uow = FakeUnitOfWork()
    business = await _business(uow)
    asha = _customer(uow, business, "Asha Stores")
    await _sale(uow, business, "INV-1", "12500", on=YESTERDAY, customer=asha)
    await _sale(uow, business, "INV-2", "100", on=date(2026, 11, 1))  # no customer
    await _expense(uow, business, "3200", on=YESTERDAY)
    summary = await BuildBusinessSummaryUseCase(uow).execute(
        business_id=business.id, period="yesterday", today=TODAY, lang="hi"
    )

    text = format_summary_message(summary, link="https://finverlo.com/app/dashboard", lang="hi")

    assert text.startswith("*Sharma Traders* - कल (सोम 23 नव)")
    assert "बिक्री: ₹12,500.00 (1 बिक्री)" in text and "खर्च: ₹3,200.00" in text
    assert "मुनाफ़ा: ₹9,300.00" in text
    assert "वसूलना है (उधार): ₹12,600.00" in text
    assert "- Asha Stores: ₹12,500.00" in text and "- बिना नाम के ग्राहक: ₹100.00" in text
    assert text.endswith("Finverlo खोलें: https://finverlo.com/app/dashboard")


def test_the_hindi_week_label_names_both_ends() -> None:
    _, _, label = period_range("week", TODAY, "hi")

    assert label == "पिछले 7 दिन (मंगल 17 नव से सोम 23 नव)"


async def test_the_scheduled_send_uses_the_businesss_language() -> None:
    uow, sender = FakeUnitOfWork(), FakeWhatsAppSender()
    await _business(uow, whatsapp_number="9111111111", language="hi")
    await _business(uow, whatsapp_number="9222222222")

    await _run(uow, sender)

    by_number = {m["to"]: m["message"] for m in sender.sent}
    assert "खर्च:" in by_number["+919111111111"]
    assert "Expenses:" in by_number["+919222222222"]


def test_only_known_languages_are_accepted() -> None:
    business = Business.register(owner_user_id=uuid.uuid4(), name="A")
    assert business.language == "en"

    business.complete_onboarding(language="hi")
    assert business.language == "hi"
    with pytest.raises(ValidationException):
        business.complete_onboarding(language="fr")
