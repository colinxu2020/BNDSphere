# Deployment Updater & Dev Panel — Design

Date: 2026-08-24
Status: Approved for planning

## 1. Context

BNDSphere is deployed as a Docker Compose stack (`postgres`, `alembic-migration`,
`backend`, `caddy`). Today there is no release pipeline at all: `git tag` and
`gh release list` are both empty, `.github/workflows/docker.yml` only lints and
scans, and `docker-compose.yml` references locally-built image names
(`bndsphere-backend`, `bndsphere-caddy`, `bndsphere-postgres`) with no registry.
Updating production means someone SSHing in and rebuilding by hand.

This design adds two things that must ship together:

1. A **release pipeline** that publishes versioned `backend` and `caddy` images
   through two delivery paths (GHCR and a GitHub Release tarball).
2. A **developer panel** (`RoleEnum.dev` only) that shows the deployed version
   against the latest release and can trigger an update or a rollback, executed
   by a privileged **updater sidecar**.

The application frontend is baked into `bndsphere-caddy`; the backend and its
Alembic migrations are baked into `bndsphere-backend`. An "update" is therefore
a new pair of images plus a migration step.

## 2. Goals

- Show current version, previous version, and latest upstream release.
- One-click update, with automatic rollback if the new version fails health checks.
- One-click manual rollback to the previous version.
- Durable, inspectable state: an administrator can always tell exactly which
  stage an operation reached and why it stopped.
- Verify release artifacts before executing them.
- Keep the privileged surface as small and as explicitly documented as possible.

## 3. Non-goals

- PostgreSQL upgrades. Postgres is pinned independently and is never touched by
  an application update or rollback. Major-version upgrades are a separate
  maintenance workflow with their own backup/restore procedure.
- Database rollback. Application rollback is not data rollback (see §11).
- Multi-host or multi-replica orchestration. This is a single-host Compose stack.
- Artifact signing in v1. The design leaves a slot for it (§6.4).

## 4. Security boundary

This section is normative. It must not be softened during implementation.

**The updater sidecar mounts `/var/run/docker.sock`. Access to the Docker socket
is equivalent to root on the host.** A process that can talk to the Docker daemon
can start a privileged container that bind-mounts `/`, and from there do anything.

Therefore:

| Component | If compromised |
|---|---|
| `backend` | Application data is compromised. The host is **not**. |
| `updater` | **Assume the host is fully compromised.** |

`read_only`, `cap_drop: ALL`, `no-new-privileges`, and request validation reduce
the updater's attack surface. **They do not make Docker socket access safe** and
must never be described as doing so. They make it harder to reach the socket;
they do nothing once you have.

The design consequences that follow from this:

- The updater has **no HTTP listener and no published port** (§7). It cannot be
  reached over the network, only through a filesystem request path.
- The updater takes **no commands** from the backend — only a validated version
  identifier (§8). Image names, service names, URLs, registries, and asset names
  are all derived from the updater's own configuration.
- The backend **cannot write to the updater's status or log output** (§7), so a
  compromised backend cannot forge a "rollback succeeded" record.
- The updater treats the request as **untrusted input** even though the only
  writer is the backend.

## 5. Architecture

```
GitHub Actions (tag v*)
  └─ builds backend + caddy ONCE
     ├─ pushes to ghcr.io/colinxu2020/bndsphere-{backend,caddy}:<version>
     └─ docker save ──▶ Release assets:
                          bndsphere-images-amd64.tar.gz
                          release-manifest.json
                          SHA256SUMS

Host: /opt/bndsphere  (COMPOSE_PROJECT_DIR)
  ├─ docker-compose.yml            (ro in updater)
  ├─ deploy/versions.env           (rw in updater — the deployed image pins)
  ├─ secrets/                      (ro, resolved host-side)
  └─ Compose project "bndsphere"
       ├─ postgres      (never updated)
       ├─ backend       ─── writes ──▶ request volume ─── reads ──▶ updater
       ├─ caddy                        status volume  ◀── writes ── updater
       └─ updater       (docker.sock, no ports, no listener)
```

### 5.1 New and changed files

**Release pipeline**
- `.github/workflows/release.yml` — new.
- `backend/Dockerfile`, `infra/Dockerfile.Caddy` — add `ARG APP_VERSION` → `ENV APP_VERSION`.

