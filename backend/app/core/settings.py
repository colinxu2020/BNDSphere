from functools import cache
from typing import Self
from urllib.parse import quote

from pydantic import computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class _AppBaseSettings(BaseSettings):
    model_config = SettingsConfigDict(secrets_dir="/run/secrets")


class WebSettings(_AppBaseSettings):
    debug: bool
    cors_origin: str
    secret_key: str
    # Per-IP auth request budgets (``app.core.rate_limit``). Opt-in and off by
    # default: a whole campus can share one NAT egress IP, so an IP-level block
    # takes out many legitimate users at once. Set
    # ``AUTH_IP_RATE_LIMIT_ENABLED=true`` to enforce them. The per-account
    # failure lockout and the process-wide circuit breaker are always on.
    auth_ip_rate_limit_enabled: bool = False

    @model_validator(mode="after")
    def _reject_wildcard_cors_outside_debug(self) -> Self:
        """Refuse to boot with ``CORS_ORIGIN=*`` once auth rides on a cookie.

        Starlette echoes the caller's origin instead of ``*`` when
        ``allow_credentials`` is on (which it is, in ``app.main``), so a
        wildcard does not merely relax reads — it authorizes *credentialed*
        cross-origin requests from any site on the internet, each one carrying
        the visitor's session cookie. That was harmless when the credential was
        a bearer token another origin could not obtain; it is a session-riding
        hole now that the browser attaches the cookie by itself.

        Allowed under ``DEBUG=true`` so local development keeps working.
        """
        if not self.debug and self.cors_origin.strip() == "*":
            raise ValueError(
                "CORS_ORIGIN='*' is refused when DEBUG is false: it would let "
                "any origin make credentialed requests with the visitor's "
                "session cookie. Set CORS_ORIGIN to the site's own origin "
                "(e.g. https://bnd.fun).",
            )
        return self


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


@cache
def db_settings() -> DatabaseSettings:
    return DatabaseSettings()  # type: ignore[call-arg]


@cache
def web_settings() -> WebSettings:
    return WebSettings()  # type: ignore[call-arg]


@cache
def oss_settings() -> OSSSettings:
    return OSSSettings()  # type: ignore[call-arg]
