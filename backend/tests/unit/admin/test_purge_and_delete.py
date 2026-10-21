import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import app.main  # noqa: F401 - imports every model so Base.metadata is complete
from app.admin.application.commands.delete_user import DeleteUserCommand, DeleteUserUseCase
from app.admin.application.commands.purge_business import (
    BUSINESS_SCOPED_MODELS,
    PurgeBusinessCommand,
    PurgeBusinessUseCase,
)
from app.business.domain.exceptions import BusinessNotFoundException
from app.identity.domain.exceptions import UserNotFoundException
from app.shared.domain.exceptions import ConflictException, ValidationException
from app.shared.infrastructure.db.base import Base

ACTOR = uuid.uuid4()


def test_every_business_scoped_table_is_covered_by_the_purge() -> None:
    covered = {m.__tablename__ for m in BUSINESS_SCOPED_MODELS}  # type: ignore[attr-defined]
    scoped = {name for name, table in Base.metadata.tables.items() if "business_id" in table.c}

    assert scoped == covered, f"Add new business-scoped tables to the purge: {scoped - covered}"


def _session(get_result: object | None, owned_names: list[str] | None = None) -> MagicMock:
    session = MagicMock()
    session.get = AsyncMock(return_value=get_result)
    session.execute = AsyncMock()
    session.delete = AsyncMock()
    session.commit = AsyncMock()
    if owned_names is not None:
        result = MagicMock()
        result.all.return_value = [(n,) for n in owned_names]
        session.execute.return_value = result
    return session


async def test_purge_unknown_business_is_not_found() -> None:
    with pytest.raises(BusinessNotFoundException):
        await PurgeBusinessUseCase(_session(None)).execute(
            PurgeBusinessCommand(business_id=uuid.uuid4(), confirm_name="x", actor_user_id=ACTOR)
        )


async def test_purge_requires_the_exact_business_name() -> None:
    session = _session(SimpleNamespace(name="Acme Co"))

    with pytest.raises(ValidationException):
        await PurgeBusinessUseCase(session).execute(
            PurgeBusinessCommand(business_id=uuid.uuid4(), confirm_name="acme", actor_user_id=ACTOR)
        )

    session.execute.assert_not_called()
    session.commit.assert_not_called()


async def test_purge_removes_every_scoped_table_then_the_business() -> None:
    business = SimpleNamespace(name="Acme Co")
    session = _session(business)

    await PurgeBusinessUseCase(session).execute(
        PurgeBusinessCommand(business_id=uuid.uuid4(), confirm_name=" Acme Co ", actor_user_id=ACTOR)
    )

    assert session.execute.await_count == len(BUSINESS_SCOPED_MODELS)
    session.delete.assert_awaited_once_with(business)
    session.commit.assert_awaited_once()


def _user() -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), email="qa@example.com", is_platform_admin=False)


async def test_delete_user_refuses_self_admins_and_wrong_confirmation() -> None:
    user = _user()
    with pytest.raises(ValidationException):
        await DeleteUserUseCase(_session(user, [])).execute(
            DeleteUserCommand(user_id=user.id, confirm_email="qa@example.com", actor_user_id=user.id)
        )

    admin = SimpleNamespace(id=uuid.uuid4(), email="a@example.com", is_platform_admin=True)
    with pytest.raises(ValidationException):
        await DeleteUserUseCase(_session(admin, [])).execute(
            DeleteUserCommand(user_id=admin.id, confirm_email="a@example.com", actor_user_id=ACTOR)
        )

    with pytest.raises(ValidationException):
        await DeleteUserUseCase(_session(user, [])).execute(
            DeleteUserCommand(user_id=user.id, confirm_email="other@example.com", actor_user_id=ACTOR)
        )


async def test_delete_user_unknown_user_is_not_found() -> None:
    with pytest.raises(UserNotFoundException):
        await DeleteUserUseCase(_session(None)).execute(
            DeleteUserCommand(user_id=uuid.uuid4(), confirm_email="x", actor_user_id=ACTOR)
        )


async def test_delete_user_refuses_while_they_still_own_a_business() -> None:
    user = _user()
    session = _session(user, ["Acme Co"])

    with pytest.raises(ConflictException):
        await DeleteUserUseCase(session).execute(
            DeleteUserCommand(user_id=user.id, confirm_email="QA@example.com", actor_user_id=ACTOR)
        )

    session.commit.assert_not_called()


async def test_delete_user_removes_memberships_and_the_user() -> None:
    user = _user()
    session = _session(user, [])

    await DeleteUserUseCase(session).execute(
        DeleteUserCommand(user_id=user.id, confirm_email="QA@example.com", actor_user_id=ACTOR)
    )

    session.delete.assert_awaited_once_with(user)
    session.commit.assert_awaited_once()
