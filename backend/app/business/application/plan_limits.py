from dataclasses import dataclass

from app.business.domain.value_objects import BusinessPlan


@dataclass(frozen=True)
class PlanLimits:
    max_team_members: int


# Hardcoded, not DB-configurable — no admin UI to edit these exists yet
# (that's Admin Panel territory later), and there's no consumer for that
# flexibility today. The frontend keeps its own small mirrored constant
# for the "X of Y used" display, per this codebase's established
# per-layer-duplication convention.
PLAN_LIMITS: dict[BusinessPlan, PlanLimits] = {
    BusinessPlan.FREE: PlanLimits(max_team_members=2),
    BusinessPlan.STARTER: PlanLimits(max_team_members=5),
    BusinessPlan.PRO: PlanLimits(max_team_members=20),
}
