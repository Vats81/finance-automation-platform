"""The private invoice link: an unguessable token, only its hash stored, with an expiry and revocation."""

import uuid
from datetime import datetime, timedelta, timezone

from app.sales.domain.share_link import (
    SHARE_LINK_DAYS,
    InvoiceShareLink,
    hash_share_token,
    new_share_token,
)

NOW = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)


def _link() -> tuple[InvoiceShareLink, str]:
    return InvoiceShareLink.issue(business_id=uuid.uuid4(), sale_id=uuid.uuid4(), now=NOW)


def test_the_token_is_not_stored_only_its_hash_is() -> None:
    link, token = _link()

    assert link.token_hash == hash_share_token(token)
    assert token not in link.token_hash and len(link.token_hash) == 64


def test_tokens_are_long_and_never_repeat() -> None:
    tokens = {new_share_token() for _ in range(200)}

    assert len(tokens) == 200
    assert all(len(t) >= 32 for t in tokens)


def test_a_new_link_is_active_until_it_expires() -> None:
    link, _ = _link()

    assert link.is_active(NOW)
    assert link.is_active(NOW + timedelta(days=SHARE_LINK_DAYS) - timedelta(seconds=1))
    assert not link.is_active(NOW + timedelta(days=SHARE_LINK_DAYS))


def test_a_revoked_link_stops_working_and_revoking_twice_changes_nothing() -> None:
    link, _ = _link()

    link.revoke(NOW)
    first = link.revoked_at
    link.revoke(NOW + timedelta(days=1))

    assert not link.is_active(NOW)
    assert link.revoked_at == first
