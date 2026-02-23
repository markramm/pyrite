"""
Alembic environment configuration for pyrite.

Configures Alembic to use the ORM models from storage/models.py.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from pyrite.storage.models import Base

# Alembic Config object
config = context.config

# Set up logging from alembic.ini if available
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Virtual tables to exclude from autogenerate
VIRTUAL_TABLES = {"entry_fts", "vec_entry"}


def include_object(object, name, type_, reflected, compare_to):
    """Exclude virtual tables from autogenerate."""
    if type_ == "table" and name in VIRTUAL_TABLES:
        return False
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