**Compose**
- `docker-compose.yml` — parameterise image refs; add `updater` service and two volumes.
- `docker-compose.build.yml` — unchanged behaviour for local builds.
- `deploy/versions.env.example` — new, committed template (§18.2).
- `deploy/versions.env` — host deployment state. Bootstrapped on first deploy,
  updated atomically by the updater, **git-ignored — never committed**.
- `.gitignore` — add `deploy/versions.env`.

**Updater**
- `infra/Dockerfile.Updater` — new (`docker:cli` + compose plugin + `curl`, `jq`, `coreutils`).
- `infra/updater/updater.sh` — new, the poll loop and state machine.
- `infra/updater/selfcheck.sh` — new, assertion-based checks for validation and version compare.

**Backend**
- `app/api/v1/dev/__init__.py` — new router, `RoleChecker([RoleEnum.dev])`.
- `app/api/v1/dev/deployment.py` — new endpoints.
- `app/services/deployment.py` — new: GitHub Releases client, version compare, state I/O.
- `app/schemas/deployment.py` — new.
- `app/core/settings.py` — add `DeploymentSettings`.
- `app/api/v1/__init__.py` — register the dev router.

**Frontend**
- `src/pages/DevPanel.tsx` — new.
- `src/api/deployment.ts` — new, following the existing `src/api/admin.ts` pattern.
- `src/App.tsx` — lazy dev-gated route.

**Tests**
- `backend/tests/test_deployment.py` — new.
- `infra/updater/selfcheck.sh` — new.
- Crash-recovery tests, one per durable stage boundary (§19).

## 6. Release pipeline

### 6.1 Build once, publish twice

Triggered on pushing a tag matching `v*`. The workflow builds `backend` and
`caddy` **exactly once** each, with `--build-arg APP_VERSION=<tag>`, then:

1. Pushes both to GHCR as `ghcr.io/colinxu2020/bndsphere-<component>:<version>`.
   Capture the resulting registry manifest digests.
2. `docker save` **the same local image IDs** into `bndsphere-images-amd64.tar.gz`.
   No rebuild — the tarball and the registry hold the same bits by construction.
3. Emit `release-manifest.json` recording, for each component: the GHCR
   reference, the registry manifest digest, and the local image config digest.
4. Emit `SHA256SUMS` covering the tarball and `release-manifest.json`.
5. Create the GitHub Release with all three assets attached.

Both delivery paths are traceable to one build, which is what makes the fallback
path trustworthy rather than merely convenient.

### 6.2 Version stamping

`APP_VERSION` is baked into both images as an environment variable. The backend
reports its own `APP_VERSION` as the current version; it never infers the version
from anything mutable.

### 6.3 Artifact verification

- **GHCR path**: pull by immutable digest (`...@sha256:...`) taken from
  `release-manifest.json`, never by mutable tag.
- **Tarball path**: verify the download against `SHA256SUMS` **before**
  `docker load`. A checksum mismatch aborts the operation; the file is deleted
  and the stage is recorded as `failed`. After a successful load, verify the
  loaded image config digest matches the manifest.

Under no circumstances is a downloaded file passed to `docker load` unverified.

### 6.4 Future hardening

`release-manifest.json` is currently trusted because it arrives over TLS from the
GitHub API. Signing (Sigstore/Cosign over the GHCR digests and over `SHA256SUMS`)
closes that gap and is the intended next step. The manifest indirection exists
partly so signing can be added without reshaping the updater.

## 7. Shared state: split by trust direction

Two named volumes, mounted with opposite permissions:

| Volume | `backend` | `updater` |
|---|---|---|
| `updater_request` | `rw` | `ro` |
| `updater_status` | `ro` | `rw` |

The backend can request work. It cannot write the record of what happened. The
updater can record what happened. It cannot forge a request from itself.

```
request/request.json    backend writes, updater reads
status/state.json       updater writes, backend reads
status/update.log       updater appends, backend reads (bounded tail)
status/deployed.json    updater writes — current_version, previous_version, digests
```

`update.log` is truncated to a bounded size (last 2000 lines / 256 KiB) so a
looping failure cannot fill the volume.

**`state.json` vs `deployed.json`.** They are not redundant. `state.json` is
per-operation and churns on every stage transition. `deployed.json` is the
durable deployment record — current version, previous version, and the image
digests for both — and is written only at a terminal success. Rollback targets
are read from `deployed.json`, never from in-flight operation state.

