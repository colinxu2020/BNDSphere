from functools import cache
from pathlib import Path
from urllib.parse import quote

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class _AppBaseSettings(BaseSettings):
    model_config = SettingsConfigDict(secrets_dir="/run/secrets")


class WebSettings(_AppBaseSettings):
    debug: bool
    cors_origin: str
    secret_key: str


class DatabaseSettings(_AppBaseSettings):
    postgres_user: str = "postgres"
    postgres_password: str
    postgres_db: str = "postgres"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        # ``quote`` (not ``quote_plus``) encodes a space as ``%20`` instead of
        # ``+``; ``+`` is not decoded back to a space in the userinfo component
        # of a URI, which would corrupt passwords containing spaces.
        safe_password = quote(self.postgres_password, safe="")

        return f"postgresql+psycopg://{self.postgres_user}:{safe_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    model_config = SettingsConfigDict(secrets_dir="/run/secrets")


class OSSSettings(_AppBaseSettings):
    oss_endpoint_url: str
    oss_access_key_id: str
    oss_access_key: str
    oss_bucket: str
    # Public (e.g. CDN-fronted) base URL objects are served from; distinct from
    # oss_endpoint_url, which is only used for signing upload requests.
    oss_public_base_url: str


class DeploymentSettings(_AppBaseSettings):
    # Baked in at image build time via the APP_VERSION build arg. This is
    # ground truth for "what version is running" — never inferred from a file
    # on disk, which an updater crash could leave stale (spec §7).
    app_version: str = "dev"
    github_repo: str = "colinxu2020/BNDSphere"
    # Optional, and read-only: it only raises the rate limit on the public
    # release lookup. The panel cannot start a deploy, so no write scope is
    # needed or wanted here.
    github_token: str | None = None
    # Only used to build the link to the workflow on GitHub.
    deploy_workflow: str = "deploy.yml"
    # Bind-mounted read-only: written on the host by the deploy workflow, so
    # the backend can report deploy state but never forge it.
    status_dir: Path = Path("/srv/status")


@cache
def db_settings() -> DatabaseSettings:
    return DatabaseSettings()  # type: ignore[call-arg]


@cache
def web_settings() -> WebSettings:
    return WebSettings()  # type: ignore[call-arg]


@cache
def oss_settings() -> OSSSettings:
    return OSSSettings()  # type: ignore[call-arg]


@cache
def deployment_settings() -> DeploymentSettings:
    return DeploymentSettings()
