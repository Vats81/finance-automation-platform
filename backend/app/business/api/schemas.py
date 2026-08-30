import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.business.application.queries.list_my_businesses import MyBusinessView
from app.business.application.queries.list_team_members import TeamMemberView
from app.business.domain.entities import Business
from app.business.domain.value_objects import BusinessPlan, BusinessRole, BusinessStatus, MembershipStatus


class RegisterBusinessRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class CompleteOnboardingRequest(BaseModel):
    business_type: str | None = None
    industry: str | None = None
    country: str | None = None
    currency: str | None = None
    financial_year_start_month: int | None = Field(default=None, ge=1, le=12)
    gst_registered: bool | None = None
    business_size: str | None = None
    number_of_branches: int | None = Field(default=None, ge=1)
    whatsapp_number: str | None = None
    contact_email: EmailStr | None = None


class BusinessResponse(BaseModel):
    id: uuid.UUID
    owner_user_id: uuid.UUID
    name: str
    business_type: str | None
    industry: str | None
    country: str | None
    currency: str
    financial_year_start_month: int
    gst_registered: bool
    business_size: str | None
    number_of_branches: int
    whatsapp_number: str | None
    contact_email: str | None
    onboarding_completed: bool
    status: BusinessStatus
    plan: BusinessPlan
    created_at: datetime

    @classmethod
    def from_domain(cls, business: Business) -> "BusinessResponse":
        return cls(
            id=business.id,
            owner_user_id=business.owner_user_id,
            name=business.name,
            business_type=business.business_type,
            industry=business.industry,
            country=business.country,
            currency=business.currency,
            financial_year_start_month=business.financial_year_start_month,
            gst_registered=business.gst_registered,
            business_size=business.business_size,
            number_of_branches=business.number_of_branches,
            whatsapp_number=business.whatsapp_number,
            contact_email=business.contact_email,
            onboarding_completed=business.onboarding_completed,
            status=business.status,
            plan=business.plan,
            created_at=business.created_at,
        )


class MyBusinessResponse(BaseModel):
    business: BusinessResponse
    role: BusinessRole

    @classmethod
    def from_domain(cls, view: MyBusinessView) -> "MyBusinessResponse":
        return cls(business=BusinessResponse.from_domain(view.business), role=view.role)


class ChangePlanRequest(BaseModel):
    plan: BusinessPlan


class StartCheckoutSessionRequest(BaseModel):
    plan: BusinessPlan


class CheckoutSessionResponse(BaseModel):
    checkout_url: str


class BillingPortalSessionResponse(BaseModel):
    portal_url: str


class InviteTeamMemberRequest(BaseModel):
    email: EmailStr
    role: BusinessRole


class UpdateTeamMemberRoleRequest(BaseModel):
    role: BusinessRole


class TeamMemberResponse(BaseModel):
    membership_id: uuid.UUID
    user_id: uuid.UUID
    email: str
    display_name: str
    role: BusinessRole
    status: MembershipStatus

    @classmethod
    def from_domain(cls, view: TeamMemberView) -> "TeamMemberResponse":
        return cls(
            membership_id=view.membership_id,
            user_id=view.user_id,
            email=view.email,
            display_name=view.display_name,
            role=view.role,
            status=view.status,
        )