**Source of truth for "current version".** The running backend's baked-in
`APP_VERSION` (§6.2) is ground truth for what is actually serving;
`deployed.json` is the updater's record of what it last deployed. They should
agree. If they disagree — an administrator deployed by hand, say — the panel
displays the running `APP_VERSION` and flags the divergence, and rollback is
disabled until a normal update reconciles them. Trusting the record over the
process is how an updater talks confidently about a version that isn't running.

## 8. Request protocol — a deliberately narrow surface

`request/request.json` is the **only** application-level input the updater accepts:

```json
{
  "id": "<uuid4>",
  "action": "update" | "rollback",
  "version": "v1.5.0",
  "requested_at": "2026-08-24T10:00:00Z"
}
```

That is the whole schema. The backend never supplies image names, Compose service
names, Compose project names, registry hostnames, URLs, asset filenames, shell
fragments, or arbitrary arguments.

The updater derives everything else from its own environment:

- repository (`colinxu2020/BNDSphere`)
- backend image name, caddy image name
- Compose project name (`bndsphere`) and project directory
- the exact Compose service list it is allowed to recreate: `backend`, `caddy`
- release asset naming convention

**Validation, performed by the updater before the value reaches any command:**

- `id` must be a well-formed UUID and must differ from the last processed id
  recorded in `state.json` (replay/restart protection).
- `action` must be exactly `update` or `rollback`.
- `version` must match `^v?[0-9]+(\.[0-9]+){0,3}([-+][0-9A-Za-z.-]+)?$` and be at
  most 64 characters.
- For `rollback`, `version` must equal the recorded `previous_version` exactly.
- Anything else: the request is rejected, logged, and the id is marked processed.

Validated values are passed as **argument-vector arguments** to `docker` and
`curl`. The updater never uses `sh -c`, `eval`, backticks, or unquoted expansion
on request-derived data.

## 9. Updater state machine

Stages are durable — written to `status/state.json` on every transition, so a
backend restart (which happens on every update, by design) loses nothing.

```
idle ──▶ checking ──▶ downloading ──▶ verifying ──▶ migrating ──▶ deploying
                                                                     │
                                                                     ▼
                                                             health_checking
                                                              │           │
                                                        (healthy)     (unhealthy)
                                                              │           │
                                                              ▼           ▼
                                                          success   rolling_back
                                                                     │        │
                                                                     ▼        ▼
                                                        rollback_success   failed
```

Terminal stages: `success`, `rollback_success`, `failed`, `idle`.

`state.json` persists:

```json
{
  "stage": "health_checking",
  "action": "update",
  "request_id": "…",
  "last_processed_request_id": "…",
  "requested_version": "v1.5.0",
  "target_version": "v1.5.0",
  "previous_version": "v1.4.3",
  "delivery_path": "ghcr" | "tarball",
  "started_at": "…", "updated_at": "…", "finished_at": null,
  "error_code": null, "error_message": null,
  "log_tail": ["…"]
}
```

**Locking.** The lock is owned by the updater, not the backend. A single poll
loop holds an exclusive lock file in the status volume for the duration of an
operation. A request arriving while a non-terminal stage is active is rejected
with `error_code: "busy"` and the id marked processed. The backend also
pre-checks stage on `POST` and returns `409`, but that check is advisory — the
updater's lock is authoritative.

**Updater restart mid-operation.** On startup, if `state.json` holds a
non-terminal stage, the updater does **not** attempt to resume. It probes actual
system state, records what it found, and transitions to `failed` with
`error_code: "interrupted"`, preserving the stage it was interrupted at. Full
per-stage recovery and idempotency semantics are specified in §19 — that section
is normative for the implementation, not commentary.

## 10. Update flow

Preconditions checked first: request valid, no operation in flight, requested
version differs from `current_version` (otherwise `error_code: "already_current"`,
terminal, no containers touched).

1. **checking** — fetch the release and `release-manifest.json` for the target
   version. Record `previous_version = current_version`.
2. **downloading** — try GHCR first: `docker pull <image>@<digest>` for backend
   and caddy. On any failure, fall back to downloading
   `bndsphere-images-amd64.tar.gz` and `SHA256SUMS`. Record `delivery_path`.
3. **verifying** — GHCR path: the digest pull is self-verifying. Tarball path:
   check `sha256sum -c` against `SHA256SUMS`, then `docker load`, then confirm
   loaded image config digests match the manifest. Mismatch aborts here, before
   anything is deployed.
