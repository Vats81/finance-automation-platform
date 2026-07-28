from app.identity.domain.entities import User
from app.identity.domain.value_objects import AuthProvider, EmailAddress, Role
from app.identity.infrastructure.models import UserModel


def model_to_domain(model: UserModel) -> User:
    return User(
        entity_id=model.id,
        entra_object_id=model.entra_object_id,
        email=EmailAddress(model.email),
        display_name=model.display_name,
        role=Role(model.role),
        auth_provider=AuthProvider(model.auth_provider),
        password_hash=model.password_hash,
        is_email_verified=model.is_email_verified,
        email_verification_token_hash=model.email_verification_token_hash,
        email_verification_expires_at=model.email_verification_expires_at,
        password_reset_token_hash=model.password_reset_token_hash,
        password_reset_expires_at=model.password_reset_expires_at,
        is_active=model.is_active,
        is_platform_admin=model.is_platform_admin,
        created_at=model.created_at,
    )


def domain_to_model(user: User) -> UserModel:
    return UserModel(
        id=user.id,
        entra_object_id=user.entra_object_id,
        email=str(user.email),
        display_name=user.display_name,
        role=user.role.value,
        auth_provider=user.auth_provider.value,
        password_hash=user.password_hash,
        is_email_verified=user.is_email_verified,
        email_verification_token_hash=user.email_verification_token_hash,
        email_verification_expires_at=user.email_verification_expires_at,
        password_reset_token_hash=user.password_reset_token_hash,
        password_reset_expires_at=user.password_reset_expires_at,
        is_active=user.is_active,
        is_platform_admin=user.is_platform_admin,
        created_at=user.created_at,
    )


def apply_domain_to_existing_model(user: User, model: UserModel) -> None:
    """In-place update for `update()` calls, so SQLAlchemy's unit-of-work
    tracks field-level changes instead of replacing the row wholesale.
    """
    model.display_name = user.display_name
    model.role = user.role.value
    model.is_active = user.is_active
    model.is_platform_admin = user.is_platform_admin
    model.password_hash = user.password_hash
    model.is_email_verified = user.is_email_verified
    model.email_verification_token_hash = user.email_verification_token_hash
    model.email_verification_expires_at = user.email_verification_expires_at
    model.password_reset_token_hash = user.password_reset_token_hash
    model.password_reset_expires_at = user.password_reset_expires_at
