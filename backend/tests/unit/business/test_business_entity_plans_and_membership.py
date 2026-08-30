import uuid

from app.business.domain.entities import Business, BusinessMembership
from app.business.domain.value_objects import BusinessPlan, BusinessRole, BusinessStatus, MembershipStatus


def test_change_plan_is_a_noop_when_unchanged() -> None:
    business = Business.register(owner_user_id=uuid.uuid4(), name="Acme")
    business.pull_domain_events()

    business.change_plan(plan=BusinessPlan.FREE)

    assert business.plan == BusinessPlan.FREE
    assert business.pull_domain_events() == []


def test_change_plan_records_event_when_changed() -> None:
    business = Business.register(owner_user_id=uuid.uuid4(), name="Acme")
    business.pull_domain_events()

    business.change_plan(plan=BusinessPlan.STARTER)

    assert business.plan == BusinessPlan.STARTER
    events = business.pull_domain_events()
    assert len(events) == 1
    assert events[0].old_plan == "free"
    assert events[0].new_plan == "starter"


def test_suspend_records_event() -> None:
    business = Business.register(owner_user_id=uuid.uuid4(), name="Acme")
    business.pull_domain_events()

    business.suspend()

    assert business.status == BusinessStatus.SUSPENDED
    events = business.pull_domain_events()
    assert [e.event_type for e in events] == ["BusinessSuspended"]


def test_reactivate_records_no_event() -> None:
    business = Business.register(owner_user_id=uuid.uuid4(), name="Acme")
    business.suspend()
    business.pull_domain_events()

    business.reactivate()

    assert business.status == BusinessStatus.ACTIVE
    assert business.pull_domain_events() == []


def test_invite_creates_active_membership_with_inviter_recorded() -> None:
    business_id = uuid.uuid4()
    user_id = uuid.uuid4()
    inviter_id = uuid.uuid4()

    membership = BusinessMembership.invite(
        business_id=business_id, user_id=user_id, role=BusinessRole.ACCOUNTANT, invited_by_user_id=inviter_id
    )

    assert membership.status == MembershipStatus.ACTIVE
    assert membership.joined_at is not None
    assert membership.invited_by_user_id == inviter_id
    assert membership.role == BusinessRole.ACCOUNTANT
    assert membership.is_active is True


def test_remove_is_a_noop_when_already_removed() -> None:
    membership = BusinessMembership.invite(
        business_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        role=BusinessRole.VIEWER,
        invited_by_user_id=uuid.uuid4(),
    )
    membership.pull_domain_events()
    membership.remove()
    membership.pull_domain_events()

    membership.remove()

    assert membership.status == MembershipStatus.REMOVED
    assert membership.pull_domain_events() == []


def test_change_role_is_a_noop_when_unchanged() -> None:
    membership = BusinessMembership.invite(
        business_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        role=BusinessRole.VIEWER,
        invited_by_user_id=uuid.uuid4(),
    )
    membership.pull_domain_events()

    membership.change_role(role=BusinessRole.VIEWER)

    assert membership.pull_domain_events() == []


def test_change_role_records_event_when_changed() -> None:
    membership = BusinessMembership.invite(
        business_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        role=BusinessRole.VIEWER,
        invited_by_user_id=uuid.uuid4(),
    )
    membership.pull_domain_events()

    membership.change_role(role=BusinessRole.ADMIN)

    assert membership.role == BusinessRole.ADMIN
    events = membership.pull_domain_events()
    assert len(events) == 1
    assert events[0].old_role == "viewer"
    assert events[0].new_role == "admin"


def test_attach_stripe_customer_sets_field_and_records_no_event() -> None:
    business = Business.register(owner_user_id=uuid.uuid4(), name="Acme")
    business.pull_domain_events()

    business.attach_stripe_customer(customer_id="cus_123")

    assert business.stripe_customer_id == "cus_123"
    assert business.pull_domain_events() == []


def test_activate_subscription_sets_subscription_id_and_plan() -> None:
    business = Business.register(owner_user_id=uuid.uuid4(), name="Acme")
    business.pull_domain_events()

    business.activate_subscription(subscription_id="sub_123", plan=BusinessPlan.PRO)

    assert business.stripe_subscription_id == "sub_123"
    assert business.plan == BusinessPlan.PRO
    events = business.pull_domain_events()
    assert len(events) == 1
    assert events[0].new_plan == "pro"


def test_cancel_subscription_clears_subscription_id_and_resets_to_free() -> None:
    business = Business.register(owner_user_id=uuid.uuid4(), name="Acme")
    business.activate_subscription(subscription_id="sub_123", plan=BusinessPlan.STARTER)
    business.pull_domain_events()

    business.cancel_subscription()

    assert business.stripe_subscription_id is None
    assert business.plan == BusinessPlan.FREE
    events = business.pull_domain_events()
    assert len(events) == 1
    assert events[0].new_plan == "free"
