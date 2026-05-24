import asyncio
from logging.config import fileConfig
import sys

from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from app.core.database import Base
from app.core.settings import db_settings
import app.models

settings = db_settings()

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

_ALLOWED_SCHEMAS = {"app", "db_meta"}


def _get_object_schema(obj) -> str | None:
    schema = getattr(obj, "schema", None)
    if schema:
        return schema
    table = getattr(obj, "table", None)
    if table is not None:
        return getattr(table, "schema", None)
    return None


def _fk_columns_equal(fk1, fk2) -> bool:
    """Compare two ForeignKeyConstraints structurally — ignore schema differences.

    When include_schemas=True, Alembic compares FK constraints with schema
    awareness.  Reflected FKs from PostgreSQL may not carry explicit schema
    attributes on the ForeignKeyConstraint object in the same way the model
    metadata does, causing every FK to appear "changed" (schema=None vs
    schema='app').  This helper returns True when two FK constraints differ
    *only* in schema, so we can safely exclude them from the autogenerate
    diff.
    """
    # Constrained columns must match.
    cols1 = sorted(c.name for c in fk1.columns)
    cols2 = sorted(c.name for c in fk2.columns)
    if cols1 != cols2:
        return False

    # Referred table *name* must match (ignore schema).
    try:
        ref_table1 = fk1.elements[0].column.table.name
        ref_table2 = fk2.elements[0].column.table.name
    except (IndexError, AttributeError):
        return False
    if ref_table1 != ref_table2:
        return False

    # Referred columns must match.
    try:
        ref_cols1 = sorted(e.column.name for e in fk1.elements)
        ref_cols2 = sorted(e.column.name for e in fk2.elements)
    except AttributeError:
        return False
    if ref_cols1 != ref_cols2:
        return False

    # ondelete / onupdate must match.
    if fk1.ondelete != fk2.ondelete:
        return False
    if fk1.onupdate != fk2.onupdate:
        return False

    return True


def _fk_signature(fk) -> "tuple | None":
    """Return a structural signature for a FK constraint — stable regardless
    of schema or PostgreSQL identifier truncation."""
    cols = tuple(sorted(c.name for c in fk.columns))
    try:
        ref_table = fk.elements[0].column.table.name
        ref_cols = tuple(sorted(e.column.name for e in fk.elements))
    except (IndexError, AttributeError):
        return None
    ondelete = fk.ondelete or ""
    onupdate = fk.onupdate or ""
    return (cols, ref_table, ref_cols, ondelete, onupdate)


# During autogenerate comparison, FK constraints whose names differ *only*
# because of PostgreSQL's 63-character identifier truncation cannot be paired
# by Alembic (pairing is name-based).  We accumulate unpaired FKs here so that
# when a structurally identical FK appears on the other side, both can be
# excluded.
_fk_pending: dict[bool, dict[tuple, list]] = {
    True: {},   # reflected-side unpaired FKs, keyed by signature
    False: {},  # model-side unpaired FKs, keyed by signature
}


def include_object(obj, name, type_, reflected, compare_to):
    # Never operate on Alembic's own version table — it's managed by Alembic itself.
    # Without this guard, autogenerate will see a stale alembic_version table left
    # behind in a previously-configured schema (e.g. "app") and emit op.drop_table().
    if type_ == "table" and name == context.config.get_main_option(
        "version_table", "alembic_version"
    ):
        return False

    # During autogenerate comparison, skip FK constraints that are structurally
    # identical (differing only in schema representation or truncated names).
    # This prevents spurious drop+recreate of every FK when include_schemas=True
    # sees a mismatch between reflected and model FKs.
    #
    # Two cases:
    # 1. Paired (compare_to is not None): Alembic matched them by name — check
    #    if structures are equal and skip the pair if so.
    # 2. Unpaired (compare_to is None): Alembic couldn't match by name (e.g.
    #    PostgreSQL truncated a 63+ char identifier).  Accumulate the FK in a
    #    pending registry; when the matching FK from the other side shows up,
    #    both are excluded.
    if type_ == "foreign_key_constraint":
        if compare_to is not None:
            if _fk_columns_equal(obj, compare_to):
                return False  # Exclude from diff — identical FK, just schema noise.
        else:
            sig = _fk_signature(obj)
            if sig is None:
                schema = _get_object_schema(obj)
                if schema is None:
                    return True
                return schema in _ALLOWED_SCHEMAS

            other_side = not reflected
            pending = _fk_pending[other_side]
            if sig in pending:
                # Found the matching FK from the other side — exclude both.
                pending[sig].pop()  # Remove one pending item
                if not pending[sig]:
                    del pending[sig]
                return False
            else:
                # First time seeing this signature — exclude it now.
                # When the matching FK from the other side shows up, it will
                # also be excluded, resulting in no diff for this pair.
                _fk_pending[reflected].setdefault(sig, []).append(name)
                return False

    schema = _get_object_schema(obj)
    if schema is None:
        return True
    return schema in _ALLOWED_SCHEMAS


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        version_table_schema="db_meta",
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        version_table_schema="db_meta",
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.execute(text("SET ROLE app_owner"))
        await connection.execute(text("SET search_path TO app, db_meta, extensions, public"))
        await connection.commit()
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
