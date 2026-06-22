"""Pytest fixtures for BNDSphere backend tests.

Runs inside Docker — connects to the ``postgres`` service, reads secrets
from ``/run/secrets/`` (mounted by docker-compose).

Requires three secrets (env vars or files under ``/run/secrets/``):

    POSTGRES_PASSWORD     - superuser password (to create/drop test_db)
    APP_DB_PASSWORD       - ``app_user`` password
    MIGRATION_DB_PASSWORD - ``migration_user`` password
"""

import asyncio
import os
import secrets
import sys
from collections.abc import AsyncGenerator
from pathlib import Path

import psycopg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from psycopg import sql
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.dependencies import get_db
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models import User

# ── helpers ──────────────────────────────────────────────────────────


def _backend_dir() -> str:
    """Absolute path to the backend/ directory (where alembic.ini lives)."""
    return str(Path(__file__).resolve().parent.parent)


def _read_secret(env_name: str, filename: str) -> str:
    """Resolve a secret: env var first, then /run/secrets/<filename>."""
    value = os.environ.get(env_name)
    if value:
        return value

    secrets_dir = Path("/run/secrets")
    for path in (
        secrets_dir / filename,
        secrets_dir / f"{filename}.txt",
    ):
        if path.is_file():
            return path.read_text().strip()

    pytest.exit(
        f"Missing secret: env var {env_name!r} is not set and "
        f"neither /run/secrets/{filename} nor /run/secrets/{filename}.txt exist.\n"
        f"Set {env_name} or mount the secret file in the Docker container.",
    )


# ── connection parameters ────────────────────────────────────────────

TEST_DB_NAME = "test_db"

POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
SUPERUSER_PASSWORD = _read_secret("POSTGRES_PASSWORD", "postgres_password")
APP_PASSWORD = _read_secret("APP_DB_PASSWORD", "app_password")
MIGRATION_PASSWORD = _read_secret("MIGRATION_DB_PASSWORD", "migration_password")

SUPERUSER_ROOT_URL = (
    f"postgresql://postgres:{SUPERUSER_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/postgres"
)
SUPERUSER_TEST_DB_URL = (
    f"postgresql://postgres:{SUPERUSER_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{TEST_DB_NAME}"
)
APP_URL = (
    f"postgresql+psycopg://app_user:{APP_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{TEST_DB_NAME}"
)

# ── engine (app_user — matches production backend) ───────────────────

engine = create_async_engine(APP_URL)
TestSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


