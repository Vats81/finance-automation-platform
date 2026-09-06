"""Real-Postgres test for ExportBackupUseCase — the row-to-dict/JSON-safety
logic is exactly the kind of thing that looks right against fakes but can
break on real column types (UUID, DateTime, Numeric), so this is worth a
real-DB check rather than only a fakes-based unit test. Requires Docker;
skipped automatically otherwise (see tests/conftest.py:docker_available).
"""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.application.queries.export_backup import ExportBackupUseCase
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.application.commands.register_business import (
    RegisterBusinessCommand,
    RegisterBusinessUseCase,
)

pytestmark = pytest.mark.integration


async def test_export_backup_serializes_a_real_business_row(db_session: AsyncSession) -> None:
    uow = AppUnitOfWork(db_session)
    owner_id = uuid.uuid4()
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=owner_id, name="Acme Real DB Co")
    )

    backup = await ExportBackupUseCase(db_session).execute()

    assert set(backup.keys()) == {
        "users",
        "businesses",
        "business_memberships",
        "customers",
        "vendors",
        "products",
        "sales",
        "purchases",
        "expenses",
    }
    business_rows = backup["businesses"]
    assert len(business_rows) == 1
    row = business_rows[0]
    assert row["id"] == str(business.id)
    assert row["owner_user_id"] == str(owner_id)
    assert row["name"] == "Acme Real DB Co"
    assert row["plan"] == "free"
    # created_at must be JSON-safe (a string), not a raw datetime object.
    assert isinstance(row["created_at"], str)

    membership_rows = backup["business_memberships"]
    assert len(membership_rows) == 1
    assert membership_rows[0]["business_id"] == str(business.id)
    assert membership_rows[0]["role"] == "owner"
