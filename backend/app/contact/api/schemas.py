import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.contact.application.ports import ContactRequest


class SubmitContactRequestBody(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    business_name: str | None = Field(default=None, max_length=200)
    message: str | None = Field(default=None, max_length=2000)
    # Honeypot: a real visitor never sees or fills this (the form hides it);
    # bots that fill every field do. A filled value is silently dropped.
    website: str | None = Field(default=None, max_length=500)


class ContactReceivedResponse(BaseModel):
    received: bool = True


class ContactRequestResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    business_name: str | None
    message: str | None
    notified: bool
    created_at: datetime

    @classmethod
    def from_domain(cls, request: ContactRequest) -> "ContactRequestResponse":
        return cls(
            id=request.id,
            name=request.name,
            email=request.email,
            business_name=request.business_name,
            message=request.message,
            notified=request.notified,
            created_at=request.created_at,
        )


class ContactRequestsResponse(BaseModel):
    items: list[ContactRequestResponse]
