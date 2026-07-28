import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.identity.domain.entities import User
from app.identity.domain.value_objects import Role


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str
    role: Role
    is_active: bool
    created_at: datetime

    @classmethod
    def from_domain(cls, user: User) -> "UserResponse":
        return cls(
            id=user.id,
            email=str(user.email),
            display_name=user.display_name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
        )


class PagedUsersResponse(BaseModel):
    items: list[UserResponse]
    total: int
    offset: int
    limit: int


class AssignRoleRequest(BaseModel):
    role: Role
