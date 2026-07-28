from dataclasses import dataclass
from datetime import datetime

from app.identity.application.ports import IdentityUnitOfWork
from app.identity.domain.entities import User
from app.identity.domain.exceptions import (
    EmailNotVerifiedException,
    InvalidCredentialsException,
    UserDeactivatedException,
)
from app.identity.domain.value_objects import AuthProvider
from app.identity.infrastructure.local_auth.token_issuer import LocalTokenIssuer
from app.shared.application.ports import IPasswordHasher


@dataclass(frozen=True)
class LoginUserCommand:
    email: str
    password: str


@dataclass(frozen=True)
class LoginResult:
    user: User
    access_token: str
    expires_at: datetime


class LoginUserUseCase:
    """Local (email+password) login for the SMB Finance Manager product.
    Deliberately raises the same InvalidCredentialsException whether the
    email doesn't exist, the password is wrong, or the account was
    provisioned via Entra ID rather than registered locally — never reveals
    which, to avoid user enumeration.
    """

    def __init__(
        self,
        uow: IdentityUnitOfWork,
        password_hasher: IPasswordHasher,
        token_issuer: LocalTokenIssuer,
    ) -> None:
        self._uow = uow
        self._password_hasher = password_hasher
        self._token_issuer = token_issuer

    async def execute(self, command: LoginUserCommand) -> LoginResult:
        user = await self._uow.users.get_by_email(command.email)
        if (
            user is None
            or user.auth_provider != AuthProvider.LOCAL
            or user.password_hash is None
            or not self._password_hasher.verify(command.password, user.password_hash)
        ):
            raise InvalidCredentialsException("Invalid email or password")

        if not user.is_email_verified:
            raise EmailNotVerifiedException("Please verify your email before logging in")
        if not user.is_active:
            raise UserDeactivatedException(f"User {user.id} is deactivated")

        access_token, expires_at = self._token_issuer.issue(user_id=user.id)
        return LoginResult(user=user, access_token=access_token, expires_at=expires_at)
