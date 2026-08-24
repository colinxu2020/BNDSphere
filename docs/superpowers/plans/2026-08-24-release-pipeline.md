# Release Pipeline & Version Stamping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish versioned `bndsphere-backend` and `bndsphere-caddy` images from a single build through two verifiable delivery paths — GHCR and a GitHub Release tarball — and make every running container report its own version.

**Architecture:** A tag-triggered workflow builds each image exactly once, pushes it to GHCR, then `docker save`s those same local image IDs into a release tarball. A `release-manifest.json` records the GHCR references plus registry and config digests for both, and `SHA256SUMS` covers the tarball and the manifest. Compose image references become environment-driven so a host can be pinned to a published version. `APP_VERSION` is baked in at build time so the backend never infers its version from anything mutable.

**Tech Stack:** GitHub Actions, Docker Buildx, GHCR, `gh` CLI, Docker Compose v2, FastAPI, pydantic-settings, pytest.

**Spec:** `docs/superpowers/specs/2026-08-24-deployment-updater-design.md`

## Global Constraints

- Plan 1 of 3. Plan 2 (updater sidecar) and Plan 3 (dev panel) consume this plan's outputs. Do not implement either here.
- Only `bndsphere-backend` and `bndsphere-caddy` are released. `bndsphere-postgres` is **never** built, pushed, or pinned by this pipeline (spec §3, §18.3).
- Images are built **exactly once** and published through both paths. Never build a second time for the tarball (spec §6.1).
- GHCR packages are **public** in v1. No registry credentials on the deploy host, no pull-secret code (spec §18.1).
- `deploy/versions.env` is host state and is **git-ignored**. Only `deploy/versions.env.example` is committed (spec §18.2).
- The running backend's baked-in `APP_VERSION` is ground truth for what is serving (spec §7). Default when unset: the literal string `dev`.
- Asset names are fixed and are hardcoded by the Plan 2 updater — do not rename: `bndsphere-images-amd64.tar.gz`, `release-manifest.json`, `SHA256SUMS`.
- GHCR image names are lowercase (registry requirement): `ghcr.io/<owner-lowercased>/bndsphere-backend`, `.../bndsphere-caddy`.
- amd64 only in v1; the asset name says so explicitly.
- Commit messages follow Conventional Commits — `.github/workflows/conventional-checks.yml` enforces this.
- Backend tests run inside Docker against the `postgres` service. Run them with:
  `docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile test run --rm test uv run pytest <args>`

---

### Task 1: Bake `APP_VERSION` into both images and expose it from the backend

The backend must be able to state its own version. Baking it in at build time is what makes it trustworthy: a container cannot be wrong about which image it is.

**Files:**
- Modify: `backend/Dockerfile`
- Modify: `infra/Dockerfile.Caddy`
- Modify: `backend/app/core/settings.py`
- Test: `backend/tests/test_deployment_settings.py` (create)

**Interfaces:**
- Consumes: nothing (first task).
- Produces:
  - `app.core.settings.DeploymentSettings` — pydantic settings class with field `app_version: str = "dev"`.
  - `app.core.settings.deployment_settings() -> DeploymentSettings` — `@cache`d accessor, same pattern as the existing `web_settings()` / `db_settings()` / `oss_settings()`.
  - Build arg `APP_VERSION` accepted by both Dockerfiles' `prod` targets, surfaced as env var `APP_VERSION`.
  - Plan 3 extends `DeploymentSettings` with `github_repo`, `github_token`, `request_dir`, `status_dir`. Do not add those fields here.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_deployment_settings.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile test \
  run --rm test uv run pytest tests/test_deployment_settings.py -v
```
Expected: FAIL — `ImportError: cannot import name 'DeploymentSettings' from 'app.core.settings'`

- [ ] **Step 3: Add the settings class**

In `backend/app/core/settings.py`, add after the existing `OSSSettings` class:

```python
class DeploymentSettings(_AppBaseSettings):
    # Baked in at image build time via the APP_VERSION build arg. This is
    # ground truth for "what version is running" — never inferred from a file
    # on disk, which an updater crash could leave stale (spec §7).
    app_version: str = "dev"
```

And add the cached accessor alongside the existing ones at the bottom:

```python
@cache
def deployment_settings() -> DeploymentSettings:
    return DeploymentSettings()
