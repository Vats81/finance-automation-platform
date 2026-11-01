from dataclasses import dataclass

from app.business.domain.value_objects import BusinessKind, BusinessPlan


@dataclass(frozen=True)
class PlanLimits:
    max_team_members: int


# Hardcoded, not DB-configurable — no admin UI to edit these exists yet
# (that's Admin Panel territory later), and there's no consumer for that
# flexibility today. The frontend keeps its own small mirrored constant
# for the "X of Y used" display, per this codebase's established
# per-layer-duplication convention.
PLAN_LIMITS: dict[BusinessPlan, PlanLimits] = {
    # Raised for the private beta so a small team can all try it; tighten before charging.
    BusinessPlan.FREE: PlanLimits(max_team_members=10),
    BusinessPlan.STARTER: PlanLimits(max_team_members=10),
    BusinessPlan.PRO: PlanLimits(max_team_members=20),
}

# A personal account is shared with a partner or family, so its limits are small: Free, one other person;
# Plus, four. (A personal workspace only ever uses the FREE and STARTER tiers.)
PERSONAL_PLAN_LIMITS: dict[BusinessPlan, PlanLimits] = {
    BusinessPlan.FREE: PlanLimits(max_team_members=2),
    BusinessPlan.STARTER: PlanLimits(max_team_members=5),
    BusinessPlan.PRO: PlanLimits(max_team_members=5),
}


def max_team_members(plan: BusinessPlan, kind: BusinessKind) -> int:
    limits = PERSONAL_PLAN_LIMITS if kind == BusinessKind.PERSONAL else PLAN_LIMITS
    return limits[plan].max_team_members
