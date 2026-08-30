import uuid
from datetime import datetime, timezone

from app.business.domain.events import (
    BusinessOnboardingCompleted,
    BusinessPlanChanged,
    BusinessRegistered,
    BusinessSuspended,
    MembershipCreated,
    MembershipRemoved,
    MembershipRoleChanged,
)
from app.business.domain.value_objects import BusinessPlan, BusinessRole, BusinessStatus, MembershipStatus
from app.shared.domain.aggregate_root import AggregateRoot


class Business(AggregateRoot):
    """A business/company registered on the SMB Finance Manager product.
    Own aggregate; referenced by every other module (Sales, Expenses,
    Inventory, ...) only by id, mirroring how Invoice/PurchaseOrder
    reference Vendor by id only in the AP-automation contexts.

    `number_of_branches` is a plain int for now rather than a full `Branch`
    child entity — no consumer needs branch-scoped filtering until the
    Sales/Expenses/Inventory modules exist (Phase 2), so building that
    lifecycle now would have nothing to serve.
    """

    def __init__(
        self,
        *,
        entity_id: uuid.UUID | None = None,
        owner_user_id: uuid.UUID,
        name: str,
        business_type: str | None = None,
        industry: str | None = None,
        country: str | None = None,
        currency: str = "USD",
        financial_year_start_month: int = 1,
        gst_registered: bool = False,
        business_size: str | None = None,
        number_of_branches: int = 1,
        whatsapp_number: str | None = None,
        contact_email: str | None = None,
        onboarding_completed: bool = False,
        status: BusinessStatus = BusinessStatus.ACTIVE,
        plan: BusinessPlan = BusinessPlan.FREE,
        stripe_customer_id: str | None = None,
        stripe_subscription_id: str | None = None,
        created_at: datetime | None = None,
    ) -> None:
        super().__init__(entity_id)
        self.owner_user_id = owner_user_id
        self.name = name
        self.business_type = business_type
        self.industry = industry
        self.country = country
        self.currency = currency
        self.financial_year_start_month = financial_year_start_month
        self.gst_registered = gst_registered
        self.business_size = business_size
        self.number_of_branches = number_of_branches
        self.whatsapp_number = whatsapp_number
        self.contact_email = contact_email
        self.onboarding_completed = onboarding_completed
        self.status = status
        self.plan = plan
        self.stripe_customer_id = stripe_customer_id
        self.stripe_subscription_id = stripe_subscription_id
        self.created_at = created_at or datetime.now(timezone.utc)

    @classmethod
    def register(cls, *, owner_user_id: uuid.UUID, name: str) -> "Business":
        """Step 1 of the golden path (create account -> register business ->
        complete onboarding): only the business name is required up front,
        every other field is filled in (or skipped) during onboarding.
        """
        business = cls(owner_user_id=owner_user_id, name=name)
        business._record_event(
            BusinessRegistered(aggregate_id=business.id, name=name, owner_user_id=str(owner_user_id))
        )
        return business

    def complete_onboarding(
        self,
        *,
        business_type: str | None = None,
        industry: str | None = None,
        country: str | None = None,
        currency: str | None = None,
        financial_year_start_month: int | None = None,
        gst_registered: bool | None = None,
        business_size: str | None = None,
        number_of_branches: int | None = None,
        whatsapp_number: str | None = None,
        contact_email: str | None = None,
    ) -> None:
        """Every field is optional and skippable per the spec ('Allow users
        to skip optional fields and complete them later') — only fields
        actually provided are updated, and onboarding_completed is set
        regardless so the user isn't stuck re-prompted forever.
        """
        if business_type is not None:
            self.business_type = business_type
        if industry is not None:
            self.industry = industry
        if country is not None:
            self.country = country
        if currency is not None:
            self.currency = currency
        if financial_year_start_month is not None:
            self.financial_year_start_month = financial_year_start_month
        if gst_registered is not None:
            self.gst_registered = gst_registered
        if business_size is not None:
            self.business_size = business_size
        if number_of_branches is not None:
            self.number_of_branches = number_of_branches
        if whatsapp_number is not None:
            self.whatsapp_number = whatsapp_number
        if contact_email is not None:
            self.contact_email = contact_email

        self.onboarding_completed = True
        self._record_event(BusinessOnboardingCompleted(aggregate_id=self.id))

    def change_plan(self, *, plan: BusinessPlan) -> None:
        if plan == self.plan:
            return
        old_plan = self.plan
        self.plan = plan
        self._record_event(
            BusinessPlanChanged(aggregate_id=self.id, old_plan=old_plan.value, new_plan=plan.value)
        )

    def attach_stripe_customer(self, *, customer_id: str) -> None:
        """Purely a bookkeeping/reference update — no event, same
        non-event precedent as reactivate() below.
        """
        self.stripe_customer_id = customer_id

    def activate_subscription(self, *, subscription_id: str, plan: BusinessPlan) -> None:
        self.stripe_subscription_id = subscription_id
        self.change_plan(plan=plan)

    def cancel_subscription(self) -> None:
        self.stripe_subscription_id = None
        self.change_plan(plan=BusinessPlan.FREE)

    def suspend(self) -> None:
        """Same simple-toggle precedent as Product.deactivate()/reactivate()
        — records an event on the "negative" transition, none on the way
        back, no guard against a redundant call.
        """
        self.status = BusinessStatus.SUSPENDED
        self._record_event(BusinessSuspended(aggregate_id=self.id))

    def reactivate(self) -> None:
        self.status = BusinessStatus.ACTIVE


