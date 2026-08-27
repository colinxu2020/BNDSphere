#!/bin/sh
# Assertion suite for the deploy script's pure logic. No framework, no
# fixtures. Everything that needs a Docker daemon is stubbed; what a stub
# cannot observe is called out where it matters.
#
# Run: SCRIPT_DIR=infra/deploy sh infra/deploy/selfcheck.sh
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

# Overrides of real library functions always happen inside a `(...)` subshell
# function body. `unset -f` cannot restore a shadowed definition -- sh has no
# notion of one -- so a bare redefinition would delete the real function for
# every test after it. Inside a subshell the override vanishes on return while
# real file writes persist.

SCRIPT_DIR="${SCRIPT_DIR:-$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)}"
export SCRIPT_DIR

. "$SCRIPT_DIR"/lib/common.sh

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

# ── version grammar: the trust boundary ──────────────────────────────
for v in v1.5.0 1.5.0 v1.5 v1 v1.2.3.4 v1.5.0-rc.1; do
    assert_ok "valid_version accepts $v" valid_version "$v"
done

# '+' build metadata: the version becomes a Docker tag verbatim, and Docker's
# reference grammar has no '+', so such a release can never be built.
assert_fail "rejects '+' build metadata" valid_version 'v1.5.0+build.7'

# Injection and traversal. These are the reason this function exists: the
# version reaches release URLs and Docker tags, and arrives from
# workflow_dispatch.
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

# ── startup validation ───────────────────────────────────────────────
GOOD=$(mktemp -d); mkdir -p "$GOOD/secrets"
touch "$GOOD/docker-compose.yml" "$GOOD/.env"

assert_fail "startup rejects unset COMPOSE_PROJECT_DIR" \
    env -u COMPOSE_PROJECT_DIR sh -c '. $SCRIPT_DIR/lib/common.sh; validate_startup'
assert_fail "startup rejects relative COMPOSE_PROJECT_DIR" \
    env COMPOSE_PROJECT_DIR=relative/path sh -c '. $SCRIPT_DIR/lib/common.sh; validate_startup'
assert_fail "startup rejects missing directory" \
    env COMPOSE_PROJECT_DIR=/nonexistent sh -c '. $SCRIPT_DIR/lib/common.sh; validate_startup'
assert_fail "startup rejects dir without docker-compose.yml" \
    env COMPOSE_PROJECT_DIR="$(mktemp -d)" sh -c '. $SCRIPT_DIR/lib/common.sh; validate_startup'
# The compose wrapper passes .env explicitly; without it every recreate would
# interpolate CORS_ORIGIN/OSS_* to empty strings and remap CADDY_PORT to :80.
NOENV=$(mktemp -d); mkdir -p "$NOENV/secrets"; touch "$NOENV/docker-compose.yml"
assert_fail "startup rejects dir without .env" \
    env COMPOSE_PROJECT_DIR="$NOENV" sh -c '. $SCRIPT_DIR/lib/common.sh; validate_startup'
rm -rf "$NOENV"
assert_ok "startup accepts a well-formed project dir" \
    env COMPOSE_PROJECT_DIR="$GOOD" sh -c '. $SCRIPT_DIR/lib/common.sh; validate_startup'
rm -rf "$GOOD"

. "$SCRIPT_DIR"/lib/artifact.sh
. "$SCRIPT_DIR"/lib/stack.sh

# A project dir every later section reuses.
PD=$(mktemp -d); mkdir -p "$PD/deploy" "$PD/secrets"
touch "$PD/docker-compose.yml" "$PD/.env"
COMPOSE_PROJECT_DIR=$PD; export COMPOSE_PROJECT_DIR
COMPOSE_PROJECT_NAME=bndsphere; export COMPOSE_PROJECT_NAME

# ── the version record ───────────────────────────────────────────────
write_pins v1.5.0 "bndsphere-backend:v1.5.0" "bndsphere-caddy:v1.5.0"
assert_eq "v1.5.0" "$(pin_get "$(versions_env)" APP_VERSION)" \
    "write_pins records APP_VERSION"
assert_eq "bndsphere-backend:v1.5.0" "$(pin_get "$(versions_env)" BACKEND_IMAGE)" \
    "write_pins records BACKEND_IMAGE"
assert_eq "bndsphere-caddy:v1.5.0" "$(pin_get "$(versions_env)" CADDY_IMAGE)" \
    "write_pins records CADDY_IMAGE"
