import enum


class BusinessRole(str, enum.Enum):
    """Per-business RBAC for the SMB Finance Manager product — distinct
    from identity.domain.value_objects.Role (the AP-automation product's
    global AP_CLERK/APPROVER/FINANCE_ADMIN roles). A single platform user
    can hold a different BusinessRole in each business they belong to
    (see BusinessMembership), which is why this lives on the membership
    row rather than on User itself.
    """

    OWNER = "owner"
    ADMIN = "admin"
    ACCOUNTANT = "accountant"
    VIEWER = "viewer"


class BusinessKind(str, enum.Enum):
    """What the workspace is for. A business is the full product (customers,
    sales, stock...); a personal workspace is the simple income / spending /
    budget view for one person's own money.
    """

    BUSINESS = "business"
    PERSONAL = "personal"


class BusinessStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class MembershipStatus(str, enum.Enum):
    ACTIVE = "active"
    INVITED = "invited"
    REMOVED = "removed"


class BusinessPlan(str, enum.Enum):
    """Modeled now (per-plan team-member limits enforced by
    InviteTeamMemberUseCase) with billing deliberately deferred — no
    payment gateway is wired up, so "upgrading" is just a direct field
    change via ChangeBusinessPlanUseCase, not a real charge.
    """

    FREE = "free"
    STARTER = "starter"
    PRO = "pro"


# Amounts are stored as plain numbers and never converted, so a business's currency is
# a display choice. Dollars and rupees are the two the product presents today.
SUPPORTED_CURRENCIES = ("USD", "INR")
