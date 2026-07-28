import pytest

from app.identity.api.dependencies import require_platform_admin
from app.identity.domain.entities import User
from app.identity.domain.value_objects import EmailAddress
from app.shared.domain.exceptions import UnauthorizedDomainActionException


def make_user(*, is_platform_admin: bool) -> User:
    user = User.provision(entra_object_id="oid-1", email=EmailAddress("a@b.com"), display_name="A B")
    user.is_platform_admin = is_platform_admin
    return user


async def test_require_platform_admin_allows_platform_admin() -> None:
    admin_user = make_user(is_platform_admin=True)

    result = await require_platform_admin(current_user=admin_user)

    assert result is admin_user


async def test_require_platform_admin_rejects_non_admin() -> None:
    regular_user = make_user(is_platform_admin=False)

    with pytest.raises(UnauthorizedDomainActionException):
        await require_platform_admin(current_user=regular_user)