4. **migrating** — explicitly run the migration with the **new** backend image
   against the live database, while the **old** application is still serving:

   ```
   BACKEND_IMAGE="<new backend ref>" \
   docker compose --project-directory "$COMPOSE_PROJECT_DIR" \
                  -f "$COMPOSE_PROJECT_DIR/docker-compose.yml" \
                  --env-file "$COMPOSE_PROJECT_DIR/deploy/versions.env" \
                  -p bndsphere run --rm alembic-migration
   ```

   Note the `BACKEND_IMAGE` override. `deploy/versions.env` still holds the
   **old** pins at this point — it is not rewritten until step 5, so that an
   abort here leaves the durable pins pointing at the running version. Compose
   gives shell environment precedence over `--env-file`, so the override is what
   selects the new image for this one invocation. Getting this backwards would
   silently run the *old* migrations and call it a successful upgrade.

   A non-zero exit aborts the update **before** any application container is
   replaced. This is deliberate: `docker compose up backend caddy` is never
   relied on to implicitly rerun migrations via `depends_on`.

   Running the new migrations against the old application is safe only because
   of the N-1 compatibility policy in §11.

5. **deploying** — write the new pins to `deploy/versions.env`, then
   `docker compose … up -d backend caddy`. Only these two services, hardcoded.
   Postgres is never named.
6. **health_checking** — wait for the new backend to be genuinely serving, not
   merely started:
   - `docker inspect` container health reaches `healthy` for `backend` and `caddy`;
   - **and** an application-level readiness probe succeeds: `GET http://backend:8000/health`
     returns 204, and `GET http://caddy:8080/` returns 2xx.
   - Timeout 120s with a short poll interval.

   `docker compose up` exiting 0 is **not** success and must never be treated as such.

   The readiness probe requires the updater to reach `backend` and `caddy`, so
   the updater joins `backend-network` (which is also its egress route to GHCR
   and the GitHub API). This is outbound only — the updater still publishes no
   port and runs no listener (§7), so nothing on that network can initiate a
   connection *to* it. Attaching it does not widen the surface a compromised
   backend can reach.
7. **success** — only now write `current_version = target_version` and
   `previous_version = <the version replaced>` to `deployed.json`. The previous
   images are **retained**, not pruned, so rollback needs no network.

If step 6 fails, the updater transitions to **rolling_back** automatically (§12).

## 11. Database compatibility policy (N-1)

Application rollback restores images. It does **not** restore the database.
After a rollback, the schema remains at version N while the application is N-1.

**Policy: migrations shipped with version N must leave the schema usable by both
application N and application N-1.**

Destructive changes follow expand → migrate → contract across releases:

| Release | Action |
|---|---|
| N | Add the new column/table. Backfill. Write to both old and new. Do not drop anything. |
| N+1 | Read from the new shape only. Still do not drop. |
| N+2 | Drop the old column/table (the contract step). |

A migration in release N must never immediately remove schema that release N-1
requires. Rollback from N to N-1 is only safe under this discipline, and the
discipline is a review obligation on every migration, not something the updater
can enforce.

**Consequence of a mid-migration failure.** Alembic commits each revision
separately, so a multi-revision upgrade that fails partway leaves the schema
advanced by some revisions. The N-1 policy is what keeps the still-running old
application functional in that window. The failure is recorded with the last
successfully applied revision so an administrator can decide how to proceed.

Postgres itself is untouched throughout.

## 12. Rollback

### 12.1 One execution path, two triggers

Automatic and manual rollback are **the same code path and the same state
machine**, not two implementations that happen to agree. There is a single
executor:

```
rollback(target_pins, trigger)   trigger ∈ { "automatic", "manual" }
```

It performs exactly one sequence, whoever called it:

1. Assert the target images are present locally (`docker image inspect` by
   digest). Absent → `failed` / `rollback_unavailable`, nothing touched.
2. Atomically rewrite `deploy/versions.env` to the previous pins (§13.1).
3. `docker compose … up -d backend caddy` — the same hardcoded service list.
4. The **same** health check as §10.6 — identical probe, identical timeout.
5. `rollback_success`, with `current_version` reset to the previous version,
   or `failed` / `rollback_failed`.

