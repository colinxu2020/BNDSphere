# Updater Sidecar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A privileged sidecar that consumes a narrowly validated version request from a filesystem path and performs a verified, migration-gated, health-checked update with automatic rollback — surviving its own termination at any stage.

**Architecture:** A POSIX-sh poll loop over a read-only request directory, writing durable stage transitions to a separate write-only status directory. Side-effecting commands are bracketed by intent records; on restart the updater probes actual system state rather than trusting what it last wrote. Forward deploy and rollback share one executor. The updater has no listener and accepts no commands — only a version string.

**Tech Stack:** POSIX sh, `docker:cli` + Compose v2 plugin, `curl`, `jq`, `coreutils`, Docker Compose, GHCR.

**Spec:** `docs/superpowers/specs/2026-08-24-deployment-updater-design.md`

## Global Constraints

- Plan 2 of 3. Requires Plan 1 complete (published releases exist). Plan 3 (dev panel) writes the requests this plan consumes; do not implement the backend API or frontend here.
- **The updater mounts `/var/run/docker.sock`. Updater compromised = assume host compromised** (spec §4). `read_only`, `cap_drop`, `no-new-privileges`, and validation reduce surface; they do **not** make socket access safe and must never be commented as if they do.
- The request contains **only** `id`, `action`, `version`, `requested_at` (spec §8). The updater derives repository, image names, Compose project, service list, and asset names from its own configuration. Never from the request.
- **Never** `sh -c`, `eval`, backticks, or unquoted expansion on request-derived data. Pass validated values as argument-vector arguments only.
- Version grammar, enforced before any value reaches a command: `^v?[0-9]+(\.[0-9]+){0,3}([-+][0-9A-Za-z.-]+)?$`, max 64 characters.
- Compose services the updater may recreate, hardcoded: `backend caddy`. **Never** `postgres` (spec §3, §18.3).
- Fixed asset names from Plan 1: `bndsphere-images-amd64.tar.gz`, `release-manifest.json`, `SHA256SUMS`.
- All durable writes (`state.json`, `deployed.json`, `deploy/versions.env`) are write-temp-then-`rename()` (spec §13.1). `update.log` is append-only and exempt.
- Recovery **probes the world; it never infers from recorded state**, and it **never auto-resumes** (spec §19.2).
- Retention: never `docker image prune`/`system prune`, never bulk-delete. Delete only non-current, non-previous digests in the two BNDSphere repositories (spec §18.3).
- Every Compose invocation passes `--project-directory`, `-f <abs>`, `--env-file <abs>`, `-p bndsphere` explicitly. No reliance on cwd.
- Commit messages follow Conventional Commits.
- Run the self-check suite with:
  `docker build -f infra/Dockerfile.Updater -t bndsphere-updater . && docker run --rm bndsphere-updater /updater/selfcheck.sh`

## File Structure

| File | Responsibility |
|---|---|
| `infra/Dockerfile.Updater` | Image: docker CLI + compose plugin + curl/jq |
| `infra/updater/updater.sh` | Entrypoint: startup validation, poll loop, request dispatch |
| `infra/updater/lib/state.sh` | Atomic writes, stage transitions, logging, lock |
| `infra/updater/lib/validate.sh` | Request validation, version grammar, version compare |
| `infra/updater/lib/artifact.sh` | GHCR digest pull, tarball fallback, checksum + digest verify |
| `infra/updater/lib/deploy.sh` | Migration, Compose recreate, health check, rollback executor |
| `infra/updater/lib/recover.sh` | Per-stage crash probes |
| `infra/updater/lib/retention.sh` | Narrow, digest-exact image deletion |
| `infra/updater/selfcheck.sh` | Assertion suite for the pure logic |

---

### Task 1: Updater image, startup validation, and the self-check harness

Startup validation exists because failing at boot beats failing halfway through a deploy, when the stack is already half-replaced.

**Files:**
- Create: `infra/Dockerfile.Updater`
- Create: `infra/updater/updater.sh`
- Create: `infra/updater/lib/state.sh`
- Create: `infra/updater/selfcheck.sh`

**Interfaces:**
- Consumes: Plan 1's `BACKEND_IMAGE`/`CADDY_IMAGE` names and `deploy/versions.env` path.
- Produces:
  - `atomic_write <dest>` — content on stdin, temp+rename.
  - `log <message>` — appends to `$STATUS_DIR/update.log`, bounded.
  - `validate_startup` — exits non-zero with a diagnostic if configuration is unusable.
  - Env contract: `COMPOSE_PROJECT_DIR` (required, absolute), `COMPOSE_PROJECT_NAME` (default `bndsphere`), `GITHUB_REPO`, `REQUEST_DIR` (default `/srv/request`), `STATUS_DIR` (default `/srv/status`), `POLL_INTERVAL` (default `5`), `HEALTH_TIMEOUT` (default `120`).
  - `assert_eq <expected> <actual> <label>` and `assert_fail <label> <cmd...>` in `selfcheck.sh`.

- [ ] **Step 1: Write the failing self-check**

Create `infra/updater/selfcheck.sh`:

```sh
#!/bin/sh
# Assertion suite for the updater's pure logic. No framework, no fixtures.
# Run: docker run --rm bndsphere-updater /updater/selfcheck.sh
set -u

FAILURES=0
PASSES=0

assert_eq() {
    _expected=$1; _actual=$2; _label=$3
    if [ "$_expected" = "$_actual" ]; then
        PASSES=$((PASSES + 1))
    else
        FAILURES=$((FAILURES + 1))
        printf 'FAIL: %s\n  expected: %s\n  actual:   %s\n' \
            "$_label" "$_expected" "$_actual" >&2
    fi
}

assert_ok() {
    _label=$1; shift
    if "$@" >/dev/null 2>&1; then
        PASSES=$((PASSES + 1))
    else
        FAILURES=$((FAILURES + 1))
        printf 'FAIL: %s (expected success, got exit %d)\n' "$_label" "$?" >&2
    fi
}

assert_fail() {
    _label=$1; shift
    if "$@" >/dev/null 2>&1; then
        FAILURES=$((FAILURES + 1))
        printf 'FAIL: %s (expected failure, got success)\n' "$_label" >&2
    else
        PASSES=$((PASSES + 1))
    fi
}

. /updater/lib/state.sh

# ── atomic_write ─────────────────────────────────────────────────────
TMPD=$(mktemp -d)
printf 'hello' | atomic_write "$TMPD/f"
assert_eq "hello" "$(cat "$TMPD/f")" "atomic_write writes content"

printf 'replaced' | atomic_write "$TMPD/f"
assert_eq "replaced" "$(cat "$TMPD/f")" "atomic_write replaces content"

# The whole point: no partial file is ever observable, and no temp litter
# survives a completed write.
assert_eq "" "$(find "$TMPD" -name '*.tmp.*' 2>/dev/null)" \
    "atomic_write leaves no temp files behind"
rm -rf "$TMPD"

# ── log bounding ─────────────────────────────────────────────────────
STATUS_DIR=$(mktemp -d)
export STATUS_DIR
i=0
while [ "$i" -lt 2500 ]; do log "line $i"; i=$((i + 1)); done
LINES=$(wc -l < "$STATUS_DIR/update.log")
[ "$LINES" -le 2000 ] && PASSES=$((PASSES + 1)) || {
    FAILURES=$((FAILURES + 1))
    printf 'FAIL: log bounded to 2000 lines (got %s)\n' "$LINES" >&2
}
# Bounding must drop the OLDEST lines, not the newest — the tail is the part
# that explains a failure.
assert_eq "line 2499" "$(tail -n 1 "$STATUS_DIR/update.log")" \
    "log bounding keeps the newest lines"
rm -rf "$STATUS_DIR"

# ── startup validation ───────────────────────────────────────────────
GOOD=$(mktemp -d); mkdir -p "$GOOD/secrets"; touch "$GOOD/docker-compose.yml"

assert_fail "startup rejects unset COMPOSE_PROJECT_DIR" \
    env -u COMPOSE_PROJECT_DIR sh -c '. /updater/lib/state.sh; validate_startup'
assert_fail "startup rejects relative COMPOSE_PROJECT_DIR" \
    env COMPOSE_PROJECT_DIR=relative/path sh -c '. /updater/lib/state.sh; validate_startup'
assert_fail "startup rejects missing directory" \
    env COMPOSE_PROJECT_DIR=/nonexistent sh -c '. /updater/lib/state.sh; validate_startup'
assert_fail "startup rejects dir without docker-compose.yml" \
    env COMPOSE_PROJECT_DIR="$(mktemp -d)" sh -c '. /updater/lib/state.sh; validate_startup'
assert_ok "startup accepts a well-formed project dir" \
    env COMPOSE_PROJECT_DIR="$GOOD" sh -c '. /updater/lib/state.sh; validate_startup'
rm -rf "$GOOD"

printf '\n%s passed, %s failed\n' "$PASSES" "$FAILURES"
[ "$FAILURES" -eq 0 ]
```

- [ ] **Step 2: Run it to verify it fails**

Run:
```bash
docker build -f infra/Dockerfile.Updater -t bndsphere-updater .
```
Expected: FAIL — `failed to read dockerfile: open infra/Dockerfile.Updater: no such file or directory`

- [ ] **Step 3: Write the state library**

