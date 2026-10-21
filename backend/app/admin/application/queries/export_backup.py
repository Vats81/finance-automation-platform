from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.infrastructure.backup_tool import dump_database


class ExportBackupUseCase:
    """A logical (not byte-for-byte SQL) backup of every table in the schema,
    serialised to a checksummed JSON document (format and exclusions are
    documented in shared/infrastructure/backup_format.py; how to restore it is
    in docs/RECOVERY_RUNBOOK.md). Deliberately Python-only: no `pg_dump`
    binary is installed in the deployed image.

    Platform-admin only (see api/routes.py's router-level
    require_platform_admin). Business Admins cannot call it, and it holds
    every tenant's data plus password hashes, so it must only ever leave the
    app encrypted.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def execute(self) -> dict[str, Any]:
        return await self._session.run_sync(lambda sync_session: dump_database(sync_session.connection()))