`trigger` is **recorded in `state.json` and never branched on**. It exists for
the panel and the audit log, not for control flow. A divergence between the
automatic and manual paths is exactly the kind of bug that only shows up during
an incident, when the rarely-exercised branch is the one you need.

Automatic rollback is therefore not a separate feature: a failed health check in
§10.6 calls `rollback(previous_pins, trigger="automatic")`. Manual rollback is
`POST /api/v1/dev/deployment/rollback` calling `rollback(previous_pins,
trigger="manual")`.

### 12.2 Preconditions and constraints

Manual rollback is permitted only when a `previous_version` is recorded in
`deployed.json` and its images are still present locally — guaranteed by the
retention rule in §18.3.

**Rollback never runs migrations, forward or backward, under either trigger.**
The schema stays at N while the application returns to N-1; §11's compatibility
policy is what makes that safe. No migration is ever reversed automatically.

`rollback_failed` is the highest-severity terminal state in the system: the new
version is unhealthy *and* the old one would not come back. The panel surfaces it
as an operator-attention state with the full log retained.

## 13. Compose project directory

Bind-mount source paths in `docker-compose.yml` (notably `./secrets/*` and
`./backend/migrations/versions`) are resolved by the **host** Docker daemon, not
inside the updater container. If the updater guesses the location, secrets
silently resolve to empty or missing paths and the stack comes up broken.

The deployment directory is therefore **explicit, not inferred**:

- `COMPOSE_PROJECT_DIR` is a required environment variable holding the absolute
  host path (e.g. `/opt/bndsphere`).
- The host directory is bind-mounted into the updater **at that identical path**,
  read-only, so client-side and daemon-side path resolution agree.
- `deploy/` is bind-mounted read-write at the same nested path, so the updater
  can persist `versions.env` while the rest of the project stays read-only.
- Every Compose invocation passes `--project-directory`, `-f <abs path>`,
  `--env-file`, and `-p bndsphere` explicitly. No reliance on the working directory.
- **Startup validation**: the updater refuses to start if `COMPOSE_PROJECT_DIR`
  is unset, is not an absolute path, does not exist at the expected path, or does
  not contain `docker-compose.yml` and `secrets/`. Failing at boot beats failing
  halfway through a deploy.

### 13.1 Atomic durable writes

Every durable file the updater owns — `state.json`, `deployed.json`, and
`deploy/versions.env` — is written **write-temp-then-`rename()`** within the same
filesystem, never edited in place. `rename()` is atomic on POSIX, so a reader
sees either the old complete file or the new complete file, never a truncated one.

This matters because the updater can be killed at any instant (§19), and a
half-written `versions.env` would make the entire stack unstartable — including
by hand, including for rollback. Readers may tolerate a *missing* file; no reader
is required to tolerate a *partial* one.

`update.log` is append-only and exempt; a truncated final log line is harmless.

## 14. Backend API

New router at `/api/v1/dev`, gated on `RoleChecker([RoleEnum.dev])` — separate
from `/api/v1/admin`, so `RoleEnum.admin` does **not** grant deployment control.

| Method | Path | Behaviour |
|---|---|---|
| `GET` | `/deployment/status` | Current + previous version, latest release (tag, published_at, notes, url), update-available flag, full updater state, bounded log tail. |
| `POST` | `/deployment/check` | Force-refresh the GitHub release cache. |
| `POST` | `/deployment/update` | Write an update request. `409` if an operation is in flight, `400` if already current. |
| `POST` | `/deployment/rollback` | Write a rollback request for the recorded previous version. `409` if in flight, `400` if no previous version. |

`DeploymentSettings`: `github_repo`, optional `github_token` (from `/run/secrets`,
raising the API rate limit and enabling private-repo reads), `app_version`,
`request_dir`, `status_dir`. GitHub responses are cached ~5 minutes; `httpx`
already ships with `fastapi[standard]`, so no new dependency.

## 15. Dev panel

`src/pages/DevPanel.tsx`, following the reference layout: repo / current version /
latest release cards, a details block, release notes, and the action row.
Rollback is surfaced from the start:

```
Current: v1.5.0     Previous: v1.4.3     [Rollback to v1.4.3]
```

Labels are in **Chinese**, matching every other page (`ROLE_MAP` etc.) rather
than the English reference screenshot. Built from existing `AppPrimitives`
(`PageHeader`, `Badge`, `PrimaryButton`, `SecondaryButton`, `StatusMessage`).