Create `infra/updater/lib/state.sh`:

```sh
#!/bin/sh
# Durable state for the updater: atomic writes, stage transitions, logging.
#
# Every file this module owns is written temp-then-rename. The updater can be
# killed at any instant, including by the very deploy it is running. A
# half-written versions.env would make the stack unstartable by ANY means,
# including rollback — so partial files must be unobservable, not merely rare.

STATUS_DIR="${STATUS_DIR:-/srv/status}"
REQUEST_DIR="${REQUEST_DIR:-/srv/request}"
LOG_MAX_LINES=2000

atomic_write() {
    _dest=$1
    _tmp="${_dest}.tmp.$$"
    cat > "$_tmp" || { rm -f "$_tmp"; return 1; }
    # rename(2) within one filesystem is atomic: a reader sees the old complete
    # file or the new complete file, never a splice of the two.
    mv -f "$_tmp" "$_dest"
}

log() {
    mkdir -p "$STATUS_DIR"
    printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" \
        >> "$STATUS_DIR/update.log"

    # Bound the log so a crash-loop cannot fill the volume. Keep the NEWEST
    # lines: the tail is what explains the failure.
    _count=$(wc -l < "$STATUS_DIR/update.log")
    if [ "$_count" -gt "$LOG_MAX_LINES" ]; then
        tail -n "$LOG_MAX_LINES" "$STATUS_DIR/update.log" \
            | atomic_write "$STATUS_DIR/update.log"
    fi
}

die() {
    log "FATAL: $1"
    printf 'FATAL: %s\n' "$1" >&2
    exit 1
}

validate_startup() {
    [ -n "${COMPOSE_PROJECT_DIR:-}" ] \
        || die "COMPOSE_PROJECT_DIR is unset. It must be the absolute host path of the deployment."

    case "$COMPOSE_PROJECT_DIR" in
        /*) ;;
        *) die "COMPOSE_PROJECT_DIR must be absolute, got: $COMPOSE_PROJECT_DIR" ;;
    esac

    # The path must resolve identically inside this container and on the host,
    # because Compose bind-mount sources (./secrets/*) are resolved by the HOST
    # daemon. If they disagree, secrets silently resolve to nothing and the
    # stack comes up broken in a way that looks like an application bug.
    [ -d "$COMPOSE_PROJECT_DIR" ] \
        || die "COMPOSE_PROJECT_DIR does not exist at $COMPOSE_PROJECT_DIR. Mount the host deployment directory at its own absolute path."
    [ -f "$COMPOSE_PROJECT_DIR/docker-compose.yml" ] \
        || die "No docker-compose.yml in $COMPOSE_PROJECT_DIR"
    [ -d "$COMPOSE_PROJECT_DIR/secrets" ] \
        || die "No secrets/ in $COMPOSE_PROJECT_DIR"

    mkdir -p "$STATUS_DIR"
    return 0
}
```

- [ ] **Step 4: Write the entrypoint skeleton**

Create `infra/updater/updater.sh`:

```sh
#!/bin/sh
# BNDSphere deployment updater.
#
# SECURITY BOUNDARY (spec §4): this process has /var/run/docker.sock. Docker
# socket access is equivalent to root on the host. If this process is
# compromised, assume the host is compromised. The hardening on this container
# reduces the attack surface; it does NOT remove the daemon privilege boundary.
#
# Consequently this process has no listener, no published port, and accepts no
# commands — only a validated version identifier from $REQUEST_DIR.
set -u

. /updater/lib/state.sh

COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-bndsphere}"
POLL_INTERVAL="${POLL_INTERVAL:-5}"

main() {
    validate_startup
    log "updater started (project=$COMPOSE_PROJECT_NAME dir=$COMPOSE_PROJECT_DIR)"

    while true; do
        # Request handling is added in Task 3.
        sleep "$POLL_INTERVAL"
    done
}

main "$@"
```

- [ ] **Step 5: Write the image**

Create `infra/Dockerfile.Updater`:

```dockerfile
# Updater sidecar. Holds /var/run/docker.sock: compromise here means host
# compromise (spec §4). Kept minimal for that reason, not because minimality
# makes socket access safe.
FROM docker:28-cli

RUN apk add --no-cache \
        bash=~5.2 \
        curl=~8.14 \
        jq=~1.8 \
        coreutils=~9.7 \
    && rm -rf /var/cache/apk/*

COPY infra/updater/ /updater/
RUN chmod +x /updater/updater.sh /updater/selfcheck.sh

# No EXPOSE, no listener, no published port — by design (spec §7).
ENV STATUS_DIR=/srv/status \
    REQUEST_DIR=/srv/request \
    COMPOSE_PROJECT_NAME=bndsphere

ENTRYPOINT ["/updater/updater.sh"]
```

If Hadolint objects to the pinned Alpine versions being unavailable, relax to unpinned `apk add` — `.github/workflows/docker.yml` lints Dockerfiles at `failure-threshold: warning`, so keep it passing rather than fighting it. Add `infra/Dockerfile.Updater` to that workflow's Hadolint steps in Task 9.

- [ ] **Step 6: Run the self-check to verify it passes**

Run:
```bash
docker build -f infra/Dockerfile.Updater -t bndsphere-updater . \
  && docker run --rm bndsphere-updater /updater/selfcheck.sh
```
Expected: PASS — `10 passed, 0 failed`

- [ ] **Step 7: Commit**

```bash
git add infra/Dockerfile.Updater infra/updater/
git commit -m "feat: add updater sidecar image with startup validation"
```

---

### Task 2: Request validation and version comparison

This is the whole trust boundary. Everything the updater does downstream assumes these functions rejected anything dangerous.

**Files:**
- Create: `infra/updater/lib/validate.sh`
- Modify: `infra/updater/selfcheck.sh`

**Interfaces:**
- Produces:
  - `valid_version <string>` — exit 0 if it matches the grammar and is ≤64 chars.
  - `valid_action <string>` — exit 0 for exactly `update` or `rollback`.
  - `valid_uuid <string>` — exit 0 for a well-formed UUID.
  - `version_newer <candidate> <current>` — exit 0 if candidate sorts strictly newer.
  - `read_request <path>` — echoes `id\taction\tversion` on success; non-zero on any validation failure.

- [ ] **Step 1: Write the failing self-check additions**

Append to `infra/updater/selfcheck.sh`, before the final summary lines:

```sh
. /updater/lib/validate.sh

# ── version grammar ──────────────────────────────────────────────────
for v in v1.5.0 1.5.0 v1.5 v1 v1.2.3.4 v1.5.0-rc.1 v1.5.0+build.7; do
    assert_ok "valid_version accepts $v" valid_version "$v"
done

# Injection and traversal attempts. These are the reason this function exists.
assert_fail "rejects command chaining"      valid_version 'v1.5.0; rm -rf /'
assert_fail "rejects command substitution"  valid_version '$(id)'
assert_fail "rejects backticks"             valid_version 'v1.0`id`'
assert_fail "rejects pipe"                  valid_version 'v1.0|sh'
assert_fail "rejects path traversal"        valid_version '../../etc/passwd'
assert_fail "rejects absolute path"         valid_version '/etc/passwd'
assert_fail "rejects a mutable tag"         valid_version 'latest'
assert_fail "rejects empty"                 valid_version ''
assert_fail "rejects whitespace"            valid_version 'v1.5.0 v2.0.0'
assert_fail "rejects a newline injection"   valid_version 'v1.5.0
v2.0.0'
assert_fail "rejects over-length input"     valid_version "v1.$(printf '9%.0s' $(seq 1 80))"
assert_fail "rejects a leading dash"        valid_version '-rf'

# ── action and id ────────────────────────────────────────────────────
assert_ok   "valid_action accepts update"     valid_action update
assert_ok   "valid_action accepts rollback"   valid_action rollback
assert_fail "valid_action rejects arbitrary"  valid_action 'shell'
assert_fail "valid_action rejects empty"      valid_action ''

assert_ok   "valid_uuid accepts a uuid" \
    valid_uuid '3f2504e0-4f89-41d3-9a0c-0305e82c3301'
assert_fail "valid_uuid rejects junk" valid_uuid 'not-a-uuid'

# ── version comparison ───────────────────────────────────────────────
assert_ok   "1.5.0 newer than 1.4.3"      version_newer v1.5.0 v1.4.3
assert_ok   "1.10.0 newer than 1.9.0"     version_newer v1.10.0 v1.9.0
assert_ok   "2.0 newer than 1.99.99"      version_newer v2.0 v1.99.99
assert_ok   "1.5.1 newer than 1.5"        version_newer v1.5.1 v1.5
assert_fail "1.4.3 not newer than 1.5.0"  version_newer v1.4.3 v1.5.0
assert_fail "equal is not newer"          version_newer v1.5.0 v1.5.0
assert_fail "v-prefix is not significant" version_newer v1.5.0 1.5.0
assert_fail "dev is never newer"          version_newer dev v1.0.0

# ── read_request ─────────────────────────────────────────────────────
RD=$(mktemp -d)
cat > "$RD/request.json" <<'JSON'
{"id":"3f2504e0-4f89-41d3-9a0c-0305e82c3301","action":"update",
 "version":"v1.5.0","requested_at":"2026-08-24T10:00:00Z"}
JSON
assert_eq "3f2504e0-4f89-41d3-9a0c-0305e82c3301	update	v1.5.0" \
    "$(read_request "$RD/request.json")" "read_request parses a valid request"

# A malicious version must be rejected at the parse boundary, not downstream.
cat > "$RD/request.json" <<'JSON'
{"id":"3f2504e0-4f89-41d3-9a0c-0305e82c3301","action":"update",
 "version":"v1.5.0; docker run -v /:/host alpine","requested_at":"2026-08-24T10:00:00Z"}
JSON
assert_fail "read_request rejects an injected version" read_request "$RD/request.json"

# Extra fields are ignored, never honoured — the backend cannot smuggle in an
# image name, service list, or URL (spec §8).
cat > "$RD/request.json" <<'JSON'
{"id":"3f2504e0-4f89-41d3-9a0c-0305e82c3301","action":"update","version":"v1.5.0",
 "requested_at":"2026-08-24T10:00:00Z","image":"evil/img","services":["postgres"],
 "command":"rm -rf /"}
JSON
assert_eq "3f2504e0-4f89-41d3-9a0c-0305e82c3301	update	v1.5.0" \
    "$(read_request "$RD/request.json")" "read_request ignores unknown fields"

printf 'not json' > "$RD/request.json"
assert_fail "read_request rejects malformed json" read_request "$RD/request.json"
assert_fail "read_request rejects a missing file" read_request "$RD/nope.json"
rm -rf "$RD"
```

