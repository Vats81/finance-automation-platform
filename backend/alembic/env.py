from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

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
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