# Compose sources this file, so it must be shell-loadable, not merely
# greppable.
assert_eq "bndsphere-backend:v1.5.0" \
    "$(. "$(versions_env)"; printf '%s' "$BACKEND_IMAGE")" \
    "versions.env is loadable by Compose"
assert_eq "" "$(find "$PD/deploy" -name '*.tmp.*')" "write_pins leaves no temp file"
# Postgres must never appear in a pin file this script writes.
assert_fail "version pins never mention postgres" \
    grep -qi postgres "$(versions_env)"
assert_eq "" "$(pin_get /nonexistent/versions.env APP_VERSION)" \
    "pin_get is empty for a missing file"
assert_eq "" "$(pin_get "$(versions_env)" NO_SUCH_KEY)" \
    "pin_get is empty for an absent key"

# ── the compose wrapper ──────────────────────────────────────────────
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
# --env-file REPLACES the default .env rather than adding to it, so the
# wrapper must pass BOTH -- the deployment's .env first, the pins second so
# they win on BACKEND_IMAGE/CADDY_IMAGE.
case "$_cmd" in
    *"--env-file $PD/.env --env-file $PD/deploy/versions.env"*)
        PASSES=$((PASSES + 1)) ;;
    *) FAILURES=$((FAILURES + 1))
       printf 'FAIL: compose wrapper must pass .env before the pins (got: %s)\n' "$_cmd" >&2 ;;
esac

# ── what may be recreated ────────────────────────────────────────────
# Postgres is never named, recreated or restarted by a deploy.
case "$MANAGED_SERVICES" in
    *postgres*) FAILURES=$((FAILURES + 1))
        printf 'FAIL: MANAGED_SERVICES includes postgres\n' >&2 ;;
    *) PASSES=$((PASSES + 1)) ;;
esac
RS_OUT=$(recreate_services v1.6.0 "bndsphere-backend:v1.6.0" "bndsphere-caddy:v1.6.0")
case "$RS_OUT" in
    *postgres*) FAILURES=$((FAILURES + 1))
        printf 'FAIL: recreate_services named postgres (got: %s)\n' "$RS_OUT" >&2 ;;
    *) PASSES=$((PASSES + 1)) ;;
esac
case "$RS_OUT" in
    *"up -d --no-deps backend caddy"*) PASSES=$((PASSES + 1)) ;;
    *) FAILURES=$((FAILURES + 1))
       printf 'FAIL: recreate_services did not target backend caddy (got: %s)\n' "$RS_OUT" >&2 ;;
esac
# Without --no-deps, `up` pulls postgres in via depends_on and re-runs
# alembic-migration a second time through backend's
# service_completed_successfully dependency. This can only inspect the argv;
# whether Compose's fan-out actually happens needs a live daemon.
case "$RS_OUT" in
    *"--no-deps"*) PASSES=$((PASSES + 1)) ;;
    *) FAILURES=$((FAILURES + 1))
       printf 'FAIL: recreate_services omits --no-deps (got: %s)\n' "$RS_OUT" >&2 ;;
esac
assert_eq "v1.6.0" "$(pin_get "$(versions_env)" APP_VERSION)" \
    "recreate_services pinned the version it was given"
unset COMPOSE_ECHO

# A failed pin write must never be followed by `compose up`: with the OLD pins
# still on disk, `up` would recreate nothing, exit 0, and the OLD (genuinely
# healthy) containers would sail through the health gate -- reporting success
# while still running the old version.
_write_pins_failing_write() (
    atomic_write() { cat >/dev/null; return 1; }
    write_pins v1 "backend:v1" "caddy:v1"
)
assert_fail "write_pins propagates a refused write" _write_pins_failing_write

_up_called=$(mktemp)
_recreate_failing_write() (
    atomic_write() { cat >/dev/null; return 1; }
    compose() { case "$1" in up) printf 'called' > "$_up_called" ;; esac; }
    recreate_services v1 "backend:v1" "caddy:v1"
)
assert_fail "recreate_services propagates a refused pin write" _recreate_failing_write
assert_eq "" "$(cat "$_up_called")" \
    "recreate_services never calls compose up when the pin write failed"
rm -f "$_up_called"