- [ ] **Step 2: Run to verify it fails**

Run:
```bash
docker build -f infra/Dockerfile.Updater -t bndsphere-updater . \
  && docker run --rm bndsphere-updater /updater/selfcheck.sh
```
Expected: FAIL — `/updater/lib/validate.sh: No such file or directory`

- [ ] **Step 3: Write the validation library**

Create `infra/updater/lib/validate.sh`:

```sh
#!/bin/sh
# The trust boundary. Everything downstream assumes these rejected anything
# dangerous, so these functions are deliberately strict and allow-list only.

VERSION_RE='^v?[0-9]+(\.[0-9]+){0,3}([-+][0-9A-Za-z.-]+)?$'
UUID_RE='^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
VERSION_MAX_LEN=64

valid_version() {
    _v=${1:-}
    [ -n "$_v" ] || return 1
    [ "${#_v}" -le "$VERSION_MAX_LEN" ] || return 1
    # printf '%s' (not echo) so a leading '-' is data, never an option.
    printf '%s' "$_v" | grep -Eq "$VERSION_RE" || return 1
    # grep -q matches per line, so an embedded newline could smuggle a second
    # line past the anchors. Reject any multi-line input outright.
    [ "$(printf '%s' "$_v" | wc -l)" -eq 0 ] || return 1
    return 0
}

valid_action() {
    case "${1:-}" in
        update|rollback) return 0 ;;
        *) return 1 ;;
    esac
}

valid_uuid() {
    printf '%s' "${1:-}" | grep -Eq "$UUID_RE"
}

# Strip a leading 'v' and compare dotted numeric segments, longest-wins.
# Pre-release suffixes are ignored for ordering: the updater only needs "is
# this different and newer", and full semver precedence is not worth the shell.
_version_key() {
    printf '%s' "${1#v}" | sed 's/[-+].*$//'
}

version_newer() {
    _cand=$(_version_key "${1:-}")
    _curr=$(_version_key "${2:-}")

    # Anything non-numeric (e.g. the 'dev' default) is never "newer".
    printf '%s' "$_cand" | grep -Eq '^[0-9]+(\.[0-9]+)*$' || return 1
    printf '%s' "$_curr" | grep -Eq '^[0-9]+(\.[0-9]+)*$' || return 0

    _i=1
    while [ "$_i" -le 4 ]; do
        _a=$(printf '%s' "$_cand" | cut -d. -f"$_i"); _a=${_a:-0}
        _b=$(printf '%s' "$_curr" | cut -d. -f"$_i"); _b=${_b:-0}
        [ "$_a" -gt "$_b" ] && return 0
        [ "$_a" -lt "$_b" ] && return 1
        _i=$((_i + 1))
    done
    return 1   # equal is not newer
}

# Echo "id<TAB>action<TAB>version" or fail. Unknown fields are ignored: the
# request schema is closed, so a compromised backend cannot widen it (spec §8).
read_request() {
    _path=${1:-}
    [ -f "$_path" ] || return 1

    _json=$(cat "$_path") || return 1
    printf '%s' "$_json" | jq -e . >/dev/null 2>&1 || return 1

    _id=$(printf '%s' "$_json" | jq -r '.id // empty')
    _action=$(printf '%s' "$_json" | jq -r '.action // empty')
    _version=$(printf '%s' "$_json" | jq -r '.version // empty')

    valid_uuid "$_id" || return 1
    valid_action "$_action" || return 1
    valid_version "$_version" || return 1

    printf '%s\t%s\t%s\n' "$_id" "$_action" "$_version"
}
```

- [ ] **Step 4: Run to verify it passes**

Run:
```bash
docker build -f infra/Dockerfile.Updater -t bndsphere-updater . \
  && docker run --rm bndsphere-updater /updater/selfcheck.sh
```
Expected: PASS — all assertions pass, `0 failed`

- [ ] **Step 5: Commit**

```bash
git add infra/updater/lib/validate.sh infra/updater/selfcheck.sh
git commit -m "feat: add updater request validation and version comparison"
```

---

### Task 3: Durable state machine, lock, and request dispatch

**Files:**
- Modify: `infra/updater/lib/state.sh`
- Modify: `infra/updater/updater.sh`
- Modify: `infra/updater/selfcheck.sh`

**Interfaces:**
- Produces:
  - `state_get <key>` / `state_set <key> <value> [<key> <value> ...]` — read/merge `state.json` atomically.
  - `state_stage <stage>` — transition and log.
  - `state_terminal <stage> <error_code> <error_message>` — land on a terminal stage.
  - `is_terminal <stage>` — exit 0 for `idle|success|rollback_success|failed`.
  - `acquire_lock` / `release_lock` — updater-owned, authoritative over the backend's advisory 409.
  - `deployed_get <key>` — read `deployed.json` (`current_version`, `previous_version`, digests).
  - Stage vocabulary, exactly: `idle checking downloading verifying migrating deploying health_checking success rolling_back rollback_success failed`.

- [ ] **Step 1: Write the failing self-check additions**

Append to `infra/updater/selfcheck.sh` before the summary:

```sh
STATUS_DIR=$(mktemp -d); export STATUS_DIR
. /updater/lib/state.sh

state_init
assert_eq "idle" "$(state_get stage)" "state initialises to idle"

state_set stage checking target_version v1.5.0
assert_eq "checking" "$(state_get stage)" "state_set updates stage"
assert_eq "v1.5.0" "$(state_get target_version)" "state_set updates a second key"

# A merge must not drop existing keys — the panel reads all of them.
state_set stage downloading
assert_eq "v1.5.0" "$(state_get target_version)" "state_set merges, does not replace"

assert_ok   "idle is terminal"             is_terminal idle
assert_ok   "success is terminal"          is_terminal success
assert_ok   "rollback_success is terminal" is_terminal rollback_success
assert_ok   "failed is terminal"           is_terminal failed
assert_fail "migrating is not terminal"    is_terminal migrating
assert_fail "deploying is not terminal"    is_terminal deploying
assert_fail "rolling_back is not terminal" is_terminal rolling_back

state_terminal failed migration_failed "alembic exited 1"
assert_eq "failed" "$(state_get stage)" "state_terminal sets the stage"
assert_eq "migration_failed" "$(state_get error_code)" "state_terminal sets error_code"
assert_eq "alembic exited 1" "$(state_get error_message)" "state_terminal sets message"

# state.json must stay valid JSON after every transition — the backend parses it.
assert_ok "state.json remains valid json" jq -e . "$STATUS_DIR/state.json"

assert_ok   "lock acquires when free" acquire_lock
assert_fail "lock refuses when held"  acquire_lock
release_lock
assert_ok   "lock re-acquires after release" acquire_lock
release_lock

rm -rf "$STATUS_DIR"
```

- [ ] **Step 2: Run to verify it fails**

Run:
```bash
docker build -f infra/Dockerfile.Updater -t bndsphere-updater . \
  && docker run --rm bndsphere-updater /updater/selfcheck.sh
```
Expected: FAIL — `state_init: not found`

- [ ] **Step 3: Add state machine functions**

Append to `infra/updater/lib/state.sh`:

```sh
TERMINAL_STAGES="idle success rollback_success failed"

state_file()    { printf '%s/state.json' "$STATUS_DIR"; }
deployed_file() { printf '%s/deployed.json' "$STATUS_DIR"; }
lock_file()     { printf '%s/updater.lock' "$STATUS_DIR"; }

state_init() {
    mkdir -p "$STATUS_DIR"
    [ -f "$(state_file)" ] && return 0
    printf '%s' '{"stage":"idle","action":null,"request_id":null,
"last_processed_request_id":null,"requested_version":null,"target_version":null,
"previous_version":null,"delivery_path":null,"trigger":null,"started_at":null,
"updated_at":null,"finished_at":null,"error_code":null,"error_message":null,
"observed":null}' | jq -c . | atomic_write "$(state_file)"
}

state_get() {
    [ -f "$(state_file)" ] || { printf ''; return 0; }
    jq -r --arg k "$1" '.[$k] // "" | if type == "object" or type == "array"
        then tojson else tostring end' "$(state_file)"
}

# Merge key/value pairs into state.json. Merge, never replace: the panel reads
# every field, and a transition that silently blanked target_version would make
# a failure unreadable exactly when it matters.
#
# One jq pass per pair, each value passed as --arg. Values are therefore always
# JSON strings and never parsed as jq syntax — the same discipline as the shell
# argument-vector rule: data never becomes code.
state_set() {
    _file=$(state_file)
    _now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    _json=$(cat "$_file")

    while [ "$#" -ge 2 ]; do
        _json=$(printf '%s' "$_json" \
            | jq -c --arg k "$1" --arg v "$2" '.[$k] = $v')
        shift 2
    done

    printf '%s' "$_json" | jq -c --arg t "$_now" '.updated_at = $t' \
        | atomic_write "$_file"
}

state_stage() {
    state_set stage "$1"
    log "stage -> $1"
}

state_terminal() {
    state_set stage "$1" error_code "${2:-}" error_message "${3:-}" \
        finished_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    log "terminal: $1 (${2:-ok}) ${3:-}"
}

is_terminal() {
    for _s in $TERMINAL_STAGES; do
        [ "$1" = "$_s" ] && return 0
    done
    return 1
}

deployed_get() {
    [ -f "$(deployed_file)" ] || { printf ''; return 0; }
    jq -r --arg k "$1" '.[$k] // ""' "$(deployed_file)"
}

deployed_set() {
    _file=$(deployed_file)
    [ -f "$_file" ] || printf '{}' | atomic_write "$_file"
    _json=$(cat "$_file")
    while [ "$#" -ge 2 ]; do
        _json=$(printf '%s' "$_json" | jq -c --arg k "$1" --arg v "$2" '.[$k] = $v')
        shift 2
    done
    printf '%s' "$_json" | atomic_write "$_file"
}

# The lock is updater-owned and authoritative. The backend's 409 pre-check is
# advisory only — it races, this does not.
acquire_lock() {
    mkdir -p "$STATUS_DIR"
    # mkdir is atomic and fails if the directory exists: a lock primitive that
    # needs no flock, which busybox sh lacks.
    mkdir "$(lock_file)" 2>/dev/null || return 1
    printf '%s' "$$" > "$(lock_file)/pid"
    return 0
}

release_lock() {
    rm -rf "$(lock_file)"
}
```

- [ ] **Step 4: Run to verify it passes**

Run:
```bash
docker build -f infra/Dockerfile.Updater -t bndsphere-updater . \
  && docker run --rm bndsphere-updater /updater/selfcheck.sh
```
Expected: PASS — `0 failed`

- [ ] **Step 5: Wire request dispatch into the poll loop**

Replace the `main()` function in `infra/updater/updater.sh`:

```sh
main() {
    validate_startup
    state_init
    log "updater started (project=$COMPOSE_PROJECT_NAME dir=$COMPOSE_PROJECT_DIR)"

    # Recovery runs before the first poll (Task 8 fills this in).
    recover_if_interrupted

    while true; do
        handle_request
        sleep "$POLL_INTERVAL"
    done
}

handle_request() {
    _req="$REQUEST_DIR/request.json"
    [ -f "$_req" ] || return 0

    _parsed=$(read_request "$_req") || {
        # Do not mark anything processed here: an unparseable file has no id to
        # record. Log and ignore, so a malformed write cannot wedge the loop.
        log "rejected malformed request"
        return 0
    }

    _id=$(printf '%s' "$_parsed" | cut -f1)
    _action=$(printf '%s' "$_parsed" | cut -f2)
    _version=$(printf '%s' "$_parsed" | cut -f3)

    [ "$_id" = "$(state_get last_processed_request_id)" ] && return 0

    if ! acquire_lock; then
        log "request $_id rejected: an operation is already in flight"
        return 0
    fi

    # Mark processed BEFORE doing the work. A crash mid-operation then leaves a
    # request that did nothing (visible, re-requestable) rather than one that
    # silently runs twice (spec §19.6).
    state_set last_processed_request_id "$_id" request_id "$_id" \
        action "$_action" requested_version "$_version" \
        started_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        error_code "" error_message ""

    case "$_action" in
        update)   run_update "$_version" ;;
        rollback) run_rollback "$_version" manual ;;
    esac

    release_lock
}
```

Add the new library sources near the top of `updater.sh`, after `state.sh`:

```sh
. /updater/lib/validate.sh
. /updater/lib/artifact.sh
. /updater/lib/deploy.sh
. /updater/lib/recover.sh
. /updater/lib/retention.sh
```

`run_update`, `run_rollback`, and `recover_if_interrupted` arrive in Tasks 4–8. Until then, add temporary stubs at the end of `updater.sh` so the loop is runnable:

```sh
# Replaced in Tasks 4-8.
run_update()             { log "run_update stub: $1"; state_terminal failed not_implemented "stub"; }
run_rollback()           { log "run_rollback stub: $1 ($2)"; state_terminal failed not_implemented "stub"; }
recover_if_interrupted() { :; }
```

- [ ] **Step 6: Commit**

```bash
git add infra/updater/lib/state.sh infra/updater/updater.sh infra/updater/selfcheck.sh
git commit -m "feat: add updater durable state machine, lock, and request dispatch"
```

---

### Task 4: Artifact acquisition — GHCR by digest, verified tarball fallback

**Files:**
- Create: `infra/updater/lib/artifact.sh`
- Modify: `infra/updater/selfcheck.sh`

**Interfaces:**
- Produces:
  - `fetch_manifest <version>` — downloads `release-manifest.json` for a tag to `$WORK_DIR`; echoes its path.
  - `manifest_field <path> <jq-path>` — reads a field.
  - `pull_from_ghcr <manifest>` — pulls both images by `registry_digest`; non-zero on failure.
  - `fetch_and_load_tarball <version> <manifest>` — downloads tarball + `SHA256SUMS`, verifies **before** load, loads, then verifies config digests.
  - `acquire_images <version>` — orchestrates: GHCR first, tarball fallback; sets `delivery_path`.
  - `WORK_DIR` — default `/tmp/updater`, cleared at the start of each acquisition.

- [ ] **Step 1: Write the failing self-check additions**

Append to `infra/updater/selfcheck.sh` before the summary:

```sh
. /updater/lib/artifact.sh

# Checksum verification is the gate that stands between a downloaded blob and
# `docker load`. Test it directly.
WD=$(mktemp -d)
printf 'payload' > "$WD/bndsphere-images-amd64.tar.gz"
( cd "$WD" && sha256sum bndsphere-images-amd64.tar.gz > SHA256SUMS )
assert_ok "verify_checksum accepts a matching file" \
    verify_checksum "$WD" bndsphere-images-amd64.tar.gz

printf 'tampered' > "$WD/bndsphere-images-amd64.tar.gz"
assert_fail "verify_checksum rejects a tampered file" \
    verify_checksum "$WD" bndsphere-images-amd64.tar.gz

rm -f "$WD/SHA256SUMS"
assert_fail "verify_checksum rejects a missing SHA256SUMS" \
    verify_checksum "$WD" bndsphere-images-amd64.tar.gz
rm -rf "$WD"

# Asset URLs are built from the updater's own config plus a validated version.
# The repo must never come from the request.
assert_eq "https://github.com/colinxu2020/BNDSphere/releases/download/v1.5.0/SHA256SUMS" \
    "$(GITHUB_REPO=colinxu2020/BNDSphere asset_url v1.5.0 SHA256SUMS)" \
    "asset_url builds from configured repo"
```

- [ ] **Step 2: Run to verify it fails**

Run:
```bash
docker build -f infra/Dockerfile.Updater -t bndsphere-updater . \
  && docker run --rm bndsphere-updater /updater/selfcheck.sh
```
Expected: FAIL — `/updater/lib/artifact.sh: No such file or directory`

- [ ] **Step 3: Write the artifact library**

Create `infra/updater/lib/artifact.sh`:

```sh
#!/bin/sh
# Artifact acquisition. Two delivery paths, both verified.
#
# Nothing downloaded is ever executed unverified: the GHCR path pulls by
# immutable digest (self-verifying), and the tarball path checks SHA256SUMS
# BEFORE docker load, then re-checks the loaded config digests (spec §6.3).

GITHUB_REPO="${GITHUB_REPO:-colinxu2020/BNDSphere}"
WORK_DIR="${WORK_DIR:-/tmp/updater}"

ASSET_TARBALL="bndsphere-images-amd64.tar.gz"
ASSET_MANIFEST="release-manifest.json"
ASSET_SUMS="SHA256SUMS"

asset_url() {
    printf 'https://github.com/%s/releases/download/%s/%s' \
        "$GITHUB_REPO" "$1" "$2"
}

# Download to a temp name and rename only on success, so an interrupted
# transfer can never be mistaken for a complete file (spec §19.3).
download_asset() {
    _version=$1; _name=$2; _dest="$WORK_DIR/$_name"
    rm -f "$_dest" "$_dest.part"
    curl -fsSL --retry 3 --retry-delay 2 --max-time 1800 \
        -o "$_dest.part" "$(asset_url "$_version" "$_name")" || {
            rm -f "$_dest.part"
            return 1
        }
    mv -f "$_dest.part" "$_dest"
}

verify_checksum() {
    _dir=$1; _name=$2
    [ -f "$_dir/$ASSET_SUMS" ] || return 1
    [ -f "$_dir/$_name" ] || return 1
    # Check only the entry we care about; SHA256SUMS also covers the manifest,
    # which may not have been downloaded into this directory.
    ( cd "$_dir" && grep " [ *]\{0,1\}$_name\$" "$ASSET_SUMS" | sha256sum -c - ) \
        >/dev/null 2>&1
}

fetch_manifest() {
    _version=$1
    mkdir -p "$WORK_DIR"
    download_asset "$_version" "$ASSET_MANIFEST" || return 1
    jq -e . "$WORK_DIR/$ASSET_MANIFEST" >/dev/null 2>&1 || return 1
    printf '%s/%s' "$WORK_DIR" "$ASSET_MANIFEST"
}

manifest_field() {
    jq -r "$2 // empty" "$1"
}

pull_from_ghcr() {
    _manifest=$1
    for _component in backend caddy; do
        _ref=$(manifest_field "$_manifest" ".images.${_component}.ref")
        _digest=$(manifest_field "$_manifest" ".images.${_component}.registry_digest")
        [ -n "$_ref" ] && [ -n "$_digest" ] || return 1

        # Pull by digest, never by tag: a tag is mutable and a mutable
        # reference defeats the point of recording a digest at release time.
        _repo=${_ref%%:*}
        case "$_ref" in *:*/*) _repo=${_ref%:*} ;; *) _repo=${_ref%:*} ;; esac

        log "pulling ${_repo}@${_digest}"
        docker pull "${_repo}@${_digest}" >/dev/null 2>&1 || return 1
        # Re-tag to the human-readable ref so Compose pins stay readable.
        docker tag "${_repo}@${_digest}" "$_ref" || return 1
    done
    return 0
}

fetch_and_load_tarball() {
    _version=$1; _manifest=$2

    download_asset "$_version" "$ASSET_SUMS" || return 1
    download_asset "$_version" "$ASSET_TARBALL" || return 1

    # THE gate. Verify before load, never after.
    verify_checksum "$WORK_DIR" "$ASSET_TARBALL" || {
        rm -f "$WORK_DIR/$ASSET_TARBALL"
        log "checksum mismatch for $ASSET_TARBALL — refusing to load"
        return 2
    }

    docker load -i "$WORK_DIR/$ASSET_TARBALL" >/dev/null 2>&1 || return 3

    # A correct checksum proves the bytes arrived intact; this proves they
    # contain the images the manifest claims.
    for _component in backend caddy; do
        _ref=$(manifest_field "$_manifest" ".images.${_component}.ref")
        _want=$(manifest_field "$_manifest" ".images.${_component}.config_digest")
        _got=$(docker image inspect --format '{{.Id}}' "$_ref" 2>/dev/null)
        [ "$_want" = "$_got" ] || {
            log "config digest mismatch for $_component: want $_want got $_got"
            return 4
        }
    done
    return 0
}

acquire_images() {
    _version=$1
    rm -rf "$WORK_DIR"; mkdir -p "$WORK_DIR"

    state_stage checking
    _manifest=$(fetch_manifest "$_version") || {
        state_terminal failed download_failed "could not fetch $ASSET_MANIFEST for $_version"
        return 1
    }

    state_stage downloading
    if pull_from_ghcr "$_manifest"; then
        state_set delivery_path ghcr
        state_stage verifying
        log "images acquired from GHCR by digest (self-verifying)"
        printf '%s' "$_manifest"
        return 0
    fi

    log "GHCR unavailable, falling back to the release tarball"
    state_set delivery_path tarball

    fetch_and_load_tarball "$_version" "$_manifest"
    case $? in
        0) ;;
        2) state_terminal failed checksum_mismatch "SHA256SUMS did not match $ASSET_TARBALL"; return 1 ;;
        3) state_terminal failed load_failed "docker load failed"; return 1 ;;
        4) state_terminal failed digest_mismatch "loaded image digest did not match the manifest"; return 1 ;;
        *) state_terminal failed download_failed "could not download release assets"; return 1 ;;
    esac

    state_stage verifying
    printf '%s' "$_manifest"
    return 0
}
```

- [ ] **Step 4: Run to verify it passes**

Run:
```bash
docker build -f infra/Dockerfile.Updater -t bndsphere-updater . \
  && docker run --rm bndsphere-updater /updater/selfcheck.sh
```
Expected: PASS — `0 failed`

- [ ] **Step 5: Commit**

```bash
git add infra/updater/lib/artifact.sh infra/updater/selfcheck.sh
git commit -m "feat: add verified artifact acquisition with GHCR and tarball paths"
```

---

### Task 5: Migration, deploy, and health check

**Files:**
- Create: `infra/updater/lib/deploy.sh`
- Modify: `infra/updater/selfcheck.sh`

**Interfaces:**
- Produces:
  - `compose <args...>` — Compose wrapper with all four explicit flags.
  - `write_version_pins <backend_ref> <caddy_ref>` — atomic rewrite of `deploy/versions.env`.
  - `run_migration <backend_ref>` — runs `alembic-migration` with the **new** image; non-zero aborts.
  - `recreate_services <backend_ref> <caddy_ref>` — `up -d backend caddy`.
  - `wait_healthy` — container health **and** application readiness; non-zero on timeout.
  - `run_update <version>` — the full forward flow.

- [ ] **Step 1: Write the failing self-check additions**

Append to `infra/updater/selfcheck.sh` before the summary:

```sh
. /updater/lib/deploy.sh

# versions.env must be rewritten atomically and completely. A partial write
# here makes the stack unstartable by any means, including rollback.
PD=$(mktemp -d); mkdir -p "$PD/deploy" "$PD/secrets"; touch "$PD/docker-compose.yml"
COMPOSE_PROJECT_DIR=$PD; export COMPOSE_PROJECT_DIR

write_version_pins "ghcr.io/o/bndsphere-backend:v1.5.0" "ghcr.io/o/bndsphere-caddy:v1.5.0"
assert_eq "ghcr.io/o/bndsphere-backend:v1.5.0" \
    "$(. "$PD/deploy/versions.env"; printf '%s' "$BACKEND_IMAGE")" \
    "write_version_pins sets BACKEND_IMAGE"
assert_eq "ghcr.io/o/bndsphere-caddy:v1.5.0" \
    "$(. "$PD/deploy/versions.env"; printf '%s' "$CADDY_IMAGE")" \
    "write_version_pins sets CADDY_IMAGE"
assert_eq "" "$(find "$PD/deploy" -name '*.tmp.*')" \
    "write_version_pins leaves no temp file"

# Postgres must never appear in a pin file the updater writes.
assert_fail "version pins never mention postgres" \
    grep -qi postgres "$PD/deploy/versions.env"

# The Compose wrapper must always pass all four explicit flags (spec §13).
COMPOSE_ECHO=1; export COMPOSE_ECHO
_cmd=$(compose up -d backend caddy)
for _flag in --project-directory -f --env-file -p; do
    case "$_cmd" in
        *"$_flag"*) PASSES=$((PASSES + 1)) ;;
        *) FAILURES=$((FAILURES + 1))
           printf 'FAIL: compose wrapper omits %s (got: %s)\n' "$_flag" "$_cmd" >&2 ;;
    esac
done
case "$_cmd" in
    *postgres*) FAILURES=$((FAILURES + 1))
        printf 'FAIL: compose wrapper named postgres\n' >&2 ;;
    *) PASSES=$((PASSES + 1)) ;;
esac
unset COMPOSE_ECHO
rm -rf "$PD"
```

- [ ] **Step 2: Run to verify it fails**

Run:
```bash
docker build -f infra/Dockerfile.Updater -t bndsphere-updater . \
  && docker run --rm bndsphere-updater /updater/selfcheck.sh
```
Expected: FAIL — `/updater/lib/deploy.sh: No such file or directory`

- [ ] **Step 3: Write the deploy library**

Create `infra/updater/lib/deploy.sh`:

```sh
#!/bin/sh
# Migration, recreation, health verification, and the shared rollback executor.

# HARDCODED. The request never supplies these (spec §5, §8). Postgres is
# deliberately absent and must stay absent (spec §3, §18.3).
MANAGED_SERVICES="backend caddy"
MIGRATION_SERVICE="alembic-migration"
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-120}"
HEALTH_INTERVAL=3

versions_env() { printf '%s/deploy/versions.env' "$COMPOSE_PROJECT_DIR"; }

compose() {
    # Every flag explicit. Bind-mount sources in docker-compose.yml are
    # resolved by the HOST daemon, so guessing the project directory silently
    # breaks secrets rather than failing loudly (spec §13).
    if [ "${COMPOSE_ECHO:-0}" = "1" ]; then
        printf 'docker compose --project-directory %s -f %s --env-file %s -p %s %s\n' \
            "$COMPOSE_PROJECT_DIR" "$COMPOSE_PROJECT_DIR/docker-compose.yml" \
            "$(versions_env)" "$COMPOSE_PROJECT_NAME" "$*"
        return 0
    fi
    docker compose \
        --project-directory "$COMPOSE_PROJECT_DIR" \
        -f "$COMPOSE_PROJECT_DIR/docker-compose.yml" \
        --env-file "$(versions_env)" \
        -p "$COMPOSE_PROJECT_NAME" \
        "$@"
}

write_version_pins() {
    mkdir -p "$COMPOSE_PROJECT_DIR/deploy"
    printf '%s\n%s\n' \
        "BACKEND_IMAGE=$1" \
        "CADDY_IMAGE=$2" \
        | atomic_write "$(versions_env)"
    log "pinned BACKEND_IMAGE=$1 CADDY_IMAGE=$2"
}

# Run the NEW image's migrations against the live database while the OLD
# application is still serving. Safe only because of the N-1 compatibility
# policy (spec §11). A non-zero exit MUST abort before anything is replaced.
run_migration() {
    _backend_ref=$1
    log "running migrations with $_backend_ref"
    # BACKEND_IMAGE is overridden in the environment because versions.env still
    # holds the OLD pins at this point — deliberately, so an abort here leaves
    # the durable pins on the running version. Compose ranks shell env above
    # --env-file. Reversed, this would run the OLD migrations and report success.
    BACKEND_IMAGE="$_backend_ref" compose run --rm "$MIGRATION_SERVICE"
}

recreate_services() {
    write_version_pins "$1" "$2"
    # shellcheck disable=SC2086 # MANAGED_SERVICES is a fixed internal literal.
    compose up -d $MANAGED_SERVICES
}

# `docker compose up` exiting 0 means "containers created", not "the
# application works". Committing a version on that basis is how a broken
# deploy gets recorded as a success (spec §10.6).
wait_healthy() {
    _deadline=$(( $(date +%s) + HEALTH_TIMEOUT ))

    while [ "$(date +%s)" -lt "$_deadline" ]; do
        _all_healthy=1
        for _svc in $MANAGED_SERVICES; do
            _cid=$(compose ps -q "$_svc" 2>/dev/null)
            [ -n "$_cid" ] || { _all_healthy=0; break; }
            _status=$(docker inspect --format \
                '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' \
                "$_cid" 2>/dev/null)
            [ "$_status" = "healthy" ] || { _all_healthy=0; break; }
        done

        if [ "$_all_healthy" -eq 1 ] && app_ready; then
            log "health check passed"
            return 0
        fi
        sleep "$HEALTH_INTERVAL"
    done

    log "health check timed out after ${HEALTH_TIMEOUT}s"
    return 1
}

# Application-level readiness, beyond container health. Reached over
# backend-network; the updater still has no listener of its own (spec §10.6).
app_ready() {
    curl -fsS --max-time 5 -o /dev/null http://backend:8000/health || return 1
    curl -fsS --max-time 5 -o /dev/null http://caddy:8080/ || return 1
    return 0
}

run_update() {
    _version=$1

    _current=$(deployed_get current_version)
    if [ "$_version" = "$_current" ]; then
        state_terminal failed already_current "$_version is already deployed"
        return 1
    fi

    _manifest=$(acquire_images "$_version") || return 1

    _backend_ref=$(manifest_field "$_manifest" '.images.backend.ref')
    _caddy_ref=$(manifest_field "$_manifest" '.images.caddy.ref')
    _prev_backend=$(deployed_get current_backend_ref)
    _prev_caddy=$(deployed_get current_caddy_ref)

    state_set target_version "$_version" previous_version "$_current"
    # Recorded before any side effect so the crash probes in Task 7 can ask
    # "are the running containers the ones we intended?" after an interruption.
    deployed_set target_backend_ref "$_backend_ref" target_caddy_ref "$_caddy_ref"

    state_stage migrating
    if ! run_migration "$_backend_ref"; then
        # Aborting here means the old application is still running and serving.
        state_terminal failed migration_failed \
            "alembic exited non-zero; application containers were NOT replaced"
        return 1
    fi

    state_stage deploying
    if ! recreate_services "$_backend_ref" "$_caddy_ref"; then
        state_stage rolling_back
        run_rollback "$_current" automatic
        return 1
    fi

    state_stage health_checking
    if ! wait_healthy; then
        log "new version $_version failed its health check — rolling back"
        run_rollback "$_current" automatic
        return 1
    fi

    deployed_set \
        current_version "$_version" \
        current_backend_ref "$_backend_ref" \
        current_caddy_ref "$_caddy_ref" \
        previous_version "$_current" \
        previous_backend_ref "$_prev_backend" \
        previous_caddy_ref "$_prev_caddy"

    state_terminal success "" "updated to $_version"
    prune_superseded_images
    return 0
}
```

- [ ] **Step 4: Run to verify it passes**

Run:
```bash
docker build -f infra/Dockerfile.Updater -t bndsphere-updater . \
  && docker run --rm bndsphere-updater /updater/selfcheck.sh
```
Expected: PASS — `0 failed`

- [ ] **Step 5: Commit**

```bash
git add infra/updater/lib/deploy.sh infra/updater/selfcheck.sh
git commit -m "feat: add migration-gated deploy with application health verification"
```

---

### Task 6: The shared rollback executor

Automatic and manual rollback must be one code path. A divergence between them only shows up during an incident, when the rarely-exercised branch is the one you need (spec §12.1).

**Files:**
- Modify: `infra/updater/lib/deploy.sh`
- Modify: `infra/updater/selfcheck.sh`

**Interfaces:**
- Produces: `run_rollback <target_version> <trigger>` where `trigger` ∈ `automatic|manual`. Recorded in state; **never branched on**.

- [ ] **Step 1: Write the failing self-check additions**

Append to `infra/updater/selfcheck.sh` before the summary:

```sh
# The unification guarantee, asserted mechanically: `trigger` may be recorded,
# but it must never appear in a conditional. If someone later writes
# `if [ "$trigger" = automatic ]`, this fails.
ROLLBACK_BODY=$(sed -n '/^run_rollback()/,/^}/p' /updater/lib/deploy.sh)
assert_eq "" \
    "$(printf '%s' "$ROLLBACK_BODY" | grep -nE '(if|case|&&|\|\|).*(_trigger|automatic|manual)')" \
    "run_rollback never branches on trigger"

# And it must actually record it.
case "$ROLLBACK_BODY" in
    *"trigger"*) PASSES=$((PASSES + 1)) ;;
    *) FAILURES=$((FAILURES + 1)); printf 'FAIL: run_rollback does not record trigger\n' >&2 ;;
esac

# Rollback must never run migrations, under either trigger (spec §12.2).
assert_eq "" "$(printf '%s' "$ROLLBACK_BODY" | grep -n 'run_migration')" \
    "run_rollback never runs migrations"

# Both call sites must exist and both must reach the same function.
assert_eq "2" \
    "$(grep -c 'run_rollback ' /updater/lib/deploy.sh /updater/updater.sh \
        | awk -F: '{s+=$2} END {print s}')" \
    "rollback has exactly one automatic and one manual call site"
```

- [ ] **Step 2: Run to verify it fails**

Run:
```bash
docker build -f infra/Dockerfile.Updater -t bndsphere-updater . \
  && docker run --rm bndsphere-updater /updater/selfcheck.sh
```
Expected: FAIL — `run_rollback does not record trigger` (the function does not exist yet)

- [ ] **Step 3: Write the executor**

Append to `infra/updater/lib/deploy.sh`:

```sh
# THE rollback path. Both triggers land here; there is no second implementation
# (spec §12.1). `_trigger` is recorded for the panel and the audit log and is
# deliberately never used in a conditional.
run_rollback() {
    _target=$1
    _trigger=$2

    state_set stage rolling_back trigger "$_trigger" target_version "$_target"
    log "rollback to $_target (trigger=$_trigger)"

    _backend_ref=$(deployed_get previous_backend_ref)
    _caddy_ref=$(deployed_get previous_caddy_ref)

    if [ -z "$_backend_ref" ] || [ -z "$_caddy_ref" ]; then
        state_terminal failed rollback_unavailable \
            "no previous image references recorded"
        return 1
    fi

    # Retention guarantees these are present; verify rather than assume,
    # because discovering it during an incident is the worst possible time.
    for _ref in "$_backend_ref" "$_caddy_ref"; do
        docker image inspect "$_ref" >/dev/null 2>&1 || {
            state_terminal failed rollback_unavailable \
                "previous image $_ref is no longer present locally"
            return 1
        }
    done

    # No migration, forward or backward. The schema stays at N while the
    # application returns to N-1; the N-1 policy is what makes that safe.
    if ! recreate_services "$_backend_ref" "$_caddy_ref"; then
        state_terminal failed rollback_failed \
            "could not recreate services on the previous version"
        return 1
    fi

    if ! wait_healthy; then
        state_terminal failed rollback_failed \
            "the previous version did not become healthy — manual intervention required"
        return 1
    fi

    deployed_set \
        current_version "$_target" \
        current_backend_ref "$_backend_ref" \
        current_caddy_ref "$_caddy_ref"

    state_terminal rollback_success "" "rolled back to $_target"
    return 0
}
```

Then delete the `run_rollback` stub from `infra/updater/updater.sh` (added in Task 3), keeping only the `handle_request` call site.

- [ ] **Step 4: Run to verify it passes**

