import logging
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.exc import OperationalError

from app.config.settings import get_settings
from app.shared.infrastructure.db.base import Base

# Import every context's ORM models here so Base.metadata is fully
# populated before autogenerate runs. Uncommented incrementally as each
# bounded context's infrastructure/models.py is created.
from app.shared.infrastructure.outbox import outbox_model  # noqa: F401
from app.identity.infrastructure import models as identity_models  # noqa: F401
from app.vendors.infrastructure import models as vendors_models  # noqa: F401
from app.purchase_orders.infrastructure import models as purchase_orders_models  # noqa: F401
from app.invoices.infrastructure import models as invoices_models  # noqa: F401
from app.approvals.infrastructure import models as approvals_models  # noqa: F401
from app.payments.infrastructure import models as payments_models  # noqa: F401
from app.audit.infrastructure import models as audit_models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")

target_metadata = Base.metadata

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url_sync)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        # psycopg2 has no default connect timeout at all — without this, a
        # migration run against an unreachable database (wrong host,
        # expired free-tier instance, ...) hangs on the OS's own TCP
        # timeout, which can be minutes or effectively forever depending
        # on the network. Failing fast here means the container's boot
        # failure shows up clearly in logs instead of as a silent hang.
        connect_args={
            "connect_timeout": 10,
            # See Settings.effective_database_ssl (explicit DATABASE_SSL, or
            # automatic "require" for Render-managed Postgres hosts).
            **(
                {"sslmode": settings.effective_database_ssl}
                if settings.effective_database_ssl
                else {}
            ),
        },
    )

    try:
        connection = connectable.connect()
    except OperationalError as exc:
        # The database can't be reached at all (expired/suspended free-tier
        # instance, wrong host or credentials, ...). There is nothing to
        # migrate, and exiting non-zero here made the container's
        # `alembic upgrade head && uvicorn ...` chain stop before the web
        # server ever started — so the whole service went silent (Render's
        # edge just hung) and the cause was invisible from outside. Return
        # cleanly instead so the app boots, and /health reports
        # "postgres: error: ..." in seconds.
        #
        # Deliberately narrow: only a failed *connect* is skipped. A
        # migration that fails against a reachable database still raises and
        # aborts the deploy, which keeps Render's protection of leaving the
        # previous working version running.
        logger.warning(
            "Database unreachable, skipping migrations so the app can still start "
            "(check DATABASE_URL_SYNC / that the database is active): %s",
            exc,
        )
        return

    with connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
