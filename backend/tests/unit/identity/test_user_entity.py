import pytest

from app.identity.domain.entities import User
from app.identity.domain.exceptions import UserDeactivatedException
from app.identity.domain.value_objects import EmailAddress, Role


def make_user(role: Role = Role.AP_CLERK) -> User:
    user = User.provision(
        entra_object_id="oid-1", email=EmailAddress("a@b.com"), display_name="A B"
    )
    user.pull_domain_events()
    user.role = role
    return user


def test_provision_defaults_to_ap_clerk_and_records_event() -> None:
    user = User.provision(entra_object_id="oid-1", email=EmailAddress("a@b.com"), display_name="A B")

    assert user.role == Role.AP_CLERK
    events = user.pull_domain_events()
    assert len(events) == 1
    assert events[0].event_type == "UserProvisioned"
    assert user.has_pending_events is False


def test_provision_defaults_to_not_a_platform_admin() -> None:
    user = User.provision(entra_object_id="oid-1", email=EmailAddress("a@b.com"), display_name="A B")

    assert user.is_platform_admin is False


def test_change_role_records_event_with_previous_and_new_role() -> None:
    user = make_user(Role.AP_CLERK)

    user.change_role(new_role=Role.APPROVER, changed_by_user_id=user.id)

    events = user.pull_domain_events()
    assert len(events) == 1
    assert events[0].previous_role == "ap_clerk"
    assert events[0].new_role == "approver"
    assert user.role == Role.APPROVER


def test_change_role_to_same_role_is_a_noop() -> None:
    user = make_user(Role.APPROVER)

    user.change_role(new_role=Role.APPROVER, changed_by_user_id=user.id)

    assert user.pull_domain_events() == []


def test_deactivated_user_cannot_have_role_changed() -> None:
    user = make_user(Role.AP_CLERK)
    user.deactivate()

    with pytest.raises(UserDeactivatedException):
        user.change_role(new_role=Role.APPROVER, changed_by_user_id=user.id)


def test_has_role_false_when_deactivated_even_if_role_matches() -> None:
    user = make_user(Role.FINANCE_ADMIN)
    user.deactivate()

    assert user.has_role(Role.FINANCE_ADMIN) is False


def test_deactivate_records_event() -> None:
    user = make_user(Role.AP_CLERK)

    user.deactivate()

    assert user.is_active is False
    events = user.pull_domain_events()
    assert [e.event_type for e in events] == ["UserDeactivated"]


def test_reactivate_records_no_event() -> None:
    user = make_user(Role.AP_CLERK)
    user.deactivate()
    user.pull_domain_events()

    user.reactivate()

    assert user.is_active is True
    assert user.pull_domain_events() == []


def test_invalid_email_raises_validation_exception() -> None:
    from app.shared.domain.exceptions import ValidationException

    with pytest.raises(ValidationException):
        EmailAddress("not-an-email")