```

Note: unlike the other accessors this needs no `# type: ignore[call-arg]`, because every field has a default.

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile test \
  run --rm test uv run pytest tests/test_deployment_settings.py -v
```
Expected: PASS — 4 passed

- [ ] **Step 5: Add the build arg to the backend Dockerfile**

In `backend/Dockerfile`, the `prod` stage currently reads:

```dockerfile
FROM base AS prod
RUN uv sync --frozen --no-dev --no-cache
COPY --chown=appuser:appuser . .
ENV DEBUG=false
CMD ["/backend/.venv/bin/fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]
```

Replace it with:

```dockerfile
FROM base AS prod
ARG APP_VERSION=dev
RUN uv sync --frozen --no-dev --no-cache
COPY --chown=appuser:appuser . .
ENV DEBUG=false \
    APP_VERSION=${APP_VERSION}
CMD ["/backend/.venv/bin/fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]
```

`ARG` must be declared inside the stage that uses it — a top-level `ARG` is not visible in `prod`. Leave the `dev` stage alone; it correctly reports `dev`.

- [ ] **Step 6: Add the build arg to the Caddy Dockerfile**

In `infra/Dockerfile.Caddy`, the `prod` stage currently reads:

```dockerfile
FROM base AS prod

COPY --from=builder --chown=caddyuser:caddygroup /app/dist /srv
COPY --chown=caddyuser:caddygroup ./infra/Caddyfile /etc/caddy/Caddyfile
```

Replace it with:

```dockerfile
FROM base AS prod
ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}

COPY --from=builder --chown=caddyuser:caddygroup /app/dist /srv
COPY --chown=caddyuser:caddygroup ./infra/Caddyfile /etc/caddy/Caddyfile
```

- [ ] **Step 7: Verify the build arg reaches both images**

Run:
```bash
docker build --build-arg APP_VERSION=v9.9.9 -t bndsphere-verify-backend \
  --target prod -f backend/Dockerfile backend
docker run --rm --entrypoint sh bndsphere-verify-backend -c 'echo "$APP_VERSION"'
```
Expected: `v9.9.9`

```bash
docker build --build-arg APP_VERSION=v9.9.9 -t bndsphere-verify-caddy \
  --target prod -f infra/Dockerfile.Caddy .
docker run --rm --entrypoint sh bndsphere-verify-caddy -c 'echo "$APP_VERSION"'
```
Expected: `v9.9.9`

Then verify the default holds when the arg is omitted:
```bash
docker build -t bndsphere-verify-backend --target prod -f backend/Dockerfile backend
docker run --rm --entrypoint sh bndsphere-verify-backend -c 'echo "$APP_VERSION"'
```
Expected: `dev`

Clean up: `docker rmi bndsphere-verify-backend bndsphere-verify-caddy`

- [ ] **Step 8: Commit**

```bash
git add backend/Dockerfile infra/Dockerfile.Caddy backend/app/core/settings.py \
        backend/tests/test_deployment_settings.py
git commit -m "feat: bake APP_VERSION into backend and caddy images"
```

---

### Task 2: Make Compose image references environment-driven

A host must be able to run a published version without editing tracked files. This is also what lets the Plan 2 updater switch versions atomically.

**Files:**
- Modify: `docker-compose.yml` (services `alembic-migration`, `backend`, `caddy`, `alembic-autorevision`)
- Create: `deploy/versions.env.example`
- Create: `deploy/bootstrap.sh`
- Modify: `.gitignore`
- Test: verification commands in Steps 4 and 6 (Compose config resolution — no unit-test harness exists for Compose, and `docker compose config` is the real check CI already uses)

**Interfaces:**
- Consumes: Task 1's images.
- Produces:
  - Env var names `BACKEND_IMAGE` and `CADDY_IMAGE`, defaulting to `bndsphere-backend` / `bndsphere-caddy`. Plan 2's updater writes exactly these two names into `deploy/versions.env`.
  - Path `deploy/versions.env` (git-ignored, host state) and `deploy/versions.env.example` (committed template).
  - `deploy/bootstrap.sh` — resolves and persists `COMPOSE_PROJECT_DIR` into `.env`. Plan 2's `updater` service reads that variable; the updater itself never resolves it.

- [ ] **Step 1: Parameterise the four image references**

In `docker-compose.yml`, change the `image:` line of each of these four services. `postgres` is deliberately **not** changed — it is never released or pinned by this pipeline (spec §18.3).

`alembic-migration`:
```yaml
    image: ${BACKEND_IMAGE:-bndsphere-backend}
```

`backend`:
```yaml
    image: ${BACKEND_IMAGE:-bndsphere-backend}
```

`caddy`:
```yaml
    image: ${CADDY_IMAGE:-bndsphere-caddy}
```

`alembic-autorevision`:
```yaml
    image: ${BACKEND_IMAGE:-bndsphere-backend}
```

All four use the `:-` default form, so an unset variable keeps today's local-build behaviour exactly. `docker-compose.build.yml` keeps its literal `image:` names and needs no change — its `build:` sections still tag the local names, which the defaults then resolve to.

- [ ] **Step 2: Create the committed template**

Create `deploy/versions.env.example`:

```bash
# Deployment image pins for THIS host.
#
# On first deployment:  cp deploy/versions.env.example deploy/versions.env
#
# After that the updater owns deploy/versions.env and rewrites it atomically
# (spec §13.1). Do not hand-edit it while an update is in flight.
#
# This file is NOT the source of truth for what is running. The backend's
# baked-in APP_VERSION is (spec §7). These pins are what Compose will start
# NEXT; APP_VERSION is what is running NOW.
#
# Defaults below reproduce a local build. A deployed host will hold pinned
# digests written by the updater, e.g.
#   BACKEND_IMAGE=ghcr.io/colinxu2020/bndsphere-backend@sha256:abc...

BACKEND_IMAGE=bndsphere-backend
CADDY_IMAGE=bndsphere-caddy
```

- [ ] **Step 3: Git-ignore the real file**

Append to `.gitignore`:

```gitignore
# Host deployment state — owned by the updater, never committed (spec §18.2)
deploy/versions.env
```

- [ ] **Step 4: Write the bootstrap script**

`COMPOSE_PROJECT_DIR` must be the absolute host path of the deployment, because
Compose bind-mount sources (`./secrets/*`) are resolved by the host daemon
(spec §13). Making an operator discover and type that path by hand is a
reliable way to get a subtly wrong value — a relative path, a symlinked path,
or a trailing slash — which then fails at deploy time as a confusing secrets
error rather than as a configuration mistake.

So the value is **resolved once, mechanically, at setup**. Note what this script
does *not* do: it never searches the filesystem for a project, and the updater
never resolves or guesses this value either. The updater reads the configured
path and fails closed if it does not hold the expected Compose file (Plan 2
Task 1 `validate_startup`). Resolution happens exactly once, here, where the
script's own location is unambiguous evidence of where the deployment lives.

Create `deploy/bootstrap.sh`:

```sh
#!/bin/sh
# One-time deployment setup: resolve and persist this deployment's absolute
# path, and seed the version pins.
#
# Idempotent — safe to re-run. Run from anywhere:
#     ./deploy/bootstrap.sh
set -eu

# The script's own location IS the evidence of where the deployment lives, so
# no searching is needed or wanted. `pwd -P` resolves symlinks: the host Docker
# daemon resolves bind-mount sources against the physical filesystem, and a
# logical path containing a symlink would resolve differently there than here.
PROJECT_DIR=$(cd "$(dirname "$0")/.." && pwd -P)

# Fail closed rather than persisting a value that cannot work.
[ -f "$PROJECT_DIR/docker-compose.yml" ] || {
    printf 'ERROR: no docker-compose.yml in %s\n' "$PROJECT_DIR" >&2
    printf 'Run this script from inside the deployment checkout.\n' >&2
    exit 1
}
[ -d "$PROJECT_DIR/secrets" ] || {
    printf 'ERROR: no secrets/ in %s — create it before bootstrapping.\n' \
        "$PROJECT_DIR" >&2
    exit 1
}

ENV_FILE="$PROJECT_DIR/.env"
touch "$ENV_FILE"

# Upsert, never blind-append: re-running must not leave two conflicting
# COMPOSE_PROJECT_DIR lines, where Compose silently takes the last one.
if grep -q '^COMPOSE_PROJECT_DIR=' "$ENV_FILE"; then
    EXISTING=$(grep '^COMPOSE_PROJECT_DIR=' "$ENV_FILE" | tail -n 1 | cut -d= -f2-)
    if [ "$EXISTING" = "$PROJECT_DIR" ]; then
        printf 'COMPOSE_PROJECT_DIR already correct: %s\n' "$PROJECT_DIR"
    else
        printf 'Updating COMPOSE_PROJECT_DIR: %s -> %s\n' "$EXISTING" "$PROJECT_DIR"
        grep -v '^COMPOSE_PROJECT_DIR=' "$ENV_FILE" > "$ENV_FILE.tmp"
        printf 'COMPOSE_PROJECT_DIR=%s\n' "$PROJECT_DIR" >> "$ENV_FILE.tmp"
        mv -f "$ENV_FILE.tmp" "$ENV_FILE"
    fi
else
    printf 'COMPOSE_PROJECT_DIR=%s\n' "$PROJECT_DIR" >> "$ENV_FILE"
    printf 'Set COMPOSE_PROJECT_DIR=%s\n' "$PROJECT_DIR"
fi

# Seed the version pins. Never overwrite: after the first deployment this file
# is the updater's, and clobbering it would discard the rollback target.
if [ -f "$PROJECT_DIR/deploy/versions.env" ]; then
    printf 'deploy/versions.env already exists — left untouched.\n'
else
    cp "$PROJECT_DIR/deploy/versions.env.example" "$PROJECT_DIR/deploy/versions.env"
    printf 'Created deploy/versions.env from the template.\n'
fi

printf 'Bootstrap complete.\n'
```

Make it executable:

```bash
chmod +x deploy/bootstrap.sh
```

- [ ] **Step 5: Verify the bootstrap is correct and idempotent**

```bash
./deploy/bootstrap.sh
grep '^COMPOSE_PROJECT_DIR=' .env
```
Expected: the absolute physical path of this checkout, matching `pwd -P`.

```bash
test "$(grep '^COMPOSE_PROJECT_DIR=' .env | cut -d= -f2-)" = "$(pwd -P)" \
  && echo "path matches pwd -P"
```
Expected: `path matches pwd -P`

Re-running must not duplicate the line or clobber host state:
```bash
echo "BACKEND_IMAGE=ghcr.io/example/bndsphere-backend:v1.2.3" > deploy/versions.env
echo "CADDY_IMAGE=ghcr.io/example/bndsphere-caddy:v1.2.3" >> deploy/versions.env
./deploy/bootstrap.sh
test "$(grep -c '^COMPOSE_PROJECT_DIR=' .env)" -eq 1 && echo "exactly one entry"
grep BACKEND_IMAGE deploy/versions.env
```
Expected: `exactly one entry`, and `versions.env` still shows the pinned
`ghcr.io/example/...` value — re-running must never discard the rollback target.

A stale value must be corrected, not appended to:
```bash
sed -i.bak 's#^COMPOSE_PROJECT_DIR=.*#COMPOSE_PROJECT_DIR=/wrong/path#' .env && rm -f .env.bak
./deploy/bootstrap.sh
test "$(grep -c '^COMPOSE_PROJECT_DIR=' .env)" -eq 1 \
  && test "$(grep '^COMPOSE_PROJECT_DIR=' .env | cut -d= -f2-)" = "$(pwd -P)" \
  && echo "stale value corrected in place"
```
Expected: `stale value corrected in place`

And it must fail closed rather than persist an unusable path:
```bash
TMP=$(mktemp -d) && mkdir -p "$TMP/deploy" && cp deploy/bootstrap.sh "$TMP/deploy/"
"$TMP/deploy/bootstrap.sh" 2>&1 | head -2; echo "exit=$?"
```
Expected: `ERROR: no docker-compose.yml in ...` and a non-zero exit. Clean up with `rm -rf "$TMP"`.

- [ ] **Step 6: Verify Compose still resolves, both defaulted and pinned**

The stack's secret files must exist for `config` to parse. If you do not have real ones locally, create throwaways exactly as CI does in `.github/workflows/docker.yml`:

```bash
mkdir -p secrets
for f in postgres_password app_db_password migration_db_password \
         app_secret_key oss_access_key_id oss_access_key; do
  [ -f "secrets/$f.txt" ] || printf 'local-dummy\n' > "secrets/$f.txt"
done
```

Defaulted (no env file) — must still resolve to the local names:
```bash
docker compose -f docker-compose.yml -f docker-compose.build.yml config \
  | grep -E '^\s+image:'
```
Expected: `bndsphere-postgres`, `bndsphere-backend` (×3), `bndsphere-caddy`

Pinned — must pick up the override:
```bash
cp deploy/versions.env.example deploy/versions.env
sed -i.bak 's#^BACKEND_IMAGE=.*#BACKEND_IMAGE=ghcr.io/example/bndsphere-backend:v1.2.3#' \
  deploy/versions.env && rm -f deploy/versions.env.bak
docker compose --env-file deploy/versions.env -f docker-compose.yml config \
  | grep -E '^\s+image:'
```
Expected: backend and alembic services show `ghcr.io/example/bndsphere-backend:v1.2.3`; `postgres` still shows `bndsphere-postgres`, proving Postgres is untouched by pinning.

Confirm the ignore rule works:
```bash
git status --porcelain deploy/
```
Expected: only `deploy/versions.env.example` appears. `deploy/versions.env` must **not** be listed.

Finally, the check CI runs:
```bash
docker compose -f docker-compose.yml -f docker-compose.build.yml -f docker-compose.dev.yml config --quiet
```
Expected: no output, exit 0

- [ ] **Step 7: Commit**

```bash
git add docker-compose.yml deploy/versions.env.example deploy/bootstrap.sh .gitignore
git commit -m "feat: make compose image refs environment-driven for pinned deploys"
```

---

### Task 3: Release workflow — build once, publish through both paths

**Files:**
- Create: `.github/workflows/release.yml`
- Test: `bash -n` syntax check plus a real tagged dry run (Step 4 / Step 6)

**Interfaces:**
- Consumes: Task 1's `APP_VERSION` build arg; Task 2's `BACKEND_IMAGE` / `CADDY_IMAGE` names.
- Produces — the contract Plan 2's updater hardcodes:
  - GHCR: `ghcr.io/<owner-lc>/bndsphere-backend:<version>`, `ghcr.io/<owner-lc>/bndsphere-caddy:<version>`
  - Release assets: `bndsphere-images-amd64.tar.gz`, `release-manifest.json`, `SHA256SUMS`
  - `release-manifest.json` schema, exactly:
    ```json
    {
      "version": "v1.5.0",
      "arch": "amd64",
      "built_at": "2026-08-24T10:00:00Z",
      "commit": "<full sha>",
      "images": {
        "backend": {
          "ref": "ghcr.io/owner/bndsphere-backend:v1.5.0",
          "registry_digest": "sha256:...",
          "config_digest": "sha256:..."
        },
        "caddy": { "ref": "...", "registry_digest": "...", "config_digest": "..." }
      },
      "assets": { "tarball": "bndsphere-images-amd64.tar.gz" }
    }
    ```
  - `registry_digest` is what the updater pulls by on the GHCR path. `config_digest` (the local image ID) is what it checks after `docker load` on the tarball path. Both are recorded because they answer different questions.

- [ ] **Step 1: Write the workflow**

Create `.github/workflows/release.yml`:

```yaml
name: Release

on:
  push:
    tags:
      - "v*"
  workflow_dispatch:
    inputs:
      version:
        description: "Version tag to build (e.g. v1.5.0)"
        required: true
        type: string

permissions:
  contents: write
  packages: write

jobs:
  release:
    name: Build once, publish to GHCR and Release
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v6

      - name: Resolve version and image references
        id: meta
        shell: bash
        run: |
          set -euo pipefail

          if [ "${{ github.event_name }}" = "workflow_dispatch" ]; then
            version="${{ inputs.version }}"
          else
            version="${GITHUB_REF#refs/tags/}"
          fi

          # Same grammar the updater enforces (spec §8). Rejecting here means a
          # malformed tag fails at release time, not on someone's deploy host.
          if ! printf '%s' "$version" \
             | grep -Eq '^v?[0-9]+(\.[0-9]+){0,3}([-+][0-9A-Za-z.-]+)?$'; then
            echo "::error::Invalid version tag: $version"
            exit 1
          fi

          owner_lc="${GITHUB_REPOSITORY_OWNER,,}"   # GHCR requires lowercase

          {
            echo "version=$version"
            echo "backend_ref=ghcr.io/${owner_lc}/bndsphere-backend:${version}"
            echo "caddy_ref=ghcr.io/${owner_lc}/bndsphere-caddy:${version}"
          } >> "$GITHUB_OUTPUT"

      - name: Build backend and caddy images (exactly once)
        shell: bash
        run: |
          set -euo pipefail

          docker build \
            --build-arg APP_VERSION="${{ steps.meta.outputs.version }}" \
            --target prod \
            -f backend/Dockerfile \
            -t "${{ steps.meta.outputs.backend_ref }}" \
            backend

          docker build \
            --build-arg APP_VERSION="${{ steps.meta.outputs.version }}" \
            --target prod \
            -f infra/Dockerfile.Caddy \
            -t "${{ steps.meta.outputs.caddy_ref }}" \
            .

      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Push to GHCR and capture digests
        id: push
        shell: bash
        run: |
          set -euo pipefail

          backend_ref="${{ steps.meta.outputs.backend_ref }}"
          caddy_ref="${{ steps.meta.outputs.caddy_ref }}"

          docker push "$backend_ref"
          docker push "$caddy_ref"

          # RepoDigests is only populated after a successful push.
          backend_registry_digest=$(
            docker image inspect --format '{{index .RepoDigests 0}}' "$backend_ref" \
              | cut -d@ -f2
          )
          caddy_registry_digest=$(
            docker image inspect --format '{{index .RepoDigests 0}}' "$caddy_ref" \
              | cut -d@ -f2
          )

          # The local image ID — what `docker load` reproduces on the fallback path.
          backend_config_digest=$(docker image inspect --format '{{.Id}}' "$backend_ref")
          caddy_config_digest=$(docker image inspect --format '{{.Id}}' "$caddy_ref")

          for d in "$backend_registry_digest" "$caddy_registry_digest" \
                   "$backend_config_digest" "$caddy_config_digest"; do
            case "$d" in
              sha256:*) ;;
              *) echo "::error::Expected a sha256 digest, got: $d"; exit 1 ;;
            esac
          done

          {
            echo "backend_registry_digest=$backend_registry_digest"
            echo "caddy_registry_digest=$caddy_registry_digest"
            echo "backend_config_digest=$backend_config_digest"
            echo "caddy_config_digest=$caddy_config_digest"
          } >> "$GITHUB_OUTPUT"

      - name: Save the same images to a release tarball
        shell: bash
        run: |
          set -euo pipefail
          # NOTE: no rebuild. These are the exact local images just pushed, which
          # is what makes the fallback path equivalent to the registry path.
          docker save \
            "${{ steps.meta.outputs.backend_ref }}" \
            "${{ steps.meta.outputs.caddy_ref }}" \
            | gzip -9 > bndsphere-images-amd64.tar.gz

          ls -lh bndsphere-images-amd64.tar.gz

      - name: Write release manifest
        shell: bash
        run: |
          set -euo pipefail

          jq -n \
            --arg version        "${{ steps.meta.outputs.version }}" \
            --arg built_at       "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
            --arg commit         "$GITHUB_SHA" \
            --arg backend_ref    "${{ steps.meta.outputs.backend_ref }}" \
            --arg backend_rdig   "${{ steps.push.outputs.backend_registry_digest }}" \
            --arg backend_cdig   "${{ steps.push.outputs.backend_config_digest }}" \
            --arg caddy_ref      "${{ steps.meta.outputs.caddy_ref }}" \
            --arg caddy_rdig     "${{ steps.push.outputs.caddy_registry_digest }}" \
            --arg caddy_cdig     "${{ steps.push.outputs.caddy_config_digest }}" \
            '{
              version: $version,
              arch: "amd64",
              built_at: $built_at,
              commit: $commit,
              images: {
                backend: {
                  ref: $backend_ref,
                  registry_digest: $backend_rdig,
                  config_digest: $backend_cdig
                },
                caddy: {
                  ref: $caddy_ref,
                  registry_digest: $caddy_rdig,
                  config_digest: $caddy_cdig
                }
              },
              assets: { tarball: "bndsphere-images-amd64.tar.gz" }
            }' > release-manifest.json

          cat release-manifest.json

      - name: Write SHA256SUMS
        shell: bash
        run: |
          set -euo pipefail
          # Manifest must already exist — it is covered by these sums.
          sha256sum bndsphere-images-amd64.tar.gz release-manifest.json > SHA256SUMS
          cat SHA256SUMS

      - name: Create the GitHub Release
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        shell: bash
        run: |
          set -euo pipefail
          version="${{ steps.meta.outputs.version }}"

          if gh release view "$version" >/dev/null 2>&1; then
            gh release upload "$version" \
              bndsphere-images-amd64.tar.gz release-manifest.json SHA256SUMS \
              --clobber
          else
            gh release create "$version" \
              --title "$version" \
              --generate-notes \
              bndsphere-images-amd64.tar.gz release-manifest.json SHA256SUMS
          fi
```

- [ ] **Step 2: Lint the workflow**

Run:
```bash
python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/release.yml')); print('yaml ok')"
```
Expected: `yaml ok`

If `actionlint` is available, also run `actionlint .github/workflows/release.yml`. It is not installed by default; skip if absent rather than installing it.

- [ ] **Step 3: Verify the version validator against the same cases the updater will face**

The regex is duplicated between this workflow and the Plan 2 updater by design — each validates its own input at its own trust boundary. Confirm this copy behaves:

```bash
for v in v1.5.0 v1.5 1.5.0 v1.5.0-rc.1 v1.2.3.4 v1.5.0+build.7; do
  printf '%s' "$v" | grep -Eq '^v?[0-9]+(\.[0-9]+){0,3}([-+][0-9A-Za-z.-]+)?$' \
    && echo "ACCEPT $v" || echo "REJECT $v"
done
for v in 'v1.5.0; rm -rf /' '$(id)' '../../etc/passwd' 'latest' '' 'v1.5.0 v2'; do
  printf '%s' "$v" | grep -Eq '^v?[0-9]+(\.[0-9]+){0,3}([-+][0-9A-Za-z.-]+)?$' \
    && echo "ACCEPT $v" || echo "REJECT $v"
done
```
Expected: every value in the first loop `ACCEPT`, every value in the second `REJECT`.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "feat: add release workflow publishing to GHCR and release assets"
```

- [ ] **Step 5: Make the GHCR packages public**

This is a manual, one-time step in the GitHub UI, and it is easy to forget because nothing fails until a deploy host tries to pull. A private package surfaces on the host as an opaque authentication error, far from its cause.

After the first successful release run:
1. Go to the repository owner's **Packages** tab.
2. For each of `bndsphere-backend` and `bndsphere-caddy`: **Package settings → Danger Zone → Change visibility → Public**.

Verify from a logged-out client:
```bash
docker logout ghcr.io
docker pull ghcr.io/<owner-lc>/bndsphere-backend:<version>
```
Expected: the pull succeeds with no credentials (spec §18.1).

- [ ] **Step 6: End-to-end verification on a real tag**

```bash
git tag v0.0.1-test && git push origin v0.0.1-test
gh run watch
```

Then confirm the published artifacts are internally consistent — this is the property the updater depends on:

```bash
gh release download v0.0.1-test -D /tmp/relcheck
cd /tmp/relcheck

# 1. Checksums verify (this is the gate the updater applies before docker load)
sha256sum -c SHA256SUMS

# 2. The tarball contains exactly the two refs named in the manifest
tar -xzOf bndsphere-images-amd64.tar.gz manifest.json | jq -r '.[].RepoTags[]'
jq -r '.images[].ref' release-manifest.json

# 3. Loading reproduces the recorded config digests
docker load < bndsphere-images-amd64.tar.gz
docker image inspect --format '{{.Id}}' "$(jq -r '.images.backend.ref' release-manifest.json)"
jq -r '.images.backend.config_digest' release-manifest.json
```
Expected: `sha256sum -c` prints `OK` for both files; the ref lists match; the two digest values printed last are identical.

Clean up the throwaway release and tag:
```bash
gh release delete v0.0.1-test --yes --cleanup-tag
```
Also delete the `v0.0.1-test` GHCR package versions from the owner's Packages tab, so a test build is never pullable as if it were a real release.

---

### Task 4: Establish the N-1 database compatibility policy

Rollback restores images, not data. After a rollback the schema is at version N
while the application is N-1 — so **every rollback in this system is only as
safe as this policy** (spec §11). It is a review obligation on every migration,
which means it has to be written down somewhere reviewers actually look.

**Files:**
- Modify: `docs/architecture/database.md`
- Create: `backend/migrations/README.md`

**Interfaces:**
- Consumes: nothing.
- Produces: the documented policy Plan 2's rollback executor depends on. No code.

- [ ] **Step 1: Document the policy**

Append to `docs/architecture/database.md`:

```markdown
## N-1 compatibility policy

The deployment updater can roll the application back one version
(`docs/superpowers/specs/2026-08-24-deployment-updater-design.md` §12). It does
**not** roll the database back. After a rollback the schema is at version N
while the application is N-1.

**Therefore: migrations shipped with version N must leave the schema usable by
both application N and application N-1.**

Destructive changes are spread across three releases — expand, migrate,
contract:

| Release | Action |
|---|---|
| N | Add the new column/table. Backfill. Write to both old and new shapes. Drop nothing. |
| N+1 | Read from the new shape only. Still drop nothing. |
| N+2 | Drop the old column/table. |

A migration in release N must never immediately remove schema that release N-1
requires. Nothing enforces this automatically — the updater cannot inspect
intent — so it is checked at review time.

### Migration review checklist

- [ ] Does this migration drop a column, table, constraint, or enum value?
- [ ] If yes: was the thing being dropped already unused by the **previous**
      release, not merely by this one?
- [ ] Can the previous release's application still read and write successfully
      against the post-migration schema?
- [ ] Are new NOT NULL columns given a default or backfilled, so the previous
      release's inserts (which omit them) still succeed?
- [ ] Are renames expressed as add + backfill + later drop, never as a bare
      `ALTER ... RENAME`?

A "no" to any of the last four means the change must be split across releases.

### Partial-failure note

Alembic commits each revision separately, so a multi-revision upgrade that
fails partway leaves the schema advanced by some revisions but not all. The
updater aborts before replacing containers in that case, leaving the **old**
application running against a **partially advanced** schema. This policy is
what keeps that window survivable.
```

- [ ] **Step 2: Put the checklist where migrations are authored**

Create `backend/migrations/README.md`:

```markdown
# Migrations

Autogenerate a revision:

```bash
MESSAGE="describe the change" docker compose --profile autorevision up alembic-autorevision
```

## Before you merge: N-1 compatibility

The deployment updater can roll the application back one version without
rolling back the database. A migration shipped in release N must leave the
schema usable by application N-1.

Full policy and review checklist: `docs/architecture/database.md`.

Short version: **never drop in the same release you stop using something.**
Add and backfill in N, stop reading the old shape in N+1, drop in N+2.
```

- [ ] **Step 3: Verify the cross-references resolve**

```bash
test -f docs/architecture/database.md && grep -q "N-1 compatibility policy" docs/architecture/database.md \
  && echo "policy documented"
grep -q "docs/architecture/database.md" backend/migrations/README.md && echo "cross-reference ok"
```
Expected: both lines print.

- [ ] **Step 4: Commit**

```bash
git add docs/architecture/database.md backend/migrations/README.md
git commit -m "docs: add N-1 database compatibility policy for rollback safety"
```

---

## Plan 1 Completion Criteria

- [ ] Both images accept `--build-arg APP_VERSION` and report it as `$APP_VERSION` at runtime; omitting the arg yields `dev`.
- [ ] `deployment_settings().app_version` reads that env var, defaulting to `dev`. Tests pass.
- [ ] `docker compose config` resolves to local image names with no env file, and to pinned refs with `--env-file deploy/versions.env`. Postgres resolves to `bndsphere-postgres` in both cases.
- [ ] `deploy/versions.env` is git-ignored; only `.example` is tracked.
- [ ] `deploy/bootstrap.sh` resolves `COMPOSE_PROJECT_DIR` to `pwd -P`, upserts it into `.env`, is idempotent, never clobbers an existing `versions.env`, and exits non-zero outside a real deployment.
- [ ] A tagged push produces a Release carrying `bndsphere-images-amd64.tar.gz`, `release-manifest.json`, and `SHA256SUMS`, and pushes both images to GHCR.
- [ ] `sha256sum -c SHA256SUMS` passes on the downloaded assets.
- [ ] The tarball's loaded config digests match `release-manifest.json` — proving both delivery paths came from one build.
- [ ] Both GHCR packages are public and pull without credentials.
- [ ] The N-1 compatibility policy and migration review checklist are documented in `docs/architecture/database.md` and referenced from `backend/migrations/README.md`.

**Next:** `docs/superpowers/plans/2026-08-24-updater-sidecar.md` (Plan 2).