# ── the health gate ──────────────────────────────────────────────────
# Container health alone cannot distinguish the new version from the old: if
# nothing was actually recreated, the old containers are healthy too.
HEALTH_TIMEOUT=1
HEALTH_INTERVAL=0
_healthy_running() (
    _tag=$1
    # `compose ps -q <svc>` returns the service name as the container id, so
    # the docker stub can answer per-service and each service is compared
    # against its OWN expected ref.
    compose() { case "$1" in ps) printf '%s\n' "$3" ;; port) printf '0.0.0.0:8080\n' ;; esac; }
    docker() { case "$3" in *Health*) printf 'healthy\n' ;; *) printf '%s:%s\n' "$4" "$_tag" ;; esac; }
    app_ready() { return 0; }
    wait_healthy "backend:v2" "caddy:v2"
)
assert_ok   "health passes when the running image is the intended one" \
    _healthy_running v2
assert_fail "health fails when a healthy container runs the OLD image" \
    _healthy_running v1
# An absent expected ref must never compare "" = "" and pass vacuously.
_healthy_vacuous() (
    compose() { case "$1" in ps) printf 'cid\n' ;; port) printf '0.0.0.0:8080\n' ;; esac; }
    compose() { case "$1" in ps) printf '%s\n' "$3" ;; port) printf '0.0.0.0:8080\n' ;; esac; }
    docker() { case "$3" in *Health*) printf 'healthy\n' ;; *) printf '\n' ;; esac; }
    app_ready() { return 0; }
    wait_healthy "" ""
)
assert_fail "health never passes vacuously on empty refs" _healthy_vacuous
# Container health is necessary but not sufficient: the published port must
# actually serve.
_healthy_app_down() (
    compose() { case "$1" in ps) printf 'cid\n' ;; port) printf '0.0.0.0:8080\n' ;; esac; }
    compose() { case "$1" in ps) printf '%s\n' "$3" ;; port) printf '0.0.0.0:8080\n' ;; esac; }
    docker() { case "$3" in *Health*) printf 'healthy\n' ;; *) printf '%s:v2\n' "$4" ;; esac; }
    app_ready() { return 1; }
    wait_healthy "backend:v2" "caddy:v2"
)
assert_fail "health fails when the app does not answer on the published port" \
    _healthy_app_down
# Restore the real defaults rather than unsetting them: `set -u` plus a
# later real wait_healthy call would abort the suite.
HEALTH_TIMEOUT=120
HEALTH_INTERVAL=3

# ── artifact acquisition ─────────────────────────────────────────────
# Verification IS the digest: the daemon rejects content that does not match
# the digest asked for. So the only thing this layer must get right is
# refusing to pull anything that is NOT digest-pinned -- a tag-only ref would
# be mutable and unverified, which is the whole property being relied on.
WORK_DIR=$(mktemp -d); export WORK_DIR
_pulled=$(mktemp)

_acquire_with_ref() (
    _ref=$1
    fetch_manifest() { printf '/dev/null'; }
    manifest_field() { printf '%s' "$_ref"; }
    # docker pull <ref>
    docker() { printf '%s\n' "$2" >> "$_pulled"; return 0; }
    acquire_images v1.5.0
)
assert_ok "acquire_images accepts a digest-pinned ref" \
    _acquire_with_ref 'ghcr.io/o/bndsphere-backend@sha256:aaa'
assert_fail "acquire_images refuses a tag-only ref" \
    _acquire_with_ref 'ghcr.io/o/bndsphere-backend:v1.5.0'
assert_fail "acquire_images refuses a mutable tag" \
    _acquire_with_ref 'ghcr.io/o/bndsphere-backend:latest'
assert_fail "acquire_images refuses an empty ref" _acquire_with_ref ''

: > "$_pulled"
_acquire_with_ref 'ghcr.io/o/bndsphere-backend@sha256:aaa' >/dev/null 2>&1
assert_eq "ghcr.io/o/bndsphere-backend@sha256:aaa
ghcr.io/o/bndsphere-backend@sha256:aaa" "$(cat "$_pulled")" \
    "acquire_images pulls both components by digest"

# A pull that fails must fail the deploy, not proceed to recreate containers
# on an image that is not there.
_acquire_pull_fails() (
    fetch_manifest() { printf '/dev/null'; }
    manifest_field() { printf 'ghcr.io/o/i@sha256:aaa'; }
    docker() { return 1; }
    acquire_images v1.5.0
)
assert_fail "acquire_images fails when the pull fails" _acquire_pull_fails

# An unparseable manifest is a failure, not an empty ref set.
printf 'not json' > "$WORK_DIR/$ASSET_MANIFEST"
_bad_manifest() (
    download_asset() { return 0; }
    fetch_manifest v1.5.0
)
assert_fail "fetch_manifest rejects a manifest that is not JSON" _bad_manifest
rm -f "$_pulled"
rm -rf "$WORK_DIR"
unset WORK_DIR

