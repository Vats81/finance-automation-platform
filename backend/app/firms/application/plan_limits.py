from dataclasses import dataclass

from app.firms.domain.value_objects import FirmPlan


@dataclass(frozen=True)
class FirmPlanLimits:
    max_clients: int
    max_staff: int


# What a firm's plan allows. Hitting a limit only stops the firm adding more: clients and staff
# it already has stay reachable, so downgrading or a lapsed subscription never locks anyone out
# of their books. The frontend mirrors these numbers for display (types/firm.ts).
FIRM_PLAN_LIMITS: dict[FirmPlan, FirmPlanLimits] = {
    # Staff limits are raised for the private beta so a whole team can try it; tighten before charging.
    FirmPlan.FREE: FirmPlanLimits(max_clients=2, max_staff=10),
    FirmPlan.GROWTH: FirmPlanLimits(max_clients=15, max_staff=10),
    FirmPlan.PRACTICE: FirmPlanLimits(max_clients=50, max_staff=15),
}
