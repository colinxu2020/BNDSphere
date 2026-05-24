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

    # ondelete / onupdate / deferrable / initially must match.
    if fk1.ondelete != fk2.ondelete:
        return False
    if fk1.onupdate != fk2.onupdate:
        return False
    if getattr(fk1, "deferrable", None) != getattr(fk2, "deferrable", None):
        return False
    if getattr(fk1, "initially", None) != getattr(fk2, "initially", None):
        return False

    return True


def include_object(obj, name, type_, reflected, compare_to):
    # Never operate on Alembic's own version table — it's managed by Alembic itself.
    # Without this guard, autogenerate will see a stale alembic_version table left
    # behind in a previously-configured schema (e.g. "app") and emit op.drop_table().
    if type_ == "table" and name == context.config.get_main_option(
        "version_table", "alembic_version"
    ):
        return False

    # During autogenerate comparison, skip FK constraints that are structurally
    # identical but whose schema representation differs (include_schemas=True
    # vs reflected FK not carrying explicit schema).  Only paired FKs are
    # checked — unpaired FKs pass through to the normal schema filter.
    #
    # Name-truncation noise (PostgreSQL 63-char limit) is handled separately
    # in process_revision_directives() below, which has access to the full
    # operation list.
    if type_ == "foreign_key_constraint" and compare_to is not None:
        if _fk_columns_equal(obj, compare_to):
            return False  # Structurally identical — exclude from diff.

    schema = _get_object_schema(obj)
    if schema is None:
        return True
    return schema in _ALLOWED_SCHEMAS


def _names_truncated_pair(name_a: str, name_b: str) -> bool:
    """Check whether two FK names differ only due to PostgreSQL 63-char
    identifier truncation.

    PostgreSQL truncates overlong identifiers by keeping a prefix and
    appending an underscore + hash suffix.  The shorter name, minus its
    trailing suffix, should be a prefix of the longer name.  Length gap
    must be small (< 15 chars) to avoid false positives on genuine renames.
    """
    shorter = name_a if len(name_a) <= len(name_b) else name_b
    longer = name_b if len(name_a) <= len(name_b) else name_a
    diff = len(longer) - len(shorter)
    if diff <= 0 or diff > 15:
        return False
    # Peel off the hash suffix — try 4 or 5 chars.
    for suffix_len in (5, 4):
        if len(shorter) <= suffix_len:
            continue
        base = shorter[:-suffix_len]
        if longer.startswith(base):
            return True
    return False


def process_revision_directives(context, revision, directives):
    """Post-process autogenerated migration operations.

    Removes FK drop+create pairs whose only difference is a PostgreSQL-
    truncated constraint name (63-char identifier limit).  The autogenerate
    comparison sees the truncated DB name and the full model name as
    different FKs → emits a spurious drop+recreate.  By the time this hook
    fires the full operation list is available, so we can safely identify
    and remove those pairs without risking suppression of genuinely new or
    removed FKs.
    """
    for directive in directives:
        for ops in (getattr(directive, "upgrade_ops", None),
                     getattr(directive, "downgrade_ops", None)):
            if ops is None:
                continue
            _strip_truncated_fk_pairs(ops)


def _strip_truncated_fk_pairs(ops):
    """Remove spurious drop+create FK pairs from an operation list.

    Walks the nested operation tree (ModifyTableOps → ops) and removes
    adjacent (drop_constraint, create_foreign_key) pairs where the only
    difference is a PostgreSQL-truncated name.

    Safety: only removes pairs that share the same source columns (when the
    drop side carries that information).  Full structural comparison is not
    possible because DropConstraintOp does not carry the referred table or
    FK options for the DB-side constraint.  In practice this is safe: two
    different FKs on the same table cannot share the same column set AND
    have truncation-variant names — the naming convention includes column
    names, so different columns produce different base names.
    """
    from alembic.operations.ops import (
        CreateForeignKeyOp,
        DropConstraintOp,
        ModifyTableOps,
    )

    for container in ops.ops:
        if not isinstance(container, ModifyTableOps):
            continue
        table_ops = container.ops
        i = 0
        while i < len(table_ops) - 1:
            drop_op = table_ops[i]
            create_op = table_ops[i + 1]
            if not (isinstance(drop_op, DropConstraintOp)
                    and isinstance(create_op, CreateForeignKeyOp)):
                i += 1
                continue
            if (drop_op.table_name != create_op.source_table
                    or not drop_op.constraint_name
                    or not create_op.constraint_name):
                i += 1
                continue
            drop_name: str = drop_op.constraint_name  # type: ignore[assignment]
            create_name: str = create_op.constraint_name  # type: ignore[assignment]
            # Same table + truncation-variant names?
            if not _names_truncated_pair(drop_name, create_name):
                i += 1
                continue
            # Verify same columns when the drop side carries them.
            drop_cols = getattr(drop_op, "columns", None)
            if drop_cols is not None:
                create_cols = list(create_op.source_columns)
                if sorted(drop_cols) != sorted(create_cols):
                    i += 1
                    continue
            # Sufficient evidence this is a spurious rename — remove both.
            del table_ops[i:i + 2]
            # Don't advance i — the next pair slides into position.


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
        process_revision_directives=process_revision_directives,
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
        process_revision_directives=process_revision_directives,
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