class BusinessMembership(AggregateRoot):
    """A user's membership in a business, with its own lifecycle (own table)
    independent of the Business row itself — same reasoning as ApprovalStep
    being a child entity separate from its parent workflow: a membership can
    be invited, activated, have its role changed, or be removed on its own
    timeline. Phase 1 only creates the OWNER membership at business
    registration time; inviting teammates by email is Settings/'Team
    members' work, deferred to Phase 2.
    """

    def __init__(
        self,
        *,
        entity_id: uuid.UUID | None = None,
        business_id: uuid.UUID,
        user_id: uuid.UUID,
        role: BusinessRole,
        status: MembershipStatus = MembershipStatus.ACTIVE,
        invited_by_user_id: uuid.UUID | None = None,
        created_at: datetime | None = None,
        joined_at: datetime | None = None,
    ) -> None:
        super().__init__(entity_id)
        self.business_id = business_id
        self.user_id = user_id
        self.role = role
        self.status = status
        self.invited_by_user_id = invited_by_user_id
        self.created_at = created_at or datetime.now(timezone.utc)
        self.joined_at = joined_at

    @classmethod
    def create_owner(cls, *, business_id: uuid.UUID, user_id: uuid.UUID) -> "BusinessMembership":
        now = datetime.now(timezone.utc)
        membership = cls(
            business_id=business_id,
            user_id=user_id,
            role=BusinessRole.OWNER,
            status=MembershipStatus.ACTIVE,
            joined_at=now,
        )
        membership._record_event(
            MembershipCreated(
                aggregate_id=membership.id,
                business_id=business_id,
                user_id=str(user_id),
                role=BusinessRole.OWNER.value,
            )
        )
        return membership

    @classmethod
    def invite(
        cls,
        *,
        business_id: uuid.UUID,
        user_id: uuid.UUID,
        role: BusinessRole,
        invited_by_user_id: uuid.UUID,
    ) -> "BusinessMembership":
        """Grants ACTIVE membership immediately — there is no separate
        accept-invite step in this slice (the invitee already has a real
        account, and the inviter already has business-role authority to
        grant access). MembershipStatus.INVITED stays modeled for a future
        slice that adds a real accept flow.
        """
        now = datetime.now(timezone.utc)
        membership = cls(
            business_id=business_id,
            user_id=user_id,
            role=role,
            status=MembershipStatus.ACTIVE,
            invited_by_user_id=invited_by_user_id,
            joined_at=now,
        )
        membership._record_event(
            MembershipCreated(
                aggregate_id=membership.id, business_id=business_id, user_id=str(user_id), role=role.value
            )
        )
        return membership

    def remove(self) -> None:
        if self.status == MembershipStatus.REMOVED:
            return
        self.status = MembershipStatus.REMOVED
        self._record_event(MembershipRemoved(aggregate_id=self.id))

    def change_role(self, *, role: BusinessRole) -> None:
        if role == self.role:
            return
        old_role = self.role
        self.role = role
        self._record_event(
            MembershipRoleChanged(aggregate_id=self.id, old_role=old_role.value, new_role=role.value)
        )

    @property
    def is_active(self) -> bool:
        return self.status == MembershipStatus.ACTIVE
