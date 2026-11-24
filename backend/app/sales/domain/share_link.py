import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from app.shared.domain.base_entity import Entity

# An invoice link sent on WhatsApp should keep working while the customer pays, but not forever.
SHARE_LINK_DAYS = 60


def hash_share_token(token: str) -> str:
    """Only this hash is stored, so a copy of the database cannot be used to open anyone's invoice."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_share_token() -> str:
    """A fresh unguessable token (192 bits), safe to put in a URL."""
    return secrets.token_urlsafe(24)


class InvoiceShareLink(Entity):
    """A private link to one invoice's PDF, for sending to the customer. Whoever holds the link can open
    that invoice and nothing else; it stops working when it expires or when the owner revokes it.
    """

    def __init__(
        self,
        *,
        entity_id: uuid.UUID | None = None,
        business_id: uuid.UUID,
        sale_id: uuid.UUID,
        token_hash: str,
        created_at: datetime | None = None,
        expires_at: datetime,
        revoked_at: datetime | None = None,
    ) -> None:
        super().__init__(entity_id)
        self.business_id = business_id
        self.sale_id = sale_id
        self.token_hash = token_hash
        self.created_at = created_at or datetime.now(timezone.utc)
        self.expires_at = expires_at
        self.revoked_at = revoked_at

    @classmethod
    def issue(
        cls, *, business_id: uuid.UUID, sale_id: uuid.UUID, now: datetime | None = None
    ) -> tuple["InvoiceShareLink", str]:
        """The new link and the token to give out. The token is not kept anywhere on our side."""
        now = now or datetime.now(timezone.utc)
        token = new_share_token()
        link = cls(
            business_id=business_id,
            sale_id=sale_id,
            token_hash=hash_share_token(token),
            created_at=now,
            expires_at=now + timedelta(days=SHARE_LINK_DAYS),
        )
        return link, token

    def revoke(self, now: datetime | None = None) -> None:
        if self.revoked_at is None:
            self.revoked_at = now or datetime.now(timezone.utc)

    def is_active(self, now: datetime | None = None) -> bool:
        return self.revoked_at is None and (now or datetime.now(timezone.utc)) < self.expires_at