# ── image retention ──────────────────────────────────────────────────
# Only the current and previous versions are reachable; everything else is
# unreachable disk.
_rm_log=$(mktemp)
_prune() (
    docker() {
        case "$1" in
            image)
                case "$2" in
                    inspect) printf 'sha256:%s\n' "${5##*:}" ;;
                    ls)      printf 'sha256:keep1\nsha256:keep2\nsha256:old1\nsha256:old2\n' ;;
                    rm)      printf '%s\n' "$3" >> "$_rm_log" ;;
                esac
                ;;
        esac
    }
    prune_superseded "repo/a@sha256:keep1" "repo/b@sha256:keep2"
)
_prune >/dev/null 2>&1
assert_eq "sha256:old1
sha256:old2
sha256:old1
sha256:old2" "$(cat "$_rm_log")" \
    "prune removes only images outside the keep set (once per deployed repo)"
# `docker image rm` is called WITHOUT -f so the daemon refuses to remove an
# image a container still uses.
assert_fail "prune never force-removes" grep -q '\-f' "$_rm_log"
: > "$_rm_log"
_prune_nothing_kept() (
    docker() { case "$2" in inspect) return 1 ;; rm) printf 'rm\n' >> "$_rm_log" ;; esac; }
    prune_superseded "repo/a@sha256:keep1"
)
_prune_nothing_kept >/dev/null 2>&1
assert_eq "" "$(cat "$_rm_log")" \
    "prune removes nothing when it cannot resolve what to keep"
rm -f "$_rm_log"

# ── run_update ordering ──────────────────────────────────────────────
# The invariant: nothing on the host is replaced before the migration
# succeeds, and the rollback target is only rotated once there is something to
# roll back from.
write_pins v1.0.0 "backend:v1.0.0" "caddy:v1.0.0"
rm -f "$(versions_env_prev)" "$(compose_file_prev)"
# The release's compose file, as fetch_compose would stage it, and the one
# already installed on the host.
_staged_src=$(mktemp)
printf 'services: {backend: {image: NEW}}\n' > "$_staged_src"
printf 'services: {backend: {image: OLD}}\n' | atomic_write "$(compose_file)"

_trace=$(mktemp)
_update_migration_fails() (
    acquire_images() { printf '/dev/null'; }
    fetch_compose() { printf '%s' "$_staged_src"; }
    prune_superseded() { :; }
    manifest_field() { case "$2" in *backend*) printf 'backend:v2' ;; *) printf 'caddy:v2' ;; esac; }
    run_migration() { printf 'migrated with %s\n' "$COMPOSE_FILE" >> "$_trace"; return 1; }
    recreate_services() { printf 'recreated\n' >> "$_trace"; return 0; }
    wait_healthy() { return 0; }
    run_rollback() { printf 'rolled_back\n' >> "$_trace"; return 0; }
    run_update v2.0.0
)
assert_fail "run_update fails when the migration fails" _update_migration_fails
assert_eq "migrated with $_staged_src" "$(cat "$_trace")" \
    "the migration runs against the release's own compose file, and a failed one replaces nothing"
assert_eq "services: {backend: {image: OLD}}" "$(cat "$(compose_file)")" \
    "a failed migration leaves the installed compose file untouched"
assert_fail "a failed migration does not rotate the compose file" \
    test -f "$(compose_file_prev)"
assert_eq "v1.0.0" "$(pin_get "$(versions_env)" APP_VERSION)" \
    "a failed migration leaves the durable pins on the running version"
assert_fail "a failed migration does not rotate the rollback target" \
    test -f "$(versions_env_prev)"

: > "$_trace"
_update_recreate_fails() (
    acquire_images() { printf '/dev/null'; }
    fetch_compose() { printf '%s' "$_staged_src"; }
    prune_superseded() { :; }
    manifest_field() { case "$2" in *backend*) printf 'backend:v2' ;; *) printf 'caddy:v2' ;; esac; }
    run_migration() { return 0; }
    recreate_services() { printf 'recreated\n' >> "$_trace"; return 1; }
    wait_healthy() { printf 'health_checked\n' >> "$_trace"; return 0; }
    run_rollback() { printf 'rolled_back %s %s\n' "$1" "$2" >> "$_trace"; return 0; }
    run_update v2.0.0
)
assert_fail "run_update fails when the services cannot be recreated" \
    _update_recreate_fails
