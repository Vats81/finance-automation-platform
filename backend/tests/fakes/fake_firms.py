import uuid
from dataclasses import replace
from datetime import datetime, timezone

from app.firms.application.ports import FirmMemberRecord, FirmRecord, IFirmRepository
from app.firms.domain.value_objects import FirmMembershipStatus, FirmRole, FirmStatus


class FakeFirmRepository(IFirmRepository):
    def __init__(self) -> None:
        self.firms: dict[uuid.UUID, FirmRecord] = {}
        self.members: dict[uuid.UUID, FirmMemberRecord] = {}
        self.activity: dict[uuid.UUID, datetime] = {}

    async def create_firm(self, *, name: str, owner_user_id: uuid.UUID) -> FirmRecord:
        firm = FirmRecord(
            id=uuid.uuid4(),
            name=name,
            owner_user_id=owner_user_id,
            status=FirmStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
        )
        self.firms[firm.id] = firm
        member = FirmMemberRecord(
            id=uuid.uuid4(),
            firm_id=firm.id,
            user_id=owner_user_id,
            role=FirmRole.OWNER,
            status=FirmMembershipStatus.ACTIVE,
            invited_by_user_id=None,
            joined_at=datetime.now(timezone.utc),
        )
        self.members[member.id] = member
        return firm

    async def get_firm(self, firm_id: uuid.UUID) -> FirmRecord | None:
        return self.firms.get(firm_id)

    async def get_membership(self, firm_id: uuid.UUID, user_id: uuid.UUID) -> FirmMemberRecord | None:
        return next((m for m in self.members.values() if m.firm_id == firm_id and m.user_id == user_id), None)

    async def get_membership_by_id(self, membership_id: uuid.UUID) -> FirmMemberRecord | None:
        return self.members.get(membership_id)

    async def list_active_memberships_for_user(self, user_id: uuid.UUID) -> list[FirmMemberRecord]:
        return [m for m in self.members.values() if m.user_id == user_id and m.is_active]

    async def list_members(self, firm_id: uuid.UUID) -> list[FirmMemberRecord]:
        return [m for m in self.members.values() if m.firm_id == firm_id]

    async def add_member(
        self, *, firm_id: uuid.UUID, user_id: uuid.UUID, role: FirmRole, invited_by_user_id: uuid.UUID
    ) -> FirmMemberRecord:
        member = FirmMemberRecord(
            id=uuid.uuid4(),
            firm_id=firm_id,
            user_id=user_id,
            role=role,
            status=FirmMembershipStatus.ACTIVE,
            invited_by_user_id=invited_by_user_id,
            joined_at=datetime.now(timezone.utc),
        )
        self.members[member.id] = member
        return member

    async def update_member(
        self,
        membership_id: uuid.UUID,
        *,
        role: FirmRole | None = None,
        status: FirmMembershipStatus | None = None,
        invited_by_user_id: uuid.UUID | None = None,
    ) -> FirmMemberRecord | None:
        current = self.members.get(membership_id)
        if current is None:
            return None
        updated = replace(
            current,
            role=role or current.role,
            status=status or current.status,
            invited_by_user_id=invited_by_user_id or current.invited_by_user_id,
        )
        self.members[membership_id] = updated
        return updated

    async def last_activity_by_business(self, business_ids: list[uuid.UUID]) -> dict[uuid.UUID, datetime]:
        return {b: self.activity[b] for b in business_ids if b in self.activity}