While a non-terminal stage is active the panel polls `/status` every 3 seconds
and renders the stage plus the live log tail. **It must tolerate the backend
disappearing** — the backend is replaced during its own update — by treating
connection errors as "still deploying" and resuming once `/status` answers again.
This is exactly what the split state volumes make possible.

## 16. Failure semantics

Every row leaves a terminal stage, an `error_code`, and a log tail sufficient to
locate the stop point.

| Failure | Stage reached | Behaviour |
|---|---|---|
| GHCR unreachable | `downloading` | Fall back to tarball; `delivery_path: "tarball"`. Not an error. |
| Both paths unreachable | `downloading` → `failed` | `download_failed`. Nothing deployed. |
| Tarball download interrupted | `downloading` → `failed` | Partial file deleted. `download_failed`. Nothing deployed. |
| Checksum mismatch | `verifying` → `failed` | **Never loaded.** File deleted. `checksum_mismatch`. Nothing deployed. |
| `docker load` failure | `verifying` → `failed` | `load_failed`. Nothing deployed. |
| Loaded digest ≠ manifest | `verifying` → `failed` | `digest_mismatch`. Nothing deployed. |
| Migration failure | `migrating` → `failed` | Aborts **before** containers are replaced. Old app keeps running. `migration_failed`, with the last applied revision recorded. Schema may be partially advanced; N-1 policy covers the window. |
| Backend fails to start | `deploying` → `rolling_back` | Automatic rollback. |
| Starts but health check fails | `health_checking` → `rolling_back` | Automatic rollback. `health_check_failed`. |
| Rollback succeeds | `rollback_success` | `current_version` reset to previous. Panel shows the update failed and was reverted. |
| Rollback fails | `failed` | `rollback_failed` — highest-severity state. Stack needs manual attention; full log retained. |
| Updater restarts mid-operation | `failed` | `interrupted`, preserving the interrupted stage. State probed and recorded per §19. No auto-resume. |
| Request for the current version | `idle` | `already_current`. Rejected before any work. No containers touched. |
| Concurrent update/rollback | unchanged | Updater lock rejects with `busy`; backend also returns `409`. In-flight operation is unaffected. |

## 17. Testing

**`backend/tests/test_deployment.py`**
- Role gating: `user` → 403, `admin` → 403, `dev` → 200. The admin exclusion is
  a deliberate privilege boundary and gets its own assertion.
- `/status` shape against a mocked GitHub response, including the rate-limited
  and unreachable cases.
- Version comparison table, including `v` prefixes, differing segment counts,
  and pre-release suffixes.
- `POST /update` writes a well-formed request file; `409` when a non-terminal
  stage is present; `400` when already current.
- Backend cannot write the status volume (mount permissions honoured).

**`infra/updater/selfcheck.sh`** — assertion-based, no framework:
- The version validator rejects `; rm -rf /`, `$(id)`, backticks, newlines,
  path traversal, over-length input, and empty input; accepts valid tags.
- Version comparison agrees with the backend's table.
- Rollback requests whose version ≠ recorded `previous_version` are rejected.
- Startup validation fails fast on a missing/relative `COMPOSE_PROJECT_DIR`.
- Atomic write helper (§13.1) leaves no partial file when interrupted between
  temp write and rename.
- Retention (§18.3) deletes only non-current, non-previous digests in the two
  BNDSphere repositories, and refuses any input naming another repository.

**Crash recovery — one test per durable boundary (§19).** The updater is killed
and restarted at each of `downloading`, `verifying`, `migrating`, `deploying`,
`health_checking`, and `rolling_back`, asserting in every case that recovery
probes actual state, records an `observed` block, marks the request processed,
and lands on `failed`/`interrupted` without resuming.

Two cases get dedicated tests because they are the ones that bite:

- **Killed immediately *after* the operation completed but *before* state was
  written** — for `migrating` (Alembic already at the target revision) and for
  `deploying` (containers already recreated). The probe must report completion,
  not repeat or misreport the work.
- **The unverified-deploy case (§19.4)** — killed after containers are recreated
  but before any health check. The recovery state must be distinguishable from a
  plain `interrupted`, since this is the one crash outcome where the stack looks
  healthy and is not known to be.

Migration ambiguity (§19.5) is tested at all three revision positions: old,
target, and partway through a multi-revision upgrade.