assert_eq "recreated
rolled_back v1.0.0 automatic" "$(cat "$_trace")" \
    "a failed recreate rolls back to the recorded running version, without health-checking"
assert_ok "the rollback target is rotated before the first replacing step" \
    test -f "$(versions_env_prev)"
assert_eq "v1.0.0" "$(pin_get "$(versions_env_prev)" APP_VERSION)" \
    "the rotated target is a copy of the version that was running"
assert_eq "services: {backend: {image: NEW}}" "$(cat "$(compose_file)")" \
    "the release's compose file is installed before the services are recreated"
assert_eq "services: {backend: {image: OLD}}" "$(cat "$(compose_file_prev)")" \
    "the previous compose file is kept for rollback"

: > "$_trace"
_update_health_fails() (
    acquire_images() { printf '/dev/null'; }
    fetch_compose() { printf '%s' "$_staged_src"; }
    prune_superseded() { :; }
    manifest_field() { case "$2" in *backend*) printf 'backend:v2' ;; *) printf 'caddy:v2' ;; esac; }
    run_migration() { return 0; }
    recreate_services() { write_pins v2.0.0 backend:v2 caddy:v2; return 0; }
    wait_healthy() { return 1; }
    run_rollback() { printf 'rolled_back %s %s\n' "$1" "$2" >> "$_trace"; return 0; }
    run_update v2.0.0
)
assert_fail "run_update fails when the new version is unhealthy" _update_health_fails
assert_eq "rolled_back v1.0.0 automatic" "$(cat "$_trace")" \
    "an unhealthy deploy rolls back to the version it started from"

# Rotation must fail loudly when there is no versions.env to copy, rather
# than leaving an empty rollback target that later reads as "no image refs".
: > "$_trace"
rm -f "$(versions_env)" "$(versions_env_prev)" "$(compose_file_prev)"
_update_no_record() (
    acquire_images() { printf '/dev/null'; }
    fetch_compose() { printf '%s' "$_staged_src"; }
    prune_superseded() { :; }
    manifest_field() { case "$2" in *backend*) printf 'backend:v2' ;; *) printf 'caddy:v2' ;; esac; }
    run_migration() { return 0; }
    recreate_services() { printf 'recreated\n' >> "$_trace"; return 0; }
    wait_healthy() { return 0; }
    run_rollback() { return 0; }
    run_update v2.0.0
)
assert_fail "run_update refuses to deploy with no version record to rotate" \
    _update_no_record
assert_eq "" "$(cat "$_trace")" "nothing is recreated when rotation failed"
assert_fail "a failed rotation leaves no empty rollback target" \
    test -f "$(versions_env_prev)"

# A manifest missing an image ref must abort before anything runs.
: > "$_trace"
_update_no_refs() (
    acquire_images() { printf '/dev/null'; }
    fetch_compose() { printf '%s' "$_staged_src"; }
    prune_superseded() { :; }
    manifest_field() { printf ''; }
    run_migration() { printf 'migrated\n' >> "$_trace"; return 0; }
    run_update v2.0.0
)
assert_fail "run_update refuses a manifest with no image refs" _update_no_refs
assert_eq "" "$(cat "$_trace")" "a refless manifest never reaches the migration"

# ── run_rollback ─────────────────────────────────────────────────────
write_pins v2.0.0 "backend:v2.0.0" "caddy:v2.0.0"
printf 'APP_VERSION=v1.0.0\nBACKEND_IMAGE=backend:v1.0.0\nCADDY_IMAGE=caddy:v1.0.0\n' \
    | atomic_write "$(versions_env_prev)"
printf 'services: {backend: {image: NEW}}\n' | atomic_write "$(compose_file)"
printf 'services: {backend: {image: OLD}}\n' | atomic_write "$(compose_file_prev)"

: > "$_trace"
_rollback() (
    _target=$1
    docker() { return "${FAKE_IMAGE_MISSING:-0}"; }
    recreate_services() { printf 'recreated %s %s\n' "$1" "$2" >> "$_trace"; write_pins "$1" "$2" "$3"; }
    run_migration() { printf 'MIGRATED\n' >> "$_trace"; return 0; }
    wait_healthy() { return "${FAKE_UNHEALTHY:-0}"; }
    run_rollback "$_target" manual
)

# Naming a version that is not the recorded previous one is a two-hop
# rollback: it would skip a schema generation and walk straight through the
# N-1 compatibility boundary the whole design rests on.
assert_fail "rollback refuses a target that is not the recorded previous version" \
    _rollback v0.9.0
