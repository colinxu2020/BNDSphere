"""Version stamping — the backend must report its baked-in APP_VERSION.

Spec §6.2, §7: APP_VERSION is ground truth for what is running. It is baked
in at image build time and must never be inferred from anything mutable.
"""

import pytest

from app.core.settings import DeploymentSettings, deployment_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    """deployment_settings() is @cache'd; clear before and after each test."""
    deployment_settings.cache_clear()
    yield
    deployment_settings.cache_clear()


def test_app_version_defaults_to_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_VERSION", raising=False)
    assert deployment_settings().app_version == "dev"


def test_app_version_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_VERSION", "v1.5.0")
    assert deployment_settings().app_version == "v1.5.0"


def test_app_version_is_a_plain_string_not_parsed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Guard against anyone "helpfully" coercing this to a semver type later.
    # The updater compares tags as strings; a parsed type would silently drop
    # pre-release suffixes.
    monkeypatch.setenv("APP_VERSION", "v1.5.0-rc.1+build.7")
    assert deployment_settings().app_version == "v1.5.0-rc.1+build.7"


def test_settings_class_is_directly_constructible() -> None:
    assert DeploymentSettings(app_version="v2.0.0").app_version == "v2.0.0"