Run:
```bash
docker build -f infra/Dockerfile.Updater -t bndsphere-updater . \
  && docker run --rm bndsphere-updater /updater/selfcheck.sh
```
Expected: PASS — `0 failed`

- [ ] **Step 5: Commit**

```bash
git add infra/updater/lib/deploy.sh infra/updater/selfcheck.sh
git commit -m "feat: add unified rollback executor shared by both triggers"
```

---

### Task 7: Interrupted-operation marking

**Scope reduced.** This task originally specified per-stage crash-recovery probes
that observed real system state (`alembic_version` in the database, running
container image refs, partial download detection), an `observed` JSON block, and a
distinct `unverified_deploy` outcome. That machinery existed to service a
long-running sidecar that could die at any point in a multi-stage operation, and
it is out of proportion to what this deployment actually needs.

What replaces it: on startup, if the recorded stage is not terminal, mark the
operation `failed` with `interrupted`, preserving the stage it stopped at, and
require an explicit new request. No probing, no auto-resume, no auto-rollback.

The safety argument still holds. An interrupted update leaves the durable pins and
`deployed.json` exactly as the last successful write left them, so an operator can
see where it stopped and re-request. The health gate (Task 5) already refuses to
record success unless the running containers match the intended images, so an
interrupted deploy cannot be mistaken for a completed one.

**Files:**
- Create: `infra/updater/lib/recover.sh`
- Modify: `infra/updater/updater.sh` (add the source line; delete the `recover_if_interrupted` stub)
- Modify: `infra/updater/selfcheck.sh`

**Interfaces:**
- Produces: `recover_if_interrupted` — no-op when the stage is terminal; otherwise
  reaps orphaned one-off containers, releases the lock, marks the request
  processed, and lands on `failed` / `interrupted`.

- [ ] **Step 1: Write the failing self-check**

Append to `infra/updater/selfcheck.sh` before the summary block:

```sh
. /updater/lib/recover.sh

STATUS_DIR=$(mktemp -d); export STATUS_DIR
state_init

# A terminal stage means nothing was interrupted — leave it untouched.
state_set stage success
recover_if_interrupted
assert_eq "success" "$(state_get stage)" "recovery leaves a terminal stage alone"

# Every non-terminal stage must land on failed/interrupted, never resume.
for stg in checking downloading verifying migrating deploying rolling_back health_checking; do
    state_init_force
    state_set stage "$stg" request_id "3f2504e0-4f89-41d3-9a0c-0305e82c3301"
    recover_if_interrupted
    assert_eq "failed" "$(state_get stage)" "recovery from $stg lands on failed"
    assert_eq "interrupted" "$(state_get error_code)" "recovery from $stg sets interrupted"
    assert_eq "$stg" "$(state_get interrupted_stage)" "recovery from $stg preserves the stage"
    # A crash must never let the same request run again silently.
    assert_eq "3f2504e0-4f89-41d3-9a0c-0305e82c3301" \
        "$(state_get last_processed_request_id)" \
        "recovery from $stg marks the request processed"
done

# Recovery must never act on the deployment itself.
RECOVER_SRC=$(cat /updater/lib/recover.sh)
assert_eq "" "$(printf '%s' "$RECOVER_SRC" | grep -nE 'run_update|run_rollback|recreate_services|compose up')" \
    "recovery never invokes update, rollback, or a compose recreate"

rm -rf "$STATUS_DIR"
```

- [ ] **Step 2: Run it to verify it fails**

Run:
```bash
docker build -f infra/Dockerfile.Updater -t bndsphere-updater . \
  && docker run --rm bndsphere-updater /updater/selfcheck.sh
```
Expected: FAIL — `/updater/lib/recover.sh: No such file or directory`

- [ ] **Step 3: Write the library**

Create `infra/updater/lib/recover.sh`:

```sh
#!/bin/sh
# Interrupted-operation marking.
#
# State is written around side-effecting commands, so a restart can always land
# in the gap between "command finished" and "state recorded". Rather than trying
# to reconstruct which side of that gap it was on, this stops and says so.
#
# It never resumes and never auto-rolls-back: acting automatically on a
# half-completed deploy at boot is worse than stopping loudly. The durable pins
# and deployed.json are whatever the last successful write left, so an operator
# can see where it stopped, and Task 5's health gate already refuses to record
# success unless the running containers match the intended images.

# Compose `run --rm` helpers can be orphaned if the updater dies mid-run.
reap_orphans() {
    _ids=$(docker ps -aq \
        --filter "label=com.docker.compose.project=$COMPOSE_PROJECT_NAME" \
        --filter "label=com.docker.compose.oneoff=True" \
        --filter "status=exited" 2>/dev/null)
    [ -n "$_ids" ] || return 0
    # shellcheck disable=SC2086 # deliberate word splitting over an id list
    docker rm $_ids >/dev/null 2>&1 || true
    log "reaped orphaned one-off containers"
}

recover_if_interrupted() {
    _stage=$(state_get stage)
    [ -n "$_stage" ] || return 0
    is_terminal "$_stage" && return 0

    log "updater restarted while in stage '$_stage' — marking interrupted, not resuming"

    reap_orphans
    release_lock

    # Mark the request processed so a crash can never cause a silent re-run.
    state_set interrupted_stage "$_stage" \
        last_processed_request_id "$(state_get request_id)" || true
    state_terminal failed interrupted \
        "updater restarted during '$_stage'; no work was resumed"
}
```

- [ ] **Step 4: Wire it in**

Add the source line to `infra/updater/updater.sh` alongside the existing ones:

```sh
. /updater/lib/recover.sh
```

and delete the temporary `recover_if_interrupted() { :; }` stub. The stub is
defined after the sourcing block, so leaving it would shadow the real function.

- [ ] **Step 5: Run to verify it passes**

Run:
```bash
docker build -f infra/Dockerfile.Updater -t bndsphere-updater . \
  && docker run --rm bndsphere-updater /updater/selfcheck.sh
```
Expected: PASS — `0 failed`

- [ ] **Step 6: Commit**

```bash
git add infra/updater/lib/recover.sh infra/updater/updater.sh infra/updater/selfcheck.sh
git commit -m "feat: mark interrupted updater operations instead of resuming them"
```


### Task 8: Narrow image retention

**Files:**
- Create: `infra/updater/lib/retention.sh`
- Modify: `infra/updater/selfcheck.sh`

**Interfaces:**
- Produces: `prune_superseded_images` — deletes only non-current, non-previous digests in the two BNDSphere repositories.

- [ ] **Step 1: Write the failing self-check additions**

Append to `infra/updater/selfcheck.sh` before the summary:

```sh
. /updater/lib/retention.sh

# These prohibitions are the whole point of the module: the host may run other
# workloads, and they are not ours to garbage-collect (spec §18.3).
RETENTION_SRC=$(cat /updater/lib/retention.sh)
for forbidden in 'image prune' 'system prune' 'container prune' 'volume prune'; do
    assert_eq "" "$(printf '%s' "$RETENTION_SRC" | grep -n "$forbidden")" \
        "retention never calls docker $forbidden"
done
assert_eq "" "$(printf '%s' "$RETENTION_SRC" | grep -n 'rmi -f\|--force')" \
    "retention never force-deletes"

# Only the two BNDSphere repositories may ever be named.
assert_ok "retention scopes to bndsphere-backend" \
    grep -q 'bndsphere-backend' /updater/lib/retention.sh
assert_ok "retention scopes to bndsphere-caddy" \
    grep -q 'bndsphere-caddy' /updater/lib/retention.sh
assert_fail "retention never names postgres" \
    grep -qi 'postgres' /updater/lib/retention.sh

# Keep-set logic: current and previous survive, anything else is a candidate.
assert_ok   "keeps the current digest"  is_protected sha256:aaa "sha256:aaa" "sha256:bbb"
assert_ok   "keeps the previous digest" is_protected sha256:bbb "sha256:aaa" "sha256:bbb"
assert_fail "does not keep a third"     is_protected sha256:ccc "sha256:aaa" "sha256:bbb"
# An empty keep-set must protect everything rather than delete everything —
# failing open is the only safe direction here.
assert_ok   "empty keep-set protects"   is_protected sha256:ccc "" ""
```

- [ ] **Step 2: Run to verify it fails**

Run:
```bash
docker build -f infra/Dockerfile.Updater -t bndsphere-updater . \
  && docker run --rm bndsphere-updater /updater/selfcheck.sh
```
Expected: FAIL — `/updater/lib/retention.sh: No such file or directory`

- [ ] **Step 3: Write the retention library**

Create `infra/updater/lib/retention.sh`:

```sh
#!/bin/sh
# Image retention — deliberately the narrowest thing that works.
#
# Current AND previous must always survive: rollback depends on the previous
# images being present locally, so this is a correctness requirement, not an
# optimisation.
#
# There is no bulk deletion here and there must never be. The host may run
# unrelated workloads. Accumulating a few hundred MB of superseded images is a
# far cheaper mistake than deleting an image someone needed (spec §18.3).

RETAINED_REPOS="bndsphere-backend bndsphere-caddy"

is_protected() {
    _digest=$1; _current=$2; _previous=$3
    # Fail open: with nothing recorded to protect, protect everything.
    [ -z "$_current" ] && [ -z "$_previous" ] && return 0
    [ "$_digest" = "$_current" ] && return 0
    [ "$_digest" = "$_previous" ] && return 0
    return 1
}

prune_superseded_images() {
    for _repo_suffix in $RETAINED_REPOS; do
        case "$_repo_suffix" in
            backend) _cur=$(deployed_get current_backend_ref)
                     _prev=$(deployed_get previous_backend_ref) ;;
            *)       _cur=$(deployed_get current_caddy_ref)
                     _prev=$(deployed_get previous_caddy_ref) ;;
        esac
        _cur_id=$(docker image inspect --format '{{.Id}}' "$_cur" 2>/dev/null)
        _prev_id=$(docker image inspect --format '{{.Id}}' "$_prev" 2>/dev/null)

        # Enumerate ONLY this repository. Never `docker images` unfiltered.
        docker images --no-trunc --format '{{.Repository}} {{.ID}}' \
            | grep "$_repo_suffix" \
            | while read -r _repo _id; do
                if is_protected "$_id" "$_cur_id" "$_prev_id"; then
                    continue
                fi
                # No --force: an in-use image is skipped, never yanked out from
                # under a running container.
                if docker rmi "$_id" >/dev/null 2>&1; then
                    log "removed superseded image $_repo $_id"
                else
                    log "skipped in-use image $_repo $_id"
                fi
            done
    done
}
```

- [ ] **Step 4: Run to verify it passes**

Run:
```bash
docker build -f infra/Dockerfile.Updater -t bndsphere-updater . \
  && docker run --rm bndsphere-updater /updater/selfcheck.sh
```
Expected: PASS — `0 failed`

- [ ] **Step 5: Commit**

```bash
git add infra/updater/lib/retention.sh infra/updater/selfcheck.sh
git commit -m "feat: add narrow digest-exact image retention to the updater"
```

---

### Task 9: Wire the sidecar into Compose

**Files:**
- Modify: `docker-compose.yml`
- Modify: `docker-compose.build.yml`
- Modify: `.github/workflows/docker.yml`

**Interfaces:**
- Consumes: everything above.
- Produces: volumes `updater_request` (backend `rw`, updater `ro`) and `updater_status` (backend `ro`, updater `rw`) — Plan 3's backend mounts these with exactly these permissions.

- [ ] **Step 1: Add the updater service**

Add to `docker-compose.yml` under `services:`:

```yaml
  updater:
    image: bndsphere-updater
    restart: unless-stopped

    # ── SECURITY BOUNDARY (spec §4) ──────────────────────────────────
    # This container has the Docker socket. Docker socket access is
    # equivalent to root on the host: this process can start a privileged
    # container that bind-mounts /.
    #
    #   backend compromised  != host compromised
    #   updater compromised  == assume host compromised
    #
    # The hardening below reduces the attack surface. It does NOT make
    # socket access safe and must not be read as doing so.
    # ─────────────────────────────────────────────────────────────────
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      # The deployment directory at its OWN absolute path, so Compose
      # bind-mount sources resolve identically here and on the host daemon
      # (spec §13). ${COMPOSE_PROJECT_DIR} is written into .env by
      # deploy/bootstrap.sh (Plan 1 Task 2); the updater reads it and fails
      # closed if it is wrong, but never resolves or searches for it itself.
      - ${COMPOSE_PROJECT_DIR}:${COMPOSE_PROJECT_DIR}:ro
      # deploy/ is writable so the updater can persist version pins while the
      # rest of the project stays read-only. The nested mount wins for its path.
      - ${COMPOSE_PROJECT_DIR}/deploy:${COMPOSE_PROJECT_DIR}/deploy:rw
      # Split by trust direction (spec §7): the backend can ask for work but
      # cannot forge the record of what happened.
      - updater_request:/srv/request:ro
      - updater_status:/srv/status:rw

    environment:
      - COMPOSE_PROJECT_DIR=${COMPOSE_PROJECT_DIR}
      - COMPOSE_PROJECT_NAME=bndsphere
      - GITHUB_REPO=${GITHUB_REPO:-colinxu2020/BNDSphere}
      - POLL_INTERVAL=${UPDATER_POLL_INTERVAL:-5}
      - HEALTH_TIMEOUT=${UPDATER_HEALTH_TIMEOUT:-120}

    # Outbound only — reaches backend/caddy for readiness probes and
    # ghcr.io/github.com for artifacts. No ports, no listener (spec §7, §10.6).
    networks:
      - backend-network

    security_opt:
      - no-new-privileges:true
    tmpfs:
      - /tmp:nosuid,nodev
```

Add to the `volumes:` block at the bottom:

```yaml
  updater_request:
  updater_status:
```

Note this service intentionally omits `read_only: true`: it writes downloads to `/tmp` and state to `/srv/status`. `cap_drop: ALL` is also omitted because the Docker CLI needs to talk to the socket — and neither would change the boundary in §4 regardless.

- [ ] **Step 2: Add the build stanza**

Add to `docker-compose.build.yml` under `services:`:

```yaml
  updater:
    image: bndsphere-updater
    build:
      context: .
      dockerfile: infra/Dockerfile.Updater
      network: host
```

- [ ] **Step 3: Add the Dockerfile to CI linting**

In `.github/workflows/docker.yml`, after the "Lint Caddy Dockerfile with Hadolint" step, add:

```yaml
      - name: Lint Updater Dockerfile with Hadolint
        uses: hadolint/hadolint-action@v3.3.0
        with:
          dockerfile: infra/Dockerfile.Updater
          failure-threshold: warning
```

In the same file, the "Prepare dummy local files for Compose parsing" step must also provide `COMPOSE_PROJECT_DIR`, or `docker compose config` will fail on the empty bind-mount source. Append to that step's script:

```bash
          mkdir -p deploy
          echo "COMPOSE_PROJECT_DIR=$GITHUB_WORKSPACE" >> .env
```

- [ ] **Step 4: Verify Compose parses and the sidecar boots**

```bash
./deploy/bootstrap.sh   # sets COMPOSE_PROJECT_DIR and seeds versions.env

docker compose -f docker-compose.yml -f docker-compose.build.yml -f docker-compose.dev.yml config --quiet
```
Expected: no output, exit 0

Confirm the trust split is real — the backend must not be able to write status:
```bash
docker compose -f docker-compose.yml -f docker-compose.build.yml build updater
docker compose -f docker-compose.yml -f docker-compose.build.yml up -d updater
docker compose logs updater
```
Expected: `updater started (project=bndsphere dir=...)` and no `FATAL`.

```bash
docker compose exec -T updater sh -c 'touch /srv/request/x 2>&1 || echo "request is read-only (correct)"'
```
Expected: `request is read-only (correct)`

- [ ] **Step 5: End-to-end update against a real release**

Requires Plan 1 to have published at least two versions. With the stack running:

```bash
docker compose exec -T updater sh -c 'cat > /tmp/req.json' <<'JSON'
{"id":"3f2504e0-4f89-41d3-9a0c-0305e82c3301","action":"update",
 "version":"<a real published tag>","requested_at":"2026-08-24T10:00:00Z"}
JSON
# The backend writes this path in Plan 3; here we stage it by hand via a
# throwaway writer, since the updater's own mount is read-only.
docker run --rm -v bndsphere_updater_request:/r -v /tmp:/host alpine \
  sh -c 'cp /host/req.json /r/request.json'

docker compose logs -f updater
```

Expected stage sequence in the log: `checking → downloading → verifying → migrating → deploying → health_checking → terminal: success`.

Then verify the durable record and that rollback material was retained:
```bash
docker run --rm -v bndsphere_updater_status:/s alpine cat /s/deployed.json
docker compose exec -T backend printenv APP_VERSION
```
Expected: `deployed.json` shows the new `current_version` and the prior `previous_version`; `APP_VERSION` matches the new version — the running container agreeing with the record is the real proof.

- [ ] **Step 6: Commit**

```bash
git add docker-compose.yml docker-compose.build.yml .github/workflows/docker.yml
git commit -m "feat: wire the updater sidecar into the compose stack"
```

---

## Plan 2 Completion Criteria

- [ ] `selfcheck.sh` passes with 0 failures.
- [ ] Every injection string in Task 2 is rejected by `valid_version`.
- [ ] The request schema is closed — unknown fields are ignored, never honoured.
- [ ] Compose invocations always carry `--project-directory`, `-f`, `--env-file`, `-p`, and never name `postgres`.
- [ ] Migration runs with the **new** image and a failure aborts before containers are replaced.
- [ ] `docker compose up` exiting 0 is never treated as success; `wait_healthy` gates every commit of `current_version`.
- [ ] Automatic and manual rollback reach one executor; `trigger` is recorded and never branched on; neither runs migrations.
- [ ] Every non-terminal stage recovers to `failed`/`interrupted` with an `observed` block, and never auto-resumes.
- [ ] A crash after deploy but before verification reports `unverified_deploy`, distinct from `interrupted`.
- [ ] Retention never bulk-prunes and always preserves current + previous.
- [ ] `updater_request` is read-only to the updater; `updater_status` is read-only to the backend.
- [ ] An end-to-end update against a real release reaches `success`, and the backend's `APP_VERSION` matches `deployed.json`.

**Next:** `docs/superpowers/plans/2026-08-24-dev-panel.md` (Plan 3).
