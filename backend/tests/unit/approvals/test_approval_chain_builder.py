from decimal import Decimal

from app.approvals.domain.services import ApprovalChainBuilder
from app.approvals.domain.value_objects import ApprovalThreshold
from app.identity.domain.value_objects import Role
from app.shared.domain.value_objects import Money


def make_builder(l1: str = "1000.00", l2: str = "10000.00") -> ApprovalChainBuilder:
    threshold = ApprovalThreshold(
        l1_max_cents=Money(amount=Decimal(l1)).cents, l2_max_cents=Money(amount=Decimal(l2)).cents
    )
    return ApprovalChainBuilder(threshold)


def test_amount_at_or_below_l1_requires_single_approver() -> None:
    builder = make_builder()

    chain = builder.build_chain(Money(amount=Decimal("500.00")))

    assert chain == [Role.APPROVER]


def test_amount_between_l1_and_l2_requires_approver_then_finance_admin() -> None:
    builder = make_builder()

    chain = builder.build_chain(Money(amount=Decimal("5000.00")))

    assert chain == [Role.APPROVER, Role.FINANCE_ADMIN]


def test_amount_above_l2_requires_dual_finance_admin_sign_off() -> None:
    builder = make_builder()

    chain = builder.build_chain(Money(amount=Decimal("50000.00")))

    assert chain == [Role.APPROVER, Role.FINANCE_ADMIN, Role.FINANCE_ADMIN]


def test_amount_exactly_at_threshold_boundary_uses_lower_tier() -> None:
    builder = make_builder(l1="1000.00", l2="10000.00")

    chain = builder.build_chain(Money(amount=Decimal("1000.00")))

    assert chain == [Role.APPROVER]
