from dataclasses import dataclass

from app.bootstrap.unit_of_work import AppUnitOfWork

# Same accepted-scale-limit convention used throughout this codebase for
# Python-side aggregation (see get_dashboard_summary.py, list_outstanding_
# sales.py, etc.) — fine at foundation-slice scale.
_MAX_TO_SCAN = 10_000


@dataclass(frozen=True)
class PlatformStats:
    total_businesses: int
    total_users: int
    businesses_by_plan: dict[str, int]
    verified_users: int
    unverified_users: int


class GetPlatformStatsUseCase:
    def __init__(self, uow: AppUnitOfWork) -> None:
        self._uow = uow

    async def execute(self) -> PlatformStats:
        businesses, total_businesses = await self._uow.businesses.list_all(offset=0, limit=_MAX_TO_SCAN)
        users, total_users = await self._uow.users.list_all(offset=0, limit=_MAX_TO_SCAN)

        businesses_by_plan: dict[str, int] = {}
        for business in businesses:
            businesses_by_plan[business.plan.value] = businesses_by_plan.get(business.plan.value, 0) + 1

        verified_users = sum(1 for u in users if u.is_email_verified)
        unverified_users = total_users - verified_users

        return PlatformStats(
            total_businesses=total_businesses,
            total_users=total_users,
            businesses_by_plan=businesses_by_plan,
            verified_users=verified_users,
            unverified_users=unverified_users,
        )
