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
    of schema or PostgreSQL identifier truncation.

    Used to cross-reference unpaired FKs whose names don't match (Alembic
    pairs by name).  Two FKs with the same signature are structurally
    identical; if their names are also truncation variants they can be
    safely excluded from the diff.
    """
    cols = tuple(sorted(c.name for c in fk.columns))
    try:
        ref_table = fk.elements[0].column.table.name
        ref_cols = tuple(sorted(e.column.name for e in fk.elements))
    except (IndexError, AttributeError):
        return None
    ondelete = fk.ondelete or ""
    onupdate = fk.onupdate or ""
    return (cols, ref_table, ref_cols, ondelete, onupdate)


def _fk_names_truncated(name1: str, name2: str) -> bool:
    """Check whether two FK names differ only because PostgreSQL truncated a
    63+ character identifier.

    PostgreSQL replaces the tail of overlong identifiers with a hash suffix,
    so the stored name is a substring of the model-generated name plus an
    opaque suffix.  This returns True when the shorter name is a prefix of
    the longer one and the length difference is small (< 15 chars), which is
    characteristic of truncation — not a genuine rename.
    """
    shorter = name1 if len(name1) <= len(name2) else name2
    longer = name2 if len(name1) <= len(name2) else name1
    diff = len(longer) - len(shorter)
    if diff <= 0 or diff > 15:
        return False
    return longer.startswith(shorter[: len(shorter) - 4])


# When Alembic cannot pair two FK constraints by name (e.g. PostgreSQL
# truncated a 63+ char identifier), compare_to is None for both sides.
# We accumulate structural signatures here so the other side can find its
# match.  Only signatures with names that are clearly truncation variants
# (checked via _fk_names_truncated) are paired — genuinely new/removed FKs
# always pass through.
#
# Safety: the registry is reset at the first FK sighting so stale entries
# from a prior partial run cannot leak into a fresh comparison.
_fk_pending: dict[bool, list[tuple[tuple, str]]] = {True: [], False: []}
_fk_pending_seen: bool = False


def include_object(obj, name, type_, reflected, compare_to):
    # Never operate on Alembic's own version table — it's managed by Alembic itself.
    # Without this guard, autogenerate will see a stale alembic_version table left
    # behind in a previously-configured schema (e.g. "app") and emit op.drop_table().
    if type_ == "table" and name == context.config.get_main_option(
        "version_table", "alembic_version"
    ):
        return False

    # During autogenerate comparison, skip FK constraints that are structurally
    # identical but whose schema representation (include_schemas=True) or
    # PostgreSQL-truncated name causes a spurious diff.
    #
    # Two cases:
    # 1. Paired by name (compare_to is not None): schema mismatch — check
    #    structural equality; skip the pair if identical.
    # 2. Unpaired (compare_to is None): name mismatch (truncation) — accumulate
    #    the FK's structural signature and its name.  When the matching side
    #    arrives AND the names are truncation variants, exclude both.
    #    Genuinely new/removed FKs (unique signature, or non-truncated names)
    #    always pass through.
    if type_ == "foreign_key_constraint":
        global _fk_pending_seen
        if not _fk_pending_seen:
            _fk_pending[True].clear()
            _fk_pending[False].clear()
            _fk_pending_seen = True

        if compare_to is not None:
            if _fk_columns_equal(obj, compare_to):
                return False  # Paired — structurally identical, skip.

        else:
            sig = _fk_signature(obj)
            if sig is None:
                pass  # Fall through to schema check.
            else:
                other_side = not reflected
                for i, (other_sig, other_name) in enumerate(
                    _fk_pending[other_side]
                ):
                    if other_sig == sig and _fk_names_truncated(
                        name, other_name
                    ):
                        del _fk_pending[other_side][i]
                        return False  # Matched truncation pair — exclude.

                # Store for the other side to match.
                _fk_pending[reflected].append((sig, name))
                return False  # Defer decision — exclude, wait for match.

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
