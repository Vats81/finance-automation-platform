import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.identity.domain.entities import User


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=255)


class LocalUserResponse(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    is_email_verified: bool
    is_active: bool
    is_platform_admin: bool
    created_at: datetime

    @classmethod
    def from_domain(cls, user: User) -> "LocalUserResponse":
        return cls(
            id=user.id,
            email=str(user.email),
            display_name=user.display_name,
            is_email_verified=user.is_email_verified,
            is_active=user.is_active,
            is_platform_admin=user.is_platform_admin,
            created_at=user.created_at,
        )


class VerifyEmailRequest(BaseModel):
    user_id: uuid.UUID
    token: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    expires_at: datetime
    user: LocalUserResponse


class RequestPasswordResetRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    user_id: uuid.UUID
    token: str
    new_password: str = Field(min_length=8, max_length=128)
