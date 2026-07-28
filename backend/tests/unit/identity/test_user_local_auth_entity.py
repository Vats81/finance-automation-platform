from datetime import datetime, timedelta, timezone

import pytest

from app.identity.domain.entities import User
from app.identity.domain.exceptions import InvalidOrExpiredTokenException
from app.identity.domain.value_objects import AuthProvider, EmailAddress


def make_registered_user(*, token: str = "raw-token", ttl_hours: int = 24) -> User:
    user = User.register(
        email=EmailAddress("owner@acme.com"),
        display_name="Ada Owner",
        password_hash="hashed:pw",
        verification_token=token,
        verification_expires_at=datetime.now(timezone.utc) + timedelta(hours=ttl_hours),
    )
    user.pull_domain_events()
    return user


def test_register_defaults_to_local_unverified_and_records_event() -> None:
    user = User.register(
        email=EmailAddress("owner@acme.com"),
        display_name="Ada Owner",
        password_hash="hashed:pw",
        verification_token="raw-token",
        verification_expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )

    assert user.auth_provider == AuthProvider.LOCAL
    assert user.is_email_verified is False
    assert user.is_platform_admin is False
    events = user.pull_domain_events()
    assert [e.event_type for e in events] == ["UserRegistered"]
    assert events[0].verification_token == "raw-token"


def test_verify_email_with_correct_token_marks_verified() -> None:
    user = make_registered_user(token="correct-token")

    user.verify_email(token="correct-token", now=datetime.now(timezone.utc))

    assert user.is_email_verified is True
    assert user.email_verification_token_hash is None
    events = user.pull_domain_events()
    assert [e.event_type for e in events] == ["EmailVerified"]


def test_verify_email_with_wrong_token_raises() -> None:
    user = make_registered_user(token="correct-token")

    with pytest.raises(InvalidOrExpiredTokenException):
        user.verify_email(token="wrong-token", now=datetime.now(timezone.utc))


def test_verify_email_after_expiry_raises() -> None:
    user = make_registered_user(token="correct-token", ttl_hours=1)
    the_future = datetime.now(timezone.utc) + timedelta(hours=2)

    with pytest.raises(InvalidOrExpiredTokenException):
        user.verify_email(token="correct-token", now=the_future)


def test_request_and_complete_password_reset() -> None:
    user = make_registered_user()
    user.verify_email(token="raw-token", now=datetime.now(timezone.utc))
    user.pull_domain_events()

    user.request_password_reset(
        reset_token="reset-token", expires_at=datetime.now(timezone.utc) + timedelta(hours=2)
    )
    events = user.pull_domain_events()
    assert [e.event_type for e in events] == ["PasswordResetRequested"]

    user.reset_password(
        token="reset-token", new_password_hash="hashed:new-pw", now=datetime.now(timezone.utc)
    )

    assert user.password_hash == "hashed:new-pw"
    assert user.password_reset_token_hash is None
    events = user.pull_domain_events()
    assert [e.event_type for e in events] == ["PasswordWasReset"]


def test_reset_password_with_wrong_token_raises() -> None:
    user = make_registered_user()
    user.request_password_reset(
        reset_token="reset-token", expires_at=datetime.now(timezone.utc) + timedelta(hours=2)
    )

    with pytest.raises(InvalidOrExpiredTokenException):
        user.reset_password(token="nope", new_password_hash="hashed:new-pw", now=datetime.now(timezone.utc))