assert_eq "" "$(cat "$_trace")" "a refused rollback recreates nothing"

FAKE_IMAGE_MISSING=1 assert_fail \
    "rollback refuses when the previous image is gone from the local store" \
    _rollback v1.0.0
unset FAKE_IMAGE_MISSING

FAKE_UNHEALTHY=1
assert_fail "rollback fails when the previous version does not come back healthy" \
    _rollback v1.0.0
assert_ok "a failed rollback keeps the target for a retry" \
    test -f "$(versions_env_prev)"
unset FAKE_UNHEALTHY

: > "$_trace"
assert_ok "rollback restores the recorded previous version" _rollback v1.0.0
assert_eq "recreated v1.0.0 backend:v1.0.0" "$(cat "$_trace")" \
    "rollback never runs a migration, forward or backward"
assert_eq "v1.0.0" "$(pin_get "$(versions_env)" APP_VERSION)" \
    "rollback pins the restored version"
assert_eq "services: {backend: {image: OLD}}" "$(cat "$(compose_file)")" \
    "rollback restores the compose file that matched the restored version"
# The target is DROPPED, not rotated: kept, it would name the version now
# running, so a second rollback would sail through the target check having
# done nothing. The rolled-back-FROM version is not a target either -- that
# is the release which just failed.
assert_fail "a successful rollback leaves no rollback target behind" \
    test -f "$(versions_env_prev)"
assert_fail "a successful rollback drops the previous compose file too" \
    test -f "$(compose_file_prev)"
assert_fail "a second rollback has nothing to restore" _rollback v1.0.0

rm -f "$_trace" "$_staged_src"

# ── dispatch ─────────────────────────────────────────────────────────
# main() must reject both inputs before touching anything, and the `*)` arm
# must die rather than fall through exiting 0 having deployed nothing.
DEPLOY_NO_MAIN=1; export DEPLOY_NO_MAIN
_dispatch() (
    . "$SCRIPT_DIR"/deploy.sh
    validate_startup() { return 0; }
    reap_orphans() { return 0; }
    run_update() { printf 'update %s\n' "$1"; }
    run_rollback() { printf 'rollback %s\n' "$1"; }
    main "$@"
)
assert_eq "update v1.5.0" "$(_dispatch update v1.5.0 2>/dev/null | tail -n 1)" \
    "main dispatches update"
assert_eq "rollback v1.5.0" "$(_dispatch rollback v1.5.0 2>/dev/null | tail -n 1)" \
    "main dispatches rollback"
assert_fail "main rejects an unknown action"  _dispatch 'shell' v1.5.0
assert_fail "main rejects an empty action"    _dispatch '' v1.5.0
assert_fail "main rejects an invalid version" _dispatch update 'v1; id'
assert_fail "main rejects an empty version"   _dispatch update ''

# Refuse to deploy beside an orphaned one-off: it may be a migration still
# writing to the database.
_dispatch_orphan() (
    . "$SCRIPT_DIR"/deploy.sh
    validate_startup() { return 0; }
    reap_orphans() { return 1; }
    run_update() { printf 'update\n'; }
    main update v1.5.0
)
assert_fail "main refuses to deploy beside an unreapable one-off" _dispatch_orphan
assert_eq "" "$(_dispatch_orphan 2>/dev/null)" \
    "nothing is deployed when the orphan check fails"

# reap_orphans must verify the removal rather than assume it: `rm -f` covers
# running and exited alike, but a container that survives it is the hazard.
_reap_survivor() (
    oneoff_ids() { printf 'abc123\n'; }
    docker() { return 0; }
    reap_orphans
)
assert_fail "reap_orphans fails when a one-off survives removal" _reap_survivor
_reap_none() (
    oneoff_ids() { printf ''; }
    reap_orphans
)
assert_ok "reap_orphans succeeds when there is nothing to reap" _reap_none

# No lock, no state file, no status directory: the workflow's concurrency
# group is the only serialisation, and the run page is the only status. A
# reintroduced state file here would be a second source of truth for the
# deployed version.
assert_eq "" "$(find "$PD" -name 'state.json' -o -name 'deployed.json' -o -name '*.lock')" \
    "a deploy writes no state or lock files"

rm -rf "$PD"

# ── result ───────────────────────────────────────────────────────────
printf '\n%s passed, %s failed\n' "$PASSES" "$FAILURES"
[ "$FAILURES" -eq 0 ]