**Rollback path unification (§12.1)** — an explicit test that the automatic and
manual triggers execute the same sequence and differ only in the recorded
`trigger` field, so the two cannot drift apart.

## 18. Resolved decisions

### 18.1 GHCR visibility

GHCR packages are **public** in v1. The deploy host needs no registry
credentials and no pull secret, and the updater carries no registry
authentication code.

The verified GitHub Release tarball fallback (§6.1, §6.3) is retained
regardless — not as a credential workaround, but for hosts that cannot reliably
reach `ghcr.io`. Given this repository is mirrored from Gitee and deployed in a
network where registry reachability is genuinely uncertain, the fallback is the
expected path often enough that it must stay first-class and fully verified.

Making the packages public is a one-time manual step in GitHub package settings;
the plan includes it as an explicit release-pipeline task, because a private
package fails only at deploy time on the host, with a confusing auth error.

### 18.2 `deploy/versions.env` is deployment state, not source

`versions.env` records what a *particular host* has deployed. It is not
source-of-truth in Git and must never be treated as such.

- **Committed**: `deploy/versions.env.example` only — a documented template with
  the variable names and the local-build defaults.
- **Real file**: bootstrapped on first deployment (copied from the template if
  absent), and thereafter owned and updated by the updater, always atomically
  per §13.1.
- **Git-ignored**: `deploy/versions.env` is added to `.gitignore`, so a host's
  deployed state can never be committed over another host's.
- **Not ground truth**: the running backend's baked-in `APP_VERSION` remains
  ground truth for what is serving (§7). `versions.env` is what Compose will
  start *next*; `APP_VERSION` is what is running *now*. When they disagree, the
  panel believes `APP_VERSION`.

### 18.3 Image retention in v1

**Always preserve at least the current and previous `bndsphere-backend` and
`bndsphere-caddy` images.** This is what makes rollback work without a network,
so it is a correctness requirement, not an optimisation.

Scope limits, stated as prohibitions because the failure mode is destroying
something that was never ours:

- **No `docker image prune`, no `docker system prune`, no filtered bulk
  deletion.** Ever.
- The updater may delete **only** images in the two `bndsphere-backend` /
  `bndsphere-caddy` repositories, **only** by exact digest, and **only** when
  that digest is neither current nor previous in `deployed.json`.
- Unrelated host images are never enumerated, never touched. The host may be
  running other workloads; they are not ours to garbage-collect.
- A deletion that the daemon reports as in-use is logged and skipped, never forced.

Anything more sophisticated — age-based GC, disk-pressure triggers, configurable
depth — is future work. v1 accumulating a few hundred MB of old images is a much
cheaper mistake than v1 deleting an image someone needed.

## 19. Crash recovery and idempotency

The updater can be killed at any instant: host reboot, OOM, `docker restart`, or
the deploy it is running racing its own container. Every durable stage therefore
needs defined recovery semantics.

### 19.1 The core problem: intent vs. completion

State is written *around* side-effecting commands, so a crash can always land in
the gap between "command finished" and "state recorded". The updater can never
determine from its own state file whether the last operation completed.

**Therefore recovery never infers from recorded state. It probes the world.**

Before each side-effecting command the updater durably records an intent
descriptor (`stage` plus `in_flight_op`). On restart, if `in_flight_op` is set,
it runs that stage's **probe** — an observation of actual system state — and
records the answer. The probe, not the log, is authoritative.

### 19.2 Policy: reconcile and stop, never auto-resume

On restart with a non-terminal stage the updater:

1. Runs the probe for the interrupted stage.
2. Writes an `observed` block into `state.json` (images present, DB revision,
   running image refs, `versions.env` contents).
3. Reaps orphaned `--rm` helper containers by Compose project label.
4. Marks the interrupted request id as processed, so it can never silently re-run.
5. Transitions to `failed` with `error_code: "interrupted"`, preserving the
   interrupted stage.

It then waits for a new explicit request. Auto-resuming a half-completed deploy —
or worse, auto-rolling-back on boot — is more dangerous than stopping loudly.

### 19.3 Per-stage semantics

