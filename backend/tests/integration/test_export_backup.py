"""Real-Postgres test for ExportBackupUseCase and the restore path - the
row-to-dict/JSON-safety logic is exactly the kind of thing that looks right
against fakes but can break on real column types (UUID, DateTime, Numeric,
JSONB), so this is worth a real-DB check rather than only the SQLite-based
unit tests. Requires Docker; skipped automatically otherwise (see
tests/conftest.py:docker_available).
"""

import json
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.application.queries.export_backup import ExportBackupUseCase
from app.bootstrap.unit_of_work import AppUnitOfWork
from app.business.application.commands.register_business import (
    RegisterBusinessCommand,
    RegisterBusinessUseCase,
)
from app.identity.application.commands.register_user import RegisterUserCommand, RegisterUserUseCase
from app.shared.infrastructure import backup_format
from app.shared.infrastructure.clock import SystemClock
from app.shared.infrastructure.password_hasher import BcryptPasswordHasher

pytestmark = pytest.mark.integration


async def test_export_backup_serializes_a_real_business_row(db_session: AsyncSession) -> None:
    uow = AppUnitOfWork(db_session)
    owner_id = uuid.uuid4()
    business = await RegisterBusinessUseCase(uow).execute(
        RegisterBusinessCommand(owner_user_id=owner_id, name="Acme Real DB Co")
    )

    backup = await ExportBackupUseCase(db_session).execute()

    assert backup_format.verify_backup(backup, required_tables=("businesses",)) == []
    tables = backup["tables"]
    expected = {"users", "businesses", "business_memberships", "sales", "expenses", "business_audit_events"}
    assert expected <= set(tables)
    assert "outbox_messages" not in tables
    assert len(tables["businesses"]) == 1
    row = tables["businesses"][0]
    assert row["id"] == str(business.id)
    assert row["owner_user_id"] == str(owner_id)
    assert row["name"] == "Acme Real DB Co"
    assert row["plan"] == "free"
    # created_at must be JSON-safe (a string), not a raw datetime object.
    assert isinstance(row["created_at"], str)
    json.dumps(backup)  # the whole document must serialise

    assert len(tables["business_memberships"]) == 1
    assert tables["business_memberships"][0]["business_id"] == str(business.id)
    assert tables["business_memberships"][0]["role"] == "owner"


async def test_export_backup_excludes_one_time_tokens_but_keeps_the_password_hash(
    db_session: AsyncSession,
) -> None:
    uow = AppUnitOfWork(db_session)
    await RegisterUserUseCase(uow, BcryptPasswordHasher(), SystemClock()).execute(
        RegisterUserCommand(email="jane@example.com", password="Sup3rSecret!", display_name="Jane")
    )

    backup = await ExportBackupUseCase(db_session).execute()

    (row,) = backup["tables"]["users"]
    assert row["email"] == "jane@example.com"
    assert row["password_hash"].startswith("$2b$")  # needed to restore working logins
    for token_field in ("email_verification_token_hash", "password_reset_token_hash"):
        assert token_field not in row