# ── session-scoped DB lifecycle ──────────────────────────────────────


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _initialize_test_database() -> AsyncGenerator[None]:
    """Create test database, set up per-DB grants, run alembic migrations."""
    # 1. Create test database as superuser
    conn = await psycopg.AsyncConnection.connect(SUPERUSER_ROOT_URL, autocommit=True)
    async with conn.cursor() as cur:
        await cur.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (TEST_DB_NAME,),
        )
        if await cur.fetchone() is None:
            await cur.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(TEST_DB_NAME)),
            )
    await conn.close()

    # 2. Per-database grants + schemas (roles already exist cluster-wide)
    admin_conn = await psycopg.AsyncConnection.connect(
        SUPERUSER_TEST_DB_URL,
        autocommit=True,
    )
    async with admin_conn.cursor() as cur:
        # Database-level grants
        await cur.execute(
            sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(
                sql.Identifier(TEST_DB_NAME),
            ),
        )
        for role in ("app_user", "migration_user"):
            await cur.execute(
                sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                    sql.Identifier(TEST_DB_NAME),
                    sql.Identifier(role),
                ),
            )
        await cur.execute(
            sql.SQL("GRANT CONNECT, CREATE ON DATABASE {} TO app_owner").format(
                sql.Identifier(TEST_DB_NAME),
            ),
        )

        # Schemas owned by app_owner
        for schema_name in ("db_meta", "app", "extensions"):
            await cur.execute(
                sql.SQL(
                    "CREATE SCHEMA IF NOT EXISTS {} AUTHORIZATION app_owner",
                ).format(sql.Identifier(schema_name)),
            )

        # Lock down public
        await cur.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
        for role in ("app_user", "migration_user"):
            await cur.execute(
                sql.SQL("REVOKE ALL ON SCHEMA public FROM {}").format(
                    sql.Identifier(role),
                ),
            )

        # Schema grants for app_user
        for schema_name in ("app", "extensions"):
            await cur.execute(
                sql.SQL("GRANT USAGE ON SCHEMA {} TO app_user").format(
                    sql.Identifier(schema_name),
                ),
            )

        # Default privileges (objects created by app_owner → app_user can use)
        for stmt in (
            sql.SQL("GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user"),
            sql.SQL("GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO app_user"),
            sql.SQL("GRANT EXECUTE ON FUNCTIONS TO app_user"),
        ):
            await cur.execute(
                sql.SQL(
                    "ALTER DEFAULT PRIVILEGES FOR ROLE app_owner IN SCHEMA app {}",
                ).format(stmt),
            )
        await cur.execute(
            sql.SQL(
                "ALTER DEFAULT PRIVILEGES FOR ROLE app_owner IN SCHEMA extensions "
                "GRANT EXECUTE ON FUNCTIONS TO app_user",
            ),
        )

        # Search paths
        await cur.execute(
            sql.SQL(
                "ALTER ROLE migration_user IN DATABASE {} "
                "SET search_path = app, db_meta, extensions, public",
            ).format(sql.Identifier(TEST_DB_NAME)),
        )
        await cur.execute(
            sql.SQL(
                "ALTER ROLE app_user IN DATABASE {} "
                "SET search_path = app, extensions, public",
            ).format(sql.Identifier(TEST_DB_NAME)),
        )
    await admin_conn.close()

    # 3. Run alembic migrations as migration_user
    env = os.environ.copy()
    env["POSTGRES_USER"] = "migration_user"
    env["POSTGRES_PASSWORD"] = MIGRATION_PASSWORD
    env["POSTGRES_DB"] = TEST_DB_NAME
    env["POSTGRES_HOST"] = POSTGRES_HOST
    env["POSTGRES_PORT"] = POSTGRES_PORT

    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "alembic",
        "upgrade",
        "head",
        cwd=_backend_dir(),
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        pytest.exit(f"alembic upgrade failed:\n{stderr.decode()}")

    yield

    # 4. Teardown — drop the test database
    await engine.dispose()

    conn = await psycopg.AsyncConnection.connect(SUPERUSER_ROOT_URL, autocommit=True)
    async with conn.cursor() as cur:
        await cur.execute(
            sql.SQL(
                "SELECT pg_terminate_backend(pg_stat_activity.pid) "
                "FROM pg_stat_activity "
                "WHERE pg_stat_activity.datname = {} AND pid <> pg_backend_pid()",
            ).format(sql.Literal(TEST_DB_NAME)),
        )
        await cur.execute(
            sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(TEST_DB_NAME)),
        )
    await conn.close()


# ── per-class fixtures (class-scoped transaction) ────────────────────


@pytest_asyncio.fixture(scope="class")
async def db_session() -> AsyncGenerator[AsyncSession]:
    """One session + transaction per test class, rolled back at class teardown.

    Tests within the same class share state — e.g. a setup test creates
    a user, and a subsequent test in the same class can assert on it.
    Classes are isolated from each other.
    """
    async with engine.connect() as conn:
        await conn.begin()
        async with TestSessionLocal(bind=conn) as session:
            yield session
        await conn.rollback()


@pytest_asyncio.fixture(scope="class")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    """Async HTTP client — one per test class (matches db_session scope)."""

    async def _override_get_db() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://127.0.0.1:8000/api/v1",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="class")
async def setup_class_users(
    request: object,
    db_session: AsyncSession,
) -> AsyncGenerator[None]:
    user_specs = getattr(request.cls, "USER_SPECS", None)
    if user_specs is None:
        yield
        return

    if type(user_specs) is not list[dict]:
        pytest.fail("USER_SPECS must be a list[dict]")

    class_users = {}

    for user_data in user_specs:
        username = user_data["username"]
        hashed_password = getattr(user_data, "hashed_password", None)
        if hashed_password is None:
            password = getattr(user_data, "password", None)
            if password is None:
                password = secrets.token_hex(8)
            hashed_password = get_password_hash(password)

        filtered_data = {k: v for k, v in user_data.items() if k != "password"}

        user = User(**filtered_data)
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        token = create_access_token({"sub": str(user.id)})
        headers = {"Authorization": f"Bearer {token}"}

        class_users[username] = {"headers": headers, "user": user}

    request.cls.configured_users = class_users
    yield
