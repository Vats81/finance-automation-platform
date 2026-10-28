import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import app.main  # noqa: F401 - imports every model so Base.metadata is complete
from app.admin.application.commands.purge_firm import PurgeFirmCommand, PurgeFirmUseCase
from app.firms.domain.exceptions import FirmNotFoundException
from app.shared.domain.exceptions import ConflictException, ValidationException

ACTOR = uuid.uuid4()


def _session(firm: object | None, clients: int = 0) -> MagicMock:
    session = MagicMock()
    session.get = AsyncMock(return_value=firm)
    count = MagicMock()
    count.scalar_one.return_value = clients
    session.execute = AsyncMock(return_value=count)
    session.delete = AsyncMock()
    session.commit = AsyncMock()
    return session


def _command(name: str = "Ledger & Co") -> PurgeFirmCommand:
    return PurgeFirmCommand(firm_id=uuid.uuid4(), confirm_name=name, actor_user_id=ACTOR)


async def test_purging_an_unknown_firm_is_not_found() -> None:
    with pytest.raises(FirmNotFoundException):
        await PurgeFirmUseCase(_session(None)).execute(_command())


async def test_the_exact_firm_name_is_required() -> None:
    session = _session(SimpleNamespace(id=uuid.uuid4(), name="Ledger & Co"))

    with pytest.raises(ValidationException):
        await PurgeFirmUseCase(session).execute(_command("ledger"))

    session.delete.assert_not_called()
    session.commit.assert_not_called()


async def test_a_firm_with_clients_is_refused_and_nothing_is_deleted() -> None:
    session = _session(SimpleNamespace(id=uuid.uuid4(), name="Ledger & Co"), clients=2)

    with pytest.raises(ConflictException):
        await PurgeFirmUseCase(session).execute(_command())

    session.delete.assert_not_called()
    session.commit.assert_not_called()


async def test_an_empty_firm_is_deleted_with_its_staff_memberships() -> None:
    firm = SimpleNamespace(id=uuid.uuid4(), name="Ledger & Co")
    session = _session(firm)

    await PurgeFirmUseCase(session).execute(_command(" Ledger & Co "))

    assert session.execute.await_count == 3  # the client count, the memberships, the audit trail
    session.delete.assert_awaited_once_with(firm)
    session.commit.assert_awaited_once()