| Stage | What may be half-done | Probe on restart | Idempotent to redo? |
|---|---|---|---|
| `checking` | Nothing; read-only API calls. | None needed. | Yes, fully. |
| `downloading` | Partial asset on disk. | Temp file existence. Downloads go to a temp path and are `rename()`d only when complete, so a partial file is never mistaken for a good one. | Yes — delete temp and re-download. |
| `verifying` | `docker load` may have completed. | `docker image inspect` the config digests from `release-manifest.json`. Exact answer. | Yes — reloading identical content yields the identical image ID. |
| `migrating` | **The ambiguous case.** Migration may have not started, partly applied, or fully applied. | Query `alembic_version` in the live database and compare against the target revision. Authoritative and independent of updater state. | **No.** Never re-run blindly. Record the observed revision and stop. |
| `deploying` | Containers may or may not have been recreated; `versions.env` is atomic so it is never partial. | `docker inspect` the running `backend`/`caddy` image refs and compare to intended pins. | Yes — `up -d` converges to the pinned state. |
| `health_checking` | Nothing; purely observational. | None needed. | Yes, fully. |
| `rolling_back` | Same as `deploying`, targeting previous pins. | Same probe as `deploying`, compared against previous pins. | Yes. |

### 19.4 The dangerous recovery case, called out explicitly

A crash during `deploying` or `health_checking` can leave the **new containers
running and never health-verified**. This is the one recovery state that is
silently bad: the stack looks up, and nothing has reported a failure.

The probe detects it — running image refs match the new pins while no terminal
success was recorded — and the panel must surface it distinctly from an ordinary
`interrupted`: *"vN is running but was never verified."* The operator then
explicitly re-runs the health check or rolls back. The updater does not decide
this on their behalf.

### 19.5 Migration ambiguity

The `migrating` probe compares `alembic_version` against the revision shipped in
the target image, giving three outcomes:

- **At the old revision** — migration did not take effect. Safe to retry via a
  new request.
- **At the target revision** — migration completed; the crash was after the fact.
  A new request skips straight past migration (it is already satisfied).
- **Between the two** — a multi-revision upgrade partly applied. Recorded
  explicitly with both revisions. §11's N-1 policy is what keeps the still-running
  old application working in this window. Resolution is an operator decision.

In all three cases the schema is only ever *forward* of where it was, which is
why the N-1 policy is load-bearing rather than merely tidy.

### 19.6 Request idempotency

`last_processed_request_id` is advanced as part of the recovery transition
(§19.2 step 4), inside the same atomic `state.json` write. A crash can therefore
never cause a request to execute twice — the worst case is a request that is
marked processed having done nothing, which is visible and safely re-requestable.

## 20. Amendments during implementation

**§19 (crash recovery and idempotency) is reduced.** The per-stage probes, the
`observed` block, and the distinct `unverified_deploy` outcome are withdrawn. On
restart, a non-terminal stage is marked `failed` / `interrupted`, preserving the
stage it stopped at, and requires an explicit new request. No probing, no
auto-resume, no auto-rollback.

Rationale: that machinery existed to reconstruct which side of a state-write gap a
long-running sidecar died on. It is out of proportion to a single-host deployment,
and the guarantee it was protecting is already held elsewhere — Task 5's health
gate refuses to record success unless the running containers match the intended
images, so an interrupted deploy cannot be mistaken for a completed one. §16's
failure table still holds for every row except the `unverified_deploy` case, which
now reports plain `interrupted`.

**Periodic update checking added.** §14 originally offered only an on-demand
`/check`. The panel now also surfaces new releases without interaction: the
backend caches the release lookup for 5 minutes and the panel polls `/status` on a
timer. No scheduler is introduced.

**The GHCR delivery path is withdrawn.** §6 and §18.1 describe publishing to
both GHCR and a GitHub Release tarball; only the tarball path ships. The
release workflow no longer logs in to or pushes to GHCR, and `pull_from_ghcr`
is removed from `lib/artifact.sh`. `release-manifest.json` drops
`registry_digest` (it had no meaning without a registry) and keeps
`config_digest`, which the updater still uses to verify a loaded image
against the manifest. `delivery_path` in `state.json` is unaffected in shape
and is now always `"tarball"`. Rationale: the repository is public and
anonymous release-asset download already works with no credentials, whereas
GHCR was the only thing requiring a manual package-visibility change and
registry credentials on the deploy host; removing it deletes code, config,
and a manual step, and drops the delivery path least likely to be reachable
from the deployment's network. The only thing lost is layer deduplication
across releases, which does not matter when updates are infrequent.

## 21. Open items

None.
