from app.business.domain.entities import Business, BusinessMembership
from app.business.domain.value_objects import BusinessPlan, BusinessRole, BusinessStatus, MembershipStatus
from app.business.infrastructure.models import BusinessMembershipModel, BusinessModel


def business_model_to_domain(model: BusinessModel) -> Business:
    return Business(
        entity_id=model.id,
        owner_user_id=model.owner_user_id,
        name=model.name,
        business_type=model.business_type,
        industry=model.industry,
        country=model.country,
        currency=model.currency,
        financial_year_start_month=model.financial_year_start_month,
        gst_registered=model.gst_registered,
        business_size=model.business_size,
        number_of_branches=model.number_of_branches,
        whatsapp_number=model.whatsapp_number,
        contact_email=model.contact_email,
        onboarding_completed=model.onboarding_completed,
        status=BusinessStatus(model.status),
        plan=BusinessPlan(model.plan),
        created_at=model.created_at,
    )


def business_domain_to_model(business: Business) -> BusinessModel:
    return BusinessModel(
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
        status=business.status.value,
        plan=business.plan.value,
        created_at=business.created_at,
    )


def apply_business_domain_to_existing_model(business: Business, model: BusinessModel) -> None:
    model.name = business.name
    model.business_type = business.business_type
    model.industry = business.industry
    model.country = business.country
    model.currency = business.currency
    model.financial_year_start_month = business.financial_year_start_month
    model.gst_registered = business.gst_registered
    model.business_size = business.business_size
    model.number_of_branches = business.number_of_branches
    model.whatsapp_number = business.whatsapp_number
    model.contact_email = business.contact_email
    model.onboarding_completed = business.onboarding_completed
    model.status = business.status.value
    model.plan = business.plan.value


def membership_model_to_domain(model: BusinessMembershipModel) -> BusinessMembership:
    return BusinessMembership(
        entity_id=model.id,
        business_id=model.business_id,
        user_id=model.user_id,
        role=BusinessRole(model.role),
        status=MembershipStatus(model.status),
        invited_by_user_id=model.invited_by_user_id,
        created_at=model.created_at,
        joined_at=model.joined_at,
    )


def membership_domain_to_model(membership: BusinessMembership) -> BusinessMembershipModel:
    return BusinessMembershipModel(
        id=membership.id,
        business_id=membership.business_id,
        user_id=membership.user_id,
        role=membership.role.value,
        status=membership.status.value,
        invited_by_user_id=membership.invited_by_user_id,
        created_at=membership.created_at,
        joined_at=membership.joined_at,
    )


def apply_membership_domain_to_existing_model(
    membership: BusinessMembership, model: BusinessMembershipModel
) -> None:
    model.role = membership.role.value
    model.status = membership.status.value
    model.joined_at = membership.joined_at
