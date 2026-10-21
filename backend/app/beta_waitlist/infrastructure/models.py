import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.infrastructure.db.base import Base


class BetaWaitlistEntryModel(Base):
    """Interest in the private beta. Deliberately separate from users: an entry
    grants no access and creates no account. No bank details or financial files
    are ever collected here.
    """

    __tablename__ = "beta_waitlist_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    work_email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)  # stored lowercased
    business_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    business_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bookkeeping_method: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reporting_problem: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    weekly_feedback_ok: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="interested", index=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
