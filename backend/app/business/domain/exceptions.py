from app.shared.domain.exceptions import (
    ConflictException,
    NotFoundException,
    UnauthorizedDomainActionException,
    ValidationException,
)


class BusinessNotFoundException(NotFoundException):
    error_code = "business_not_found"


class NotABusinessMemberException(UnauthorizedDomainActionException):
    """Raised when the acting user has no membership row for the target
    business at all — distinct from having a membership with the wrong
    role (see require_business_role's generic role-mismatch message).
    """

    error_code = "not_a_business_member"


class InvalidOnboardingDataException(ValidationException):
    error_code = "invalid_onboarding_data"


class MembershipNotFoundException(NotFoundException):
    error_code = "membership_not_found"


class TeamMemberLimitExceededException(ConflictException):
    error_code = "team_member_limit_exceeded"


class InviteeNotRegisteredException(ValidationException):
    error_code = "invitee_not_registered"


class UserAlreadyMemberException(ConflictException):
    error_code = "user_already_member"


class CannotModifyOwnerMembershipException(ValidationException):
    """The founding owner's membership can never be removed or role-changed
    through the team-members flow — a safety rail against locking out the
    one account that always has full authority over the business.
    """

    error_code = "cannot_modify_owner_membership"


class DirectPlanChangeNotAllowedException(ValidationException):
    """Once Stripe is configured, paid plans can only be reached through a
    real checkout — the direct-flip endpoint may still set FREE, but never
    STARTER/PRO. See ChangeBusinessPlanUseCase.
    """

    error_code = "direct_plan_change_not_allowed"


class ActiveSubscriptionExistsException(ConflictException):
    """Refuses a direct flip back to FREE while a live Stripe subscription
    still exists — the business would keep being charged while the app
    silently thinks it's on the free plan. Cancel via the billing portal
    instead, which syncs back through the webhook.
    """

    error_code = "active_subscription_exists"


class NoStripeCustomerException(NotFoundException):
    """Raised when a business tries to open the billing portal before ever
    completing a checkout — there's no Stripe customer to manage yet.
    """

    error_code = "no_stripe_customer"
