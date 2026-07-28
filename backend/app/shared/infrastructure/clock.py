from datetime import datetime, timezone

from app.shared.application.ports import IClock


class SystemClock(IClock):
    def now(self) -> datetime:
        return datetime.now(timezone.utc)
