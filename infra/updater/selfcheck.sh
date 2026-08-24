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
# that explains a failure. Each line is "TIMESTAMP MESSAGE"; strip the
# timestamp field before comparing.
assert_eq "line 2499" "$(tail -n 1 "$STATUS_DIR/update.log" | cut -d' ' -f2-)" \
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
# Same per-line grep hazard as valid_version: a multi-line id could otherwise
# satisfy the anchors on one line while carrying a tab-smuggled field on another.
assert_fail "valid_uuid rejects an embedded newline" valid_uuid \
    '3f2504e0-4f89-41d3-9a0c-0305e82c3301
extra-line'

# ── version comparison ───────────────────────────────────────────────
assert_ok   "1.5.0 newer than 1.4.3"      version_newer v1.5.0 v1.4.3
assert_ok   "1.10.0 newer than 1.9.0"     version_newer v1.10.0 v1.9.0
assert_ok   "2.0 newer than 1.99.99"      version_newer v2.0 v1.99.99
assert_ok   "1.5.1 newer than 1.5"        version_newer v1.5.1 v1.5
assert_fail "1.4.3 not newer than 1.5.0"  version_newer v1.4.3 v1.5.0
assert_fail "equal is not newer"          version_newer v1.5.0 v1.5.0
assert_fail "v-prefix is not significant" version_newer v1.5.0 1.5.0
assert_fail "dev is never newer"          version_newer dev v1.0.0
assert_ok   "real version newer than dev" version_newer v1.0.0 dev

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

# A multi-line id must not slip through: read_request returns a single
# tab-separated line, and a smuggled newline+tab in id would shift action
# and version into the wrong fields for any caller splitting on tabs.
cat > "$RD/request.json" <<'JSON'
{"id":"3f2504e0-4f89-41d3-9a0c-0305e82c3301\nrollback\tv9.9.9","action":"update",
 "version":"v1.5.0","requested_at":"2026-08-24T10:00:00Z"}
JSON
assert_fail "read_request rejects a multi-line id" read_request "$RD/request.json"

printf 'not json' > "$RD/request.json"
assert_fail "read_request rejects malformed json" read_request "$RD/request.json"
assert_fail "read_request rejects a missing file" read_request "$RD/nope.json"
rm -rf "$RD"

# ── state machine ────────────────────────────────────────────────────
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

# ── review round 1: state_set must never blank state.json (Critical 1) ──
STATUS_DIR=$(mktemp -d); export STATUS_DIR
. /updater/lib/state.sh
state_init

printf 'not json' > "$(state_file)"
assert_fail "state_set refuses to write when state.json is corrupt" \
    state_set stage checking
assert_eq "not json" "$(cat "$(state_file)")" \
    "state_set left the corrupt file untouched rather than writing empty output"

: > "$(state_file)"
assert_fail "state_set refuses to write when state.json is empty" \
    state_set stage checking
assert_eq "" "$(cat "$(state_file)")" \
    "state_set made no write at all against an empty file"

# ── review round 2 (Important 3 regression pin): state_stage/state_terminal
# must propagate state_set's failure, not mask it with log's (always-zero)
# status. Corrupting state.json is the reachable way to force state_set to
# refuse, exactly as used manually during review.
printf 'not json' > "$(state_file)"
assert_fail "state_stage returns non-zero when the underlying state_set is refused" \
    state_stage checking
: > "$(state_file)"
assert_fail "state_terminal returns non-zero when the underlying state_set is refused" \
    state_terminal failed some_code "some message"
state_init

# ── review round 1: state_init repairs an invalid state.json (Critical 2) ──
printf 'not json' > "$(state_file)"
state_init
assert_ok "state_init repairs a corrupt state.json" jq -e . "$(state_file)"
assert_eq "idle" "$(state_get stage)" "state_init resets a corrupt file back to idle"

: > "$(state_file)"
state_init
assert_ok "state_init repairs an empty state.json" jq -e . "$(state_file)"
assert_eq "idle" "$(state_get stage)" "state_init resets an empty file back to idle"

# ── review round 1: odd argument count is a hard failure (promoted Minor 6) ──
state_init
assert_fail "state_set rejects an odd argument count" \
    state_set stage checking target_version
assert_eq "idle" "$(state_get stage)" "state_set made no partial write on odd args"

# ── review round 1: updated_at actually moves (Important 4) ──
state_init
state_set stage checking
T1=$(state_get updated_at)
assert_ok "updated_at is stamped after state_set" [ -n "$T1" ]
sleep 1
state_set stage downloading
T2=$(state_get updated_at)
assert_ok "updated_at is stamped after a second state_set" [ -n "$T2" ]
assert_fail "updated_at changes across state_set calls" [ "$T1" = "$T2" ]

rm -rf "$STATUS_DIR"

# ── review round 1: handle_request dispatch invariants (Important 5) ──
STATUS_DIR=$(mktemp -d); export STATUS_DIR
REQUEST_DIR=$(mktemp -d); export REQUEST_DIR
export UPDATER_NO_MAIN=1
. /updater/updater.sh
state_init

ID1=11111111-1111-1111-1111-111111111111
ID2=22222222-2222-2222-2222-222222222222

# (a) the id must be recorded as processed BEFORE the action is dispatched,
# so a crash inside run_update/run_rollback cannot cause a re-run.
SEEN_AT_DISPATCH=""
run_update()   { SEEN_AT_DISPATCH=$(state_get last_processed_request_id); }
run_rollback() { :; }

cat > "$REQUEST_DIR/request.json" <<JSON
{"id":"$ID1","action":"update","version":"v1.0.0","requested_at":"2026-08-24T10:00:00Z"}
JSON
handle_request
assert_eq "$ID1" "$SEEN_AT_DISPATCH" \
    "handle_request records the request id before dispatching the action"
assert_ok "lock is released after a successful dispatch" acquire_lock
release_lock

# (b) the lock must be released on every exit path that never dispatches...
rm -f "$REQUEST_DIR/request.json"
handle_request
assert_ok "lock is free when there was no request file" acquire_lock
release_lock

printf 'not json' > "$REQUEST_DIR/request.json"
handle_request
assert_ok "lock is free after an unparseable request" acquire_lock
release_lock

cat > "$REQUEST_DIR/request.json" <<JSON
{"id":"$ID1","action":"update","version":"v1.0.0","requested_at":"2026-08-24T10:00:00Z"}
JSON
handle_request
assert_ok "lock is free after a duplicate/already-processed request" acquire_lock
release_lock

# ...but NOT released when acquisition itself failed: handle_request never
# owned that lock, so it must not be the one to give it up.
acquire_lock
cat > "$REQUEST_DIR/request.json" <<JSON
{"id":"$ID2","action":"update","version":"v1.0.0","requested_at":"2026-08-24T10:00:00Z"}
JSON
handle_request
assert_fail "a pre-existing lock survives when handle_request could not acquire it" \
    acquire_lock
release_lock

unset UPDATER_NO_MAIN
rm -rf "$STATUS_DIR" "$REQUEST_DIR"

# ── review round 2: deployed_set has the same guards as state_set (Important) ──
STATUS_DIR=$(mktemp -d); export STATUS_DIR

printf 'not json' > "$(deployed_file)"
assert_ok "deployed_set recovers from a corrupt deployed.json" \
    deployed_set current_version v1.5.0
assert_eq "v1.5.0" "$(deployed_get current_version)" \
    "deployed_set wrote through after repairing a corrupt file"

rm -f "$(deployed_file)"
assert_ok "deployed_set creates deployed.json when missing" \
    deployed_set current_version v1.0.0
assert_eq "v1.0.0" "$(deployed_get current_version)" \
    "deployed_set on a missing file creates and writes it"

deployed_set previous_version v0.9.0
assert_eq "v1.0.0" "$(deployed_get current_version)" \
    "deployed_set merges, does not replace"
assert_eq "v0.9.0" "$(deployed_get previous_version)" \
    "deployed_set wrote the second key"

assert_fail "deployed_set rejects an odd argument count" \
    deployed_set current_version v2.0.0 previous_version
assert_eq "v1.0.0" "$(deployed_get current_version)" \
    "deployed_set made no partial write on odd args"

rm -rf "$STATUS_DIR"

# ── review round 2: main's startup lock-clear and signal handling ──────
# main() loops forever, so it cannot be sourced in-process like
# handle_request above. Instead this drives the real script as a child
# process (UPDATER_NO_MAIN left unset) and signals it -- the same shape as
# the container-level `docker kill`/`docker stop` checks in the report, just
# without a container. This proves the startup lock-clear runs and that
# SIGTERM makes the process exit promptly; it does NOT prove docker's exit
# code or that no request can slip in during shutdown -- see the report for
# the container-level evidence covering that.
STATUS_DIR=$(mktemp -d); export STATUS_DIR
REQUEST_DIR=$(mktemp -d); export REQUEST_DIR
PROJ=$(mktemp -d); mkdir -p "$PROJ/secrets"; touch "$PROJ/docker-compose.yml"
export COMPOSE_PROJECT_DIR="$PROJ"
export POLL_INTERVAL=5

# A lock left behind by a killed prior process.
mkdir -p "$STATUS_DIR"
mkdir "$STATUS_DIR/updater.lock"
printf '99999' > "$STATUS_DIR/updater.lock/pid"

sh /updater/updater.sh &
MAIN_PID=$!
sleep 1

assert_fail "startup clears a lock left by a previous, killed process" \
    [ -d "$STATUS_DIR/updater.lock" ]

# A process that crashed on boot would still be "gone" a moment after TERM,
# which would make the termination check below pass for the wrong reason.
# Confirm it is actually alive first, so "it was never running" cannot
# masquerade as "it terminated correctly".
assert_ok "the child is alive before it is signaled" kill -0 "$MAIN_PID"

kill -TERM "$MAIN_PID"

# Capture the real exit status rather than just checking liveness: only the
# status distinguishes a clean, handled exit (143) from any other way of
# dying (crash, hang, or a SIGKILL after a timeout). A background watchdog
# bounds the wait so a regression that makes TERM unhandled again fails this
# assertion instead of hanging the suite forever.
( sleep 5; kill -9 "$MAIN_PID" 2>/dev/null ) &
WATCHDOG=$!
wait "$MAIN_PID"
MAIN_STATUS=$?
kill "$WATCHDOG" 2>/dev/null
wait "$WATCHDOG" 2>/dev/null

assert_eq "143" "$MAIN_STATUS" \
    "a SIGTERM'd process exits with status 143 (handled), not left running or SIGKILLed"

unset COMPOSE_PROJECT_DIR POLL_INTERVAL
rm -rf "$STATUS_DIR" "$REQUEST_DIR" "$PROJ"

# ── artifact acquisition ─────────────────────────────────────────────
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

# review round 1: fill in the two branches that previously rested on
# unasserted external-tool behaviour.
printf 'payload' > "$WD/bndsphere-images-amd64.tar.gz"
( cd "$WD" && sha256sum bndsphere-images-amd64.tar.gz > SHA256SUMS )
rm -f "$WD/bndsphere-images-amd64.tar.gz"
# NOTE (review round 2): this pins fail-closed *behaviour*, not the explicit
# `[ -f "$_dir/$_name" ]` guard specifically -- sha256sum -c already refuses
# to check an entry whose file is missing on disk, so deleting the guard
# still leaves this assertion passing. It is kept anyway as belt-and-braces
# input validation (fail fast with a plain `return 1` instead of relying on
# the checksum tool's own error path), and the assertion is kept as honest
# documentation of the outcome, not a claim that it isolates that one line.
assert_fail "verify_checksum rejects when the target file is absent" \
    verify_checksum "$WD" bndsphere-images-amd64.tar.gz

printf 'payload' > "$WD/bndsphere-images-amd64.tar.gz"
printf 'deadbeef  some-other-file.tar.gz\n' > "$WD/SHA256SUMS"
assert_fail "verify_checksum rejects a SHA256SUMS with no entry for the file" \
    verify_checksum "$WD" bndsphere-images-amd64.tar.gz
rm -rf "$WD"

# Asset URLs are built from the updater's own config plus a validated version.
# The repo must never come from the request. The configured value here is
# deliberately NOT the built-in default -- an assertion using the default
# would pass even if asset_url ignored $GITHUB_REPO and hardcoded the URL.
assert_eq "https://github.com/some-other-org/some-other-repo/releases/download/v1.5.0/SHA256SUMS" \
    "$(GITHUB_REPO=some-other-org/some-other-repo asset_url v1.5.0 SHA256SUMS)" \
    "asset_url builds from configured repo, not the default"

# review round 1 (Critical 1): the post-load digest re-check must not pass
# vacuously when the manifest is missing image fields. A manifest with an
# empty .images yields an empty "want" digest; the image also won't exist
# under an empty ref, so "got" is empty too -- "" = "" must NOT read as a
# match. docker and download_asset are stubbed out: this environment has
# neither a real registry/release to hit nor a docker daemon socket, so the
# stubs isolate exactly the comparison logic being pinned, not the I/O around
# it (which remains unexercised -- see the report).
DWD=$(mktemp -d)
printf 'irrelevant' > "$DWD/bndsphere-images-amd64.tar.gz"
( cd "$DWD" && sha256sum bndsphere-images-amd64.tar.gz > SHA256SUMS )
printf '{"images":{}}' > "$DWD/release-manifest.json"
assert_fail "fetch_and_load_tarball refuses when manifest image fields are missing, instead of a vacuous pass" \
    env WORK_DIR="$DWD" STATUS_DIR="$(mktemp -d)" sh -c '
        . /updater/lib/state.sh
        . /updater/lib/artifact.sh
        download_asset() { return 0; }
        docker() { case "$1" in load) return 0 ;; image) return 1 ;; esac; }
        fetch_and_load_tarball v1.0.0 "'"$DWD"'/release-manifest.json"
    '
rm -rf "$DWD"

# review round 2 (Critical 2 regression pin): fetch_manifest must reject a
# manifest whose recorded checksum does not match, and must emit no path for
# a manifest it never verified. This is the exact fixture used to
# demonstrate the fix during review, promoted into the suite so a future
# revert of the verify_checksum call in fetch_manifest is caught here.
MWD=$(mktemp -d)
printf '{"images":{}}' > "$MWD/release-manifest.json"
printf 'deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef  release-manifest.json\n' \
    > "$MWD/SHA256SUMS"
FM_OUT=$(env WORK_DIR="$MWD" STATUS_DIR="$(mktemp -d)" sh -c '
    . /updater/lib/state.sh
    . /updater/lib/artifact.sh
    download_asset() { return 0; }
    fetch_manifest v1.0.0
')
FM_RC=$?
assert_ok "fetch_manifest rejects a manifest whose checksum does not match" \
    [ "$FM_RC" -ne 0 ]
assert_eq "" "$FM_OUT" \
    "fetch_manifest emits no manifest path when the checksum check fails"
rm -rf "$MWD"

# ── deploy: migration, recreation, health verification ──────────────
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

# MANAGED_SERVICES is the hardcoded list run_update may recreate. Postgres
# must never be named, recreated, or restarted (spec §5, §8, §18.3).
case "$MANAGED_SERVICES" in
    *postgres*) FAILURES=$((FAILURES + 1))
        printf 'FAIL: MANAGED_SERVICES includes postgres\n' >&2 ;;
    *) PASSES=$((PASSES + 1)) ;;
esac

# recreate_services must only ever target the managed app services, never
# postgres, and must go through the same four-flag compose wrapper.
PD4=$(mktemp -d); mkdir -p "$PD4/deploy" "$PD4/secrets"; touch "$PD4/docker-compose.yml"
COMPOSE_PROJECT_DIR=$PD4; export COMPOSE_PROJECT_DIR
COMPOSE_PROJECT_NAME=bndsphere; export COMPOSE_PROJECT_NAME
STATUS_DIR=$(mktemp -d); export STATUS_DIR
COMPOSE_ECHO=1; export COMPOSE_ECHO
RS_OUT=$(recreate_services "ghcr.io/o/bndsphere-backend:v1.6.0" "ghcr.io/o/bndsphere-caddy:v1.6.0")
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

# Important 1 fix: --no-deps must be present, or `up` pulls postgres in via
# depends_on (starting a deliberately-stopped postgres) and re-runs
# alembic-migration a second time via backend's service_completed_successfully
# dependency. This grep can only see the constructed argv -- it structurally
# cannot observe whether Compose's depends_on fan-out actually starts
# postgres or reruns migrations; that requires a live daemon and is
# unexercised here (see report).
case "$RS_OUT" in
    *"--no-deps"*) PASSES=$((PASSES + 1)) ;;
    *) FAILURES=$((FAILURES + 1))
       printf 'FAIL: recreate_services omits --no-deps (got: %s)\n' "$RS_OUT" >&2 ;;
esac
unset COMPOSE_ECHO
rm -rf "$PD4" "$STATUS_DIR"

# ── Critical 1 fix: write_version_pins/recreate_services must propagate a
# refused write instead of masking it behind log's always-zero return ──────
#
# atomic_write/compose are REAL library functions other tests below still
# need. A bare `func() { ... }` redefinition followed by `unset -f func` does
# NOT restore the original -- sh has no notion of a shadowed definition to
# fall back to, so `unset -f` just deletes it, permanently, for the rest of
# the script. Every override in this fix-round section therefore runs inside
# a `(...)` subshell function body: redefinitions made inside are local to
# that one call and vanish when the subshell exits, while any real file
# writes it makes (state.json, deployed.json) persist normally.
PDC1=$(mktemp -d); mkdir -p "$PDC1/deploy" "$PDC1/secrets"; touch "$PDC1/docker-compose.yml"
COMPOSE_PROJECT_DIR=$PDC1; export COMPOSE_PROJECT_DIR
STATUS_DIR=$(mktemp -d); export STATUS_DIR

_c1_write_pins_with_failing_atomic_write() (
    atomic_write() { cat >/dev/null; return 1; }
    write_version_pins "backend:v1" "caddy:v1"
)
assert_fail "write_version_pins returns non-zero when the underlying write fails" \
    _c1_write_pins_with_failing_atomic_write

_c1_up_called_file=$(mktemp)
_c1_recreate_with_failing_write() (
    atomic_write() { cat >/dev/null; return 1; }
    compose() { case "$1" in up) printf 'called' > "$_c1_up_called_file" ;; esac; }
    recreate_services "backend:v1" "caddy:v1"
)
_c1_recreate_with_failing_write >/dev/null 2>&1
assert_eq "" "$(cat "$_c1_up_called_file" 2>/dev/null)" \
    "recreate_services never calls compose up when the pin write failed"

rm -f "$_c1_up_called_file"
rm -rf "$PDC1" "$STATUS_DIR"

# ── Critical 2 fix: the health gate must fail when the running image does
# not match the recorded target, even if container health alone looks fine.
PDC2=$(mktemp -d); mkdir -p "$PDC2/deploy" "$PDC2/secrets"; touch "$PDC2/docker-compose.yml"
COMPOSE_PROJECT_DIR=$PDC2; export COMPOSE_PROJECT_DIR
COMPOSE_PROJECT_NAME=bndsphere; export COMPOSE_PROJECT_NAME
STATUS_DIR=$(mktemp -d); export STATUS_DIR

deployed_set target_backend_ref "new-backend:v2" target_caddy_ref "new-caddy:v2"

# Container health reports "healthy", but the running image is still the OLD
# one -- exactly what a silently-failed pin write / no-op `compose up` would
# produce. wait_healthy must not be fooled by that.
_c2_wait_healthy_mismatch() (
    HEALTH_TIMEOUT=1
    HEALTH_INTERVAL=0
    compose() { case "$1" in ps) printf 'fake-cid' ;; esac; }
    docker() {
        case "$1" in
            inspect)
                case "$*" in
                    *Health.Status*) printf 'healthy' ;;
                    *Config.Image*)  printf 'old-backend:v1' ;;
                esac
                ;;
        esac
    }
    app_ready() { return 0; }
    wait_healthy
)
assert_fail "wait_healthy fails when the running image does not match the recorded target" \
    _c2_wait_healthy_mismatch
rm -rf "$PDC2" "$STATUS_DIR"

# Positive control: the gate above proves wait_healthy can fail. Nothing so
# far proves it ever PASSES when it should -- a wait_healthy hard-coded to
# `return 1` would leave every prior assertion in this file green.
_c2b_wait_healthy_match() (
    HEALTH_TIMEOUT=1
    HEALTH_INTERVAL=0
    compose() { case "$1" in ps) printf 'fake-cid' ;; esac; }
    docker() {
        case "$1" in
            inspect)
                case "$*" in
                    *Health.Status*) printf 'healthy' ;;
                    *Config.Image*)  printf 'new-backend:v2' ;;
                esac
                ;;
        esac
    }
    app_ready() { return 0; }
    # Exercises the parameterised form directly (spec correction: rollback
    # must be able to pass its own expected refs instead of the recorded
    # target_*_ref, which name the version being rolled back FROM).
    wait_healthy "new-backend:v2" "new-backend:v2"
)
assert_ok "wait_healthy succeeds when containers are healthy and running the expected images" \
    _c2b_wait_healthy_match

# review round 2 (regression pin): the `-n "$_want"` guard must stay. Without
# it, an empty recorded/supplied target ref compared against an empty
# `docker inspect` result ("" = "") would pass vacuously -- the exact defect
# class already fixed once in lib/artifact.sh's digest re-check. No target
# ref has been recorded here (fresh STATUS_DIR, nothing written), so both
# sides of the comparison are empty by construction.
PDC2C=$(mktemp -d); mkdir -p "$PDC2C/deploy" "$PDC2C/secrets"; touch "$PDC2C/docker-compose.yml"
COMPOSE_PROJECT_DIR=$PDC2C; export COMPOSE_PROJECT_DIR
COMPOSE_PROJECT_NAME=bndsphere; export COMPOSE_PROJECT_NAME
STATUS_DIR=$(mktemp -d); export STATUS_DIR
_c2c_wait_healthy_vacuous() (
    HEALTH_TIMEOUT=1
    HEALTH_INTERVAL=0
    compose() { case "$1" in ps) printf 'fake-cid' ;; esac; }
    docker() {
        case "$1" in
            inspect)
                case "$*" in
                    *Health.Status*) printf 'healthy' ;;
                    *Config.Image*)  printf '' ;;
                esac
                ;;
        esac
    }
    app_ready() { return 0; }
    wait_healthy
)
assert_fail "wait_healthy refuses to pass when the target ref and the running image are both empty" \
    _c2c_wait_healthy_vacuous
rm -rf "$PDC2C" "$STATUS_DIR"

# review round 2: the state_set target_version guard has its own test --
# removing it left the suite green, since nothing previously drove run_update
# through a state_set failure at that specific site.
PDC4=$(mktemp -d); mkdir -p "$PDC4/deploy" "$PDC4/secrets"; touch "$PDC4/docker-compose.yml"
COMPOSE_PROJECT_DIR=$PDC4; export COMPOSE_PROJECT_DIR
COMPOSE_PROJECT_NAME=bndsphere; export COMPOSE_PROJECT_NAME
STATUS_DIR=$(mktemp -d); export STATUS_DIR
state_init
deployed_set current_version v1.0.0 current_backend_ref "old-backend" current_caddy_ref "old-caddy"

_c4_migration_called_file=$(mktemp)
_c4_terminal_args_file=$(mktemp)
_c4_state_set_target_version_fails() (
    acquire_images() { printf '%s' "$PDC4/manifest.json"; }
    manifest_field() {
        case "$2" in
            *backend*) printf 'new-backend' ;;
            *caddy*)   printf 'new-caddy' ;;
        esac
    }
    run_migration() { printf 'called' > "$_c4_migration_called_file"; return 0; }
    # `command state_set "$@"` cannot delegate to the real state_set: `command`
    # deliberately bypasses shell functions, and every library function here
    # is a shell function, so that delegation was a silent no-op. Instead,
    # fail only the exact call under test and succeed (without writing) for
    # every other call, then capture state_terminal's own arguments directly
    # rather than reading them back out of a state.json that was never
    # actually written to.
    state_set() {
        [ "$1" = "target_version" ] && return 1
        return 0
    }
    state_terminal() { printf '%s\n' "$@" > "$_c4_terminal_args_file"; }
    run_update v2.0.0
)
_c4_state_set_target_version_fails
RC=$?
assert_ok "run_update returns non-zero when state_set target_version fails" [ "$RC" -ne 0 ]
assert_eq "" "$(cat "$_c4_migration_called_file" 2>/dev/null)" \
    "run_update never reaches run_migration when state_set target_version fails"
assert_eq "state_write_failed" "$(sed -n '2p' "$_c4_terminal_args_file" 2>/dev/null)" \
    "a failed state_set target_version records state_write_failed"
assert_eq "could not record target_version; refusing to proceed" \
    "$(sed -n '3p' "$_c4_terminal_args_file" 2>/dev/null)" \
    "a failed state_set target_version pins the specific abort message"
rm -f "$_c4_migration_called_file" "$_c4_terminal_args_file"
rm -rf "$PDC4" "$STATUS_DIR"

# review round 2: the deployed_set target_* guard has its own test.
PDC5=$(mktemp -d); mkdir -p "$PDC5/deploy" "$PDC5/secrets"; touch "$PDC5/docker-compose.yml"
COMPOSE_PROJECT_DIR=$PDC5; export COMPOSE_PROJECT_DIR
COMPOSE_PROJECT_NAME=bndsphere; export COMPOSE_PROJECT_NAME
STATUS_DIR=$(mktemp -d); export STATUS_DIR
state_init
deployed_set current_version v1.0.0 current_backend_ref "old-backend" current_caddy_ref "old-caddy"

_c5_migration_called_file=$(mktemp)
_c5_terminal_args_file=$(mktemp)
_c5_deployed_set_target_fails() (
    acquire_images() { printf '%s' "$PDC5/manifest.json"; }
    manifest_field() {
        case "$2" in
            *backend*) printf 'new-backend' ;;
            *caddy*)   printf 'new-caddy' ;;
        esac
    }
    run_migration() { printf 'called' > "$_c5_migration_called_file"; return 0; }
    # Same delegation hazard as the state_set case above: `command
    # deployed_set "$@"` bypasses the shell function, so it never actually
    # wrote anything. Fail only the target_* call under test and capture
    # state_terminal's arguments directly instead of relying on a real write.
    # deployed_get reads in run_update before this point
    # (current_version/current_backend_ref/current_caddy_ref) go through the
    # real function untouched.
    deployed_set() {
        [ "$1" = "target_backend_ref" ] && return 1
        return 0
    }
    state_terminal() { printf '%s\n' "$@" > "$_c5_terminal_args_file"; }
    run_update v2.0.0
)
_c5_deployed_set_target_fails
RC=$?
assert_ok "run_update returns non-zero when deployed_set target_* fails" [ "$RC" -ne 0 ]
assert_eq "" "$(cat "$_c5_migration_called_file" 2>/dev/null)" \
    "run_update never reaches run_migration when deployed_set target_* fails"
assert_eq "state_write_failed" "$(sed -n '2p' "$_c5_terminal_args_file" 2>/dev/null)" \
    "a failed deployed_set target_* records state_write_failed"
assert_eq "could not record target image refs; refusing to proceed" \
    "$(sed -n '3p' "$_c5_terminal_args_file" 2>/dev/null)" \
    "a failed deployed_set target_* pins the specific abort message"
rm -f "$_c5_migration_called_file" "$_c5_terminal_args_file"
rm -rf "$PDC5" "$STATUS_DIR"

# ── Important 2 fix: a failed deployed_set current_* must never be followed
# by a recorded success -- the deploy is real and healthy, but the
# bookkeeping is stale, so this must surface as a failure, not silently as
# `state_terminal success`.
PDC3=$(mktemp -d); mkdir -p "$PDC3/deploy" "$PDC3/secrets"; touch "$PDC3/docker-compose.yml"
COMPOSE_PROJECT_DIR=$PDC3; export COMPOSE_PROJECT_DIR
COMPOSE_PROJECT_NAME=bndsphere; export COMPOSE_PROJECT_NAME
STATUS_DIR=$(mktemp -d); export STATUS_DIR
state_init
deployed_set current_version v1.0.0 current_backend_ref "old-backend" current_caddy_ref "old-caddy"

_c3_run_update_final_write_fails() (
    acquire_images() { printf '%s' "$PDC3/manifest.json"; }
    manifest_field() {
        case "$2" in
            *backend*) printf 'new-backend' ;;
            *caddy*)   printf 'new-caddy' ;;
        esac
    }
    run_migration() { return 0; }
    recreate_services() { return 0; }
    wait_healthy() { return 0; }
    # Three deployed_set calls happen on this path: (1) target_backend_ref/
    # target_caddy_ref, (2) previous_version/previous_backend_ref/
    # previous_caddy_ref (written just before recreate_services), (3) the
    # final current_* write. The first two must succeed so the run reaches
    # the current_* write this test targets; the third is what this test
    # forces to fail.
    _calls=0
    deployed_set() {
        _calls=$((_calls + 1))
        [ "$_calls" -ge 3 ] && return 1
        return 0
    }
    run_update v2.0.0
)
_c3_run_update_final_write_fails
RC=$?
assert_ok "run_update returns non-zero when the final deployed_set fails" [ "$RC" -ne 0 ]
assert_fail "a failed deployed_set current_* does not result in a recorded success" \
    [ "$(state_get stage)" = "success" ]

unset RC
rm -rf "$PDC3" "$STATUS_DIR"

# The migration must run against the NEW image, exposed as an environment
# override, NOT the old pin still on disk in versions.env. Compose ranks
# shell env above --env-file, so this is how an abort leaves the durable
# pins on the running version. Reversed, this would silently run the OLD
# migrations and report success.
PD2=$(mktemp -d); mkdir -p "$PD2/deploy" "$PD2/secrets"; touch "$PD2/docker-compose.yml"
COMPOSE_PROJECT_DIR=$PD2; export COMPOSE_PROJECT_DIR
STATUS_DIR=$(mktemp -d); export STATUS_DIR
write_version_pins "ghcr.io/o/bndsphere-backend:OLD" "ghcr.io/o/bndsphere-caddy:OLD"

# compose is a REAL library function; overriding it at top level and later
# `unset -f`-ing it would permanently delete the real one for the rest of
# this script (sh has no shadowing to fall back to -- same trap documented
# at the Critical 1 fix block above). Confined to a subshell instead.
_pd2_run_migration_uses_new_ref() (
    compose() { printf '%s' "$BACKEND_IMAGE"; }
    run_migration 'ghcr.io/o/bndsphere-backend:NEW'
)
assert_eq "ghcr.io/o/bndsphere-backend:NEW" \
    "$(_pd2_run_migration_uses_new_ref)" \
    "run_migration exposes the NEW backend ref to compose, not the old pin"
assert_eq "ghcr.io/o/bndsphere-backend:OLD" \
    "$(. "$PD2/deploy/versions.env"; printf '%s' "$BACKEND_IMAGE")" \
    "run_migration does not itself touch the still-OLD versions.env pin"
rm -rf "$PD2" "$STATUS_DIR"

# A failed migration must abort BEFORE any application container is
# replaced, leaving the old application running. No rollback is needed or
# attempted here, since nothing was replaced yet.
PD3=$(mktemp -d); mkdir -p "$PD3/deploy" "$PD3/secrets"; touch "$PD3/docker-compose.yml"
COMPOSE_PROJECT_DIR=$PD3; export COMPOSE_PROJECT_DIR
COMPOSE_PROJECT_NAME=bndsphere; export COMPOSE_PROJECT_NAME
STATUS_DIR=$(mktemp -d); export STATUS_DIR
state_init
deployed_set current_version v1.0.0 current_backend_ref "old-backend" current_caddy_ref "old-caddy"
write_version_pins "old-backend" "old-caddy"

# run_rollback is now a REAL library function (Task 6), not merely a test
# stub -- `unset -f` cannot un-shadow it (sh has no such concept; unset -f
# just deletes it, for the rest of this script). Every override here
# therefore runs inside a `(...)` subshell, same discipline as the Critical 1
# fix block above: redefinitions vanish when the subshell exits, and the two
# outcomes this test cares about are captured to files instead of variables,
# since subshell variable assignments do not propagate out either.
_recreate_called_file3=$(mktemp)
_rollback_called_file3=$(mktemp)
_pd3_failed_migration() (
    acquire_images() { printf '%s' "$PD3/manifest.json"; }
    manifest_field() {
        case "$2" in
            *backend*) printf 'new-backend' ;;
            *caddy*)   printf 'new-caddy' ;;
        esac
    }
    run_migration() { return 1; }
    recreate_services() { printf 'called' > "$_recreate_called_file3"; }
    run_rollback() { printf 'called' > "$_rollback_called_file3"; }
    run_update v2.0.0
)
_pd3_failed_migration
assert_eq "" "$(cat "$_recreate_called_file3" 2>/dev/null)" \
    "a failed migration never reaches recreate_services"
assert_eq "" "$(cat "$_rollback_called_file3" 2>/dev/null)" \
    "a failed migration does not trigger rollback (nothing was replaced yet)"
assert_eq "failed" "$(state_get stage)" \
    "a failed migration lands in the failed terminal stage"
assert_eq "migration_failed" "$(state_get error_code)" \
    "a failed migration records migration_failed"
assert_eq "old-backend" \
    "$(. "$PD3/deploy/versions.env"; printf '%s' "$BACKEND_IMAGE")" \
    "a failed migration leaves the durable pins on the OLD running version"

rm -f "$_recreate_called_file3" "$_rollback_called_file3"
rm -rf "$PD3" "$STATUS_DIR"

# ── rollback: the shared executor ────────────────────────────────────
# The unification guarantee, asserted mechanically: `trigger` may be
# recorded, but it must never appear in a conditional. If someone later
# writes `if [ "$trigger" = automatic ]`, this fails.
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
# Widened beyond the function name: a direct `compose run --rm
# "$MIGRATION_SERVICE"` (bypassing run_migration entirely) or any literal
# mention of the migration service/tool would go undetected by a check that
# only greps for the one call-site spelling.
assert_eq "" "$(printf '%s' "$ROLLBACK_BODY" | grep -niE 'run_migration|alembic|MIGRATION_SERVICE')" \
    "run_rollback never runs migrations (by name, service constant, or direct invocation)"

# Shadowing hazard, asserted directly: updater.sh must not define run_rollback
# or run_update itself. Both live in lib/deploy.sh (sourced above them); a
# stub reintroduced here after that sourcing would silently shadow the real
# implementation (this bit run_update in Task 5, and would have made every
# production rollback a silent no-op if reintroduced for run_rollback). The
# behavioural tests below cannot catch this: selfcheck.sh itself re-sources
# lib/deploy.sh after updater.sh, which would overwrite any such shadow
# before a single rollback test ran -- masking the exact defect this
# assertion exists to catch in the real container, where deploy.sh is
# sourced only once, from inside updater.sh, in the shadowed order.
assert_eq "" "$(grep -n '^run_rollback()' /updater/updater.sh)" \
    "updater.sh does not itself define run_rollback"
assert_eq "" "$(grep -n '^run_update()' /updater/updater.sh)" \
    "updater.sh does not itself define run_update"
# Same trap, same fix, for recover_if_interrupted (lib/recover.sh, Task 7):
# a stub reintroduced after the sourcing block would shadow the real function
# and make every restart-time recovery a silent no-op. Same masking caveat as
# above -- selfcheck.sh also re-sources lib/recover.sh later for the recovery
# tests below, which would overwrite any such shadow before those tests ran.
assert_eq "" "$(grep -n '^recover_if_interrupted()' /updater/updater.sh)" \
    "updater.sh does not itself define recover_if_interrupted"

# Both call sites must exist and both must reach the same function. The
# brief's original version of this check expected 2 total call sites
# (one automatic, one manual); the real run_update has TWO automatic call
# sites (recreate_services failure and wait_healthy failure), so the
# accurate total is 3. Asserted precisely per site instead of as a vague
# sum, so a regression in either file is unambiguous about which broke.
assert_eq "2" "$(grep -c 'run_rollback "\$_current" automatic' /updater/lib/deploy.sh)" \
    "run_update has exactly two automatic rollback call sites"
assert_eq "1" "$(grep -c 'run_rollback "\$_version" manual' /updater/updater.sh)" \
    "updater.sh has exactly one manual rollback call site"

# postgres must never appear anywhere run_rollback's function definition
# constructs or names services.
assert_eq "" "$(printf '%s' "$ROLLBACK_BODY" | grep -ni postgres)" \
    "run_rollback never mentions postgres"

# ── rollback: happy path ─────────────────────────────────────────────
PDR=$(mktemp -d); mkdir -p "$PDR/deploy" "$PDR/secrets"; touch "$PDR/docker-compose.yml"
COMPOSE_PROJECT_DIR=$PDR; export COMPOSE_PROJECT_DIR
COMPOSE_PROJECT_NAME=bndsphere; export COMPOSE_PROJECT_NAME
STATUS_DIR=$(mktemp -d); export STATUS_DIR
state_init
deployed_set current_version v2.0.0 \
    current_backend_ref "new-backend:v2" current_caddy_ref "new-caddy:v2" \
    target_backend_ref "wrong-backend:v3" target_caddy_ref "wrong-caddy:v3" \
    previous_version v1.0.0 \
    previous_backend_ref "old-backend:v1" previous_caddy_ref "old-caddy:v1"

_wh_args_file=$(mktemp)
COMPOSE_ECHO=1; export COMPOSE_ECHO
_rollback_happy_path() (
    docker() { case "$1" in image) return 0 ;; esac; }
    wait_healthy() { printf '%s %s' "$1" "$2" > "$_wh_args_file"; return 0; }
    run_rollback v1.0.0 automatic
)
RS_OUT=$(_rollback_happy_path)
RC=$?
unset COMPOSE_ECHO

assert_eq "0" "$RC" \
    "rollback succeeds when the previous images are present and health passes"
assert_eq "rollback_success" "$(state_get stage)" \
    "rollback records rollback_success on the happy path"
assert_eq "v1.0.0" "$(deployed_get current_version)" \
    "rollback updates current_version to the restored target"
assert_eq "old-backend:v1" "$(deployed_get current_backend_ref)" \
    "rollback updates current_backend_ref to the restored ref"
assert_eq "old-backend:v1 old-caddy:v1" "$(cat "$_wh_args_file")" \
    "rollback passes the restored OLD refs to the health gate, not the recorded target refs"
case "$RS_OUT" in
    *postgres*) FAILURES=$((FAILURES + 1))
        printf 'FAIL: rollback constructed a command naming postgres (got: %s)\n' "$RS_OUT" >&2 ;;
    *) PASSES=$((PASSES + 1)) ;;
esac
case "$RS_OUT" in
    *alembic*) FAILURES=$((FAILURES + 1))
        printf 'FAIL: rollback constructed a command naming the migration service (got: %s)\n' "$RS_OUT" >&2 ;;
    *) PASSES=$((PASSES + 1)) ;;
esac
rm -f "$_wh_args_file"
rm -rf "$PDR" "$STATUS_DIR"

# ── rollback: absent previous images fail closed, before anything changes ──
PDA=$(mktemp -d); mkdir -p "$PDA/deploy" "$PDA/secrets"; touch "$PDA/docker-compose.yml"
COMPOSE_PROJECT_DIR=$PDA; export COMPOSE_PROJECT_DIR
COMPOSE_PROJECT_NAME=bndsphere; export COMPOSE_PROJECT_NAME
STATUS_DIR=$(mktemp -d); export STATUS_DIR
state_init
deployed_set current_version v2.0.0 \
    current_backend_ref "new-backend:v2" current_caddy_ref "new-caddy:v2" \
    previous_version v1.0.0 \
    previous_backend_ref "old-backend:v1" previous_caddy_ref "old-caddy:v1"

_recreate_called_file=$(mktemp)
_rollback_absent_images() (
    docker() { case "$1" in image) return 1 ;; esac; }
    recreate_services() { printf 'called' > "$_recreate_called_file"; return 0; }
    run_rollback v1.0.0 automatic
)
_rollback_absent_images
RC=$?
assert_ok "rollback fails when the previous images are absent locally" [ "$RC" -ne 0 ]
assert_eq "rollback_unavailable" "$(state_get error_code)" \
    "absent previous images record rollback_unavailable"
assert_eq "" "$(cat "$_recreate_called_file" 2>/dev/null)" \
    "rollback never recreates services when the previous images are absent"
rm -f "$_recreate_called_file"
rm -rf "$PDA" "$STATUS_DIR"

# No previous refs recorded at all (e.g. never deployed twice) must also
# refuse, distinct from a mismatched target but with the same code -- both
# mean rollback cannot proceed from here. previous_version is deliberately
# set to MATCH the requested target, so the mismatch guard would not fire if
# reached: this isolates the empty-ref guard specifically. Checking the
# error_message (not just the shared error_code) and that recreate_services
# is never called are both required for that isolation -- with only the
# error_code check, deleting the empty-ref guard entirely would still leave
# this green, because the mismatch guard (or, if previous_version also
# matched, the image-presence guard against an empty ref) produces the same
# rollback_unavailable code.
PDN=$(mktemp -d); mkdir -p "$PDN/deploy" "$PDN/secrets"; touch "$PDN/docker-compose.yml"
COMPOSE_PROJECT_DIR=$PDN; export COMPOSE_PROJECT_DIR
COMPOSE_PROJECT_NAME=bndsphere; export COMPOSE_PROJECT_NAME
STATUS_DIR=$(mktemp -d); export STATUS_DIR
state_init
deployed_set current_version v1.0.0 current_backend_ref "backend:v1" current_caddy_ref "caddy:v1" \
    previous_version v0.9.0
# previous_backend_ref/previous_caddy_ref are deliberately left unset:
# deployed_get returns "" for a key that was never written.
_recreate_called_file_n=$(mktemp)
_rollback_no_previous_refs() (
    recreate_services() { printf 'called' > "$_recreate_called_file_n"; return 0; }
    run_rollback v0.9.0 automatic
)
_rollback_no_previous_refs
assert_eq "rollback_unavailable" "$(state_get error_code)" \
    "rollback with no previous refs recorded refuses with rollback_unavailable"
assert_eq "no previous image references recorded" "$(state_get error_message)" \
    "rollback with no previous refs recorded is refused specifically for missing refs, not a target mismatch"
assert_eq "" "$(cat "$_recreate_called_file_n" 2>/dev/null)" \
    "rollback never recreates services when no previous refs are recorded"
rm -f "$_recreate_called_file_n"
rm -rf "$PDN" "$STATUS_DIR"

# ── rollback: a stale previous_version that does not match the target
# is refused (the two-hop hazard) ────────────────────────────────────
PDS=$(mktemp -d); mkdir -p "$PDS/deploy" "$PDS/secrets"; touch "$PDS/docker-compose.yml"
COMPOSE_PROJECT_DIR=$PDS; export COMPOSE_PROJECT_DIR
COMPOSE_PROJECT_NAME=bndsphere; export COMPOSE_PROJECT_NAME
STATUS_DIR=$(mktemp -d); export STATUS_DIR
state_init
# deployed.json's previous_version names v1.0.0, but the caller is asking to
# restore v2.0.0 -- e.g. an operator undoing a failed v2.0.0 -> v3.0.0
# update whose previous_version bookkeeping is one hop stale. Restoring
# v1.0.0's refs anyway would silently skip v2.0.0 entirely.
deployed_set current_version v3.0.0 \
    current_backend_ref "backend:v3" current_caddy_ref "caddy:v3" \
    previous_version v1.0.0 \
    previous_backend_ref "old-backend:v1" previous_caddy_ref "old-caddy:v1"

_recreate_called_file2=$(mktemp)
_rollback_stale_previous() (
    docker() { case "$1" in image) return 0 ;; esac; }
    recreate_services() { printf 'called' > "$_recreate_called_file2"; return 0; }
    run_rollback v2.0.0 manual
)
_rollback_stale_previous
RC=$?
assert_ok "rollback refuses a target that does not match the recorded previous_version" \
    [ "$RC" -ne 0 ]
assert_eq "rollback_unavailable" "$(state_get error_code)" \
    "a mismatched rollback target records rollback_unavailable"
assert_eq "" "$(cat "$_recreate_called_file2" 2>/dev/null)" \
    "rollback never touches running containers when the target does not match the recorded previous version"
rm -f "$_recreate_called_file2"
rm -rf "$PDS" "$STATUS_DIR"

# ── rollback: a failed final durable write is never a recorded success ──
PDF=$(mktemp -d); mkdir -p "$PDF/deploy" "$PDF/secrets"; touch "$PDF/docker-compose.yml"
COMPOSE_PROJECT_DIR=$PDF; export COMPOSE_PROJECT_DIR
COMPOSE_PROJECT_NAME=bndsphere; export COMPOSE_PROJECT_NAME
STATUS_DIR=$(mktemp -d); export STATUS_DIR
state_init
deployed_set current_version v2.0.0 \
    current_backend_ref "backend:v2" current_caddy_ref "caddy:v2" \
    previous_version v1.0.0 \
    previous_backend_ref "old-backend:v1" previous_caddy_ref "old-caddy:v1"

_rollback_final_write_fails() (
    docker() { case "$1" in image) return 0 ;; esac; }
    recreate_services() { return 0; }
    wait_healthy() { return 0; }
    deployed_set() { return 1; }
    run_rollback v1.0.0 automatic
)
_rollback_final_write_fails
RC=$?
assert_ok "rollback returns non-zero when the final deployed_set write fails" \
    [ "$RC" -ne 0 ]
assert_fail "a failed final write is never recorded as rollback_success" \
    [ "$(state_get stage)" = "rollback_success" ]
rm -rf "$PDF" "$STATUS_DIR"

# ── rollback: the opening stage/trigger write is checked too ────────────
# Every other durable write in run_rollback aborts on refusal; the opening
# `state_set stage rolling_back trigger ...` must not be the one silent
# exception, or a refused write here leaves the trigger field absent with no
# indication anything went wrong.
PDG=$(mktemp -d); mkdir -p "$PDG/deploy" "$PDG/secrets"; touch "$PDG/docker-compose.yml"
COMPOSE_PROJECT_DIR=$PDG; export COMPOSE_PROJECT_DIR
COMPOSE_PROJECT_NAME=bndsphere; export COMPOSE_PROJECT_NAME
STATUS_DIR=$(mktemp -d); export STATUS_DIR
state_init
deployed_set current_version v2.0.0 \
    current_backend_ref "backend:v2" current_caddy_ref "caddy:v2" \
    previous_version v1.0.0 \
    previous_backend_ref "old-backend:v1" previous_caddy_ref "old-caddy:v1"

_recreate_called_file_g=$(mktemp)
_rollback_stage_write_fails() (
    docker() { case "$1" in image) return 0 ;; esac; }
    recreate_services() { printf 'called' > "$_recreate_called_file_g"; return 0; }
    wait_healthy() { return 0; }
    state_set() { return 1; }
    run_rollback v1.0.0 automatic
)
_rollback_stage_write_fails
RC=$?
assert_ok "rollback returns non-zero when the opening state_set write fails" \
    [ "$RC" -ne 0 ]
assert_eq "" "$(cat "$_recreate_called_file_g" 2>/dev/null)" \
    "rollback never touches running containers when the opening state_set write fails"
rm -f "$_recreate_called_file_g"
rm -rf "$PDG" "$STATUS_DIR"

# ── rollback: automatic and manual reach run_rollback identically, proven
# behaviourally (not just by the static grep above) -- same inputs, same
# outputs, the trigger only shows up in the recorded field. ─────────────
PDT=$(mktemp -d); mkdir -p "$PDT/deploy" "$PDT/secrets"; touch "$PDT/docker-compose.yml"
COMPOSE_PROJECT_DIR=$PDT; export COMPOSE_PROJECT_DIR
COMPOSE_PROJECT_NAME=bndsphere; export COMPOSE_PROJECT_NAME
STATUS_DIR=$(mktemp -d); export STATUS_DIR
state_init
deployed_set current_version v2.0.0 \
    current_backend_ref "backend:v2" current_caddy_ref "caddy:v2" \
    previous_version v1.0.0 \
    previous_backend_ref "old-backend:v1" previous_caddy_ref "old-caddy:v1"
_rollback_via() (
    docker() { case "$1" in image) return 0 ;; esac; }
    recreate_services() { return 0; }
    wait_healthy() { return 0; }
    run_rollback v1.0.0 "$1"
)
_rollback_via automatic
assert_eq "automatic" "$(state_get trigger)" "an automatic rollback records trigger=automatic"
assert_eq "rollback_success" "$(state_get stage)" "an automatic rollback reaches rollback_success"
deployed_set current_version v2.0.0 previous_version v1.0.0
_rollback_via manual
assert_eq "manual" "$(state_get trigger)" "a manual rollback records trigger=manual"
assert_eq "rollback_success" "$(state_get stage)" "a manual rollback reaches rollback_success"
rm -rf "$PDT" "$STATUS_DIR"

# ── rollback: end-to-end, driven entirely through run_update ────────────
# Pins the Critical fix's placement of the previous_* write: two good
# deploys, then a third whose health check fails. acquire_images/
# manifest_field are stubbed to derive deterministic, version-tagged refs
# (e.g. "backend:v2.0.0") straight from the requested version, so each
# deploy in the sequence gets distinguishable refs without extra plumbing.
PDE=$(mktemp -d); mkdir -p "$PDE/deploy" "$PDE/secrets"; touch "$PDE/docker-compose.yml"
COMPOSE_PROJECT_DIR=$PDE; export COMPOSE_PROJECT_DIR
COMPOSE_PROJECT_NAME=bndsphere; export COMPOSE_PROJECT_NAME
STATUS_DIR=$(mktemp -d); export STATUS_DIR
state_init

_e2e_deploy_good() (
    acquire_images() { printf '%s' "$1"; }
    manifest_field() {
        case "$2" in
            *backend*) printf 'backend:%s' "$1" ;;
            *caddy*)   printf 'caddy:%s' "$1" ;;
        esac
    }
    run_migration() { return 0; }
    recreate_services() { return 0; }
    wait_healthy() { return 0; }
    run_update "$1"
)
_e2e_deploy_good v1.0.0
_e2e_deploy_good v2.0.0
assert_eq "v2.0.0" "$(deployed_get current_version)" \
    "e2e: two good deploys land on v2.0.0"
assert_eq "v1.0.0" "$(deployed_get previous_version)" \
    "e2e: two good deploys record v1.0.0 as previous"

# Third deploy's health check fails -> automatic rollback must restore
# v2.0.0. wait_healthy is called from two places here: run_update's forward
# check (no args, must fail) and run_rollback's check (explicit restored
# refs, must pass) -- distinguished by whether an argument was passed.
_e2e_deploy_v3_unhealthy() (
    acquire_images() { printf '%s' "$1"; }
    manifest_field() {
        case "$2" in
            *backend*) printf 'backend:%s' "$1" ;;
            *caddy*)   printf 'caddy:%s' "$1" ;;
        esac
    }
    run_migration() { return 0; }
    recreate_services() { return 0; }
    wait_healthy() { [ -n "${1:-}" ] && return 0; return 1; }
    docker() { case "$1" in image) return 0 ;; esac; }
    run_update v3.0.0
)
_e2e_deploy_v3_unhealthy
RC=$?
assert_ok "e2e: a failing health check on the third deploy returns non-zero" [ "$RC" -ne 0 ]
assert_eq "rollback_success" "$(state_get stage)" \
    "e2e: automatic rollback reaches rollback_success after a failed health check"
assert_eq "v2.0.0" "$(deployed_get current_version)" \
    "e2e: automatic rollback restores current_version to the previous version"
assert_eq "backend:v2.0.0" "$(deployed_get current_backend_ref)" \
    "e2e: automatic rollback restores the previous backend ref"
rm -rf "$PDE" "$STATUS_DIR"

# Pins the Critical fix from the OTHER side: two good deploys, then a third
# whose container RECREATION fails (not the health check). Migration has
# already succeeded by this point, so the previous_* write has already
# happened -- if it were moved any later (e.g. after recreate_services, the
# reviewer's own counter-example), automatic rollback here would read
# previous_backend_ref/previous_version still naming v1.0.0 (the version
# before v2.0.0), not v2.0.0 -- a target/previous_version mismatch that
# refuses with rollback_unavailable before ever reaching recreation.
PDR2=$(mktemp -d); mkdir -p "$PDR2/deploy" "$PDR2/secrets"; touch "$PDR2/docker-compose.yml"
COMPOSE_PROJECT_DIR=$PDR2; export COMPOSE_PROJECT_DIR
COMPOSE_PROJECT_NAME=bndsphere; export COMPOSE_PROJECT_NAME
STATUS_DIR=$(mktemp -d); export STATUS_DIR
state_init

_e2e3_deploy_good() (
    acquire_images() { printf '%s' "$1"; }
    manifest_field() {
        case "$2" in
            *backend*) printf 'backend:%s' "$1" ;;
            *caddy*)   printf 'caddy:%s' "$1" ;;
        esac
    }
    run_migration() { return 0; }
    recreate_services() { return 0; }
    wait_healthy() { return 0; }
    run_update "$1"
)
_e2e3_deploy_good v1.0.0
_e2e3_deploy_good v2.0.0

_e2e3_deploy_v3_recreate_fails() (
    acquire_images() { printf '%s' "$1"; }
    manifest_field() {
        case "$2" in
            *backend*) printf 'backend:%s' "$1" ;;
            *caddy*)   printf 'caddy:%s' "$1" ;;
        esac
    }
    run_migration() { return 0; }
    # Fails only for the forward attempt's NEW (v3.0.0) refs; the automatic
    # rollback below calls this same function again to restore v2.0.0's
    # refs, and that second call must succeed.
    recreate_services() { case "$1" in *v3.0.0*) return 1 ;; *) return 0 ;; esac; }
    wait_healthy() { return 0; }
    docker() { case "$1" in image) return 0 ;; esac; }
    run_update v3.0.0
)
_e2e3_deploy_v3_recreate_fails
RC=$?
assert_ok "e2e: a failing container recreation on the third deploy returns non-zero" \
    [ "$RC" -ne 0 ]
assert_eq "rollback_success" "$(state_get stage)" \
    "e2e: automatic rollback reaches rollback_success after a failed recreation"
assert_eq "v2.0.0" "$(deployed_get current_version)" \
    "e2e: automatic rollback after a failed recreation restores the previous version"
rm -rf "$PDR2" "$STATUS_DIR"

# Critical fix pin: an aborted (migration_failed) update must leave
# previous_version/previous_backend_ref/previous_caddy_ref untouched -- and a
# subsequent MANUAL rollback to the genuine previous version must still
# work, not be refused and not silently "succeed" at restoring the version
# that is already running.
PDE2=$(mktemp -d); mkdir -p "$PDE2/deploy" "$PDE2/secrets"; touch "$PDE2/docker-compose.yml"
COMPOSE_PROJECT_DIR=$PDE2; export COMPOSE_PROJECT_DIR
COMPOSE_PROJECT_NAME=bndsphere; export COMPOSE_PROJECT_NAME
STATUS_DIR=$(mktemp -d); export STATUS_DIR
state_init

_e2e2_deploy_good() (
    acquire_images() { printf '%s' "$1"; }
    manifest_field() {
        case "$2" in
            *backend*) printf 'backend:%s' "$1" ;;
            *caddy*)   printf 'caddy:%s' "$1" ;;
        esac
    }
    run_migration() { return 0; }
    recreate_services() { return 0; }
    wait_healthy() { return 0; }
    run_update "$1"
)
_e2e2_deploy_good v1.0.0
_e2e2_deploy_good v2.0.0

_e2e2_deploy_v3_migration_fails() (
    acquire_images() { printf '%s' "$1"; }
    manifest_field() {
        case "$2" in
            *backend*) printf 'backend:%s' "$1" ;;
            *caddy*)   printf 'caddy:%s' "$1" ;;
        esac
    }
    run_migration() { return 1; }
    run_update v3.0.0
)
_e2e2_deploy_v3_migration_fails
assert_eq "v2.0.0" "$(deployed_get current_version)" \
    "e2e: an aborted (migration_failed) update leaves current_version on the running v2.0.0"
assert_eq "v1.0.0" "$(deployed_get previous_version)" \
    "e2e: an aborted update does not overwrite previous_version with the version still running"

_e2e2_manual_rollback_after_abort() (
    docker() { case "$1" in image) return 0 ;; esac; }
    recreate_services() { return 0; }
    wait_healthy() { return 0; }
    run_rollback v1.0.0 manual
)
_e2e2_manual_rollback_after_abort
RC=$?
assert_eq "0" "$RC" \
    "e2e: manual rollback to the genuine previous version succeeds after an aborted update"
assert_eq "rollback_success" "$(state_get stage)" \
    "e2e: manual rollback after an aborted update reaches rollback_success"
assert_eq "v1.0.0" "$(deployed_get current_version)" \
    "e2e: manual rollback after an aborted update actually restores v1.0.0, not a v2.0.0 no-op"
rm -rf "$PDE2" "$STATUS_DIR"

# ── recovery: interrupted operations are marked, never resumed ─────────
. /updater/lib/recover.sh

STATUS_DIR=$(mktemp -d); export STATUS_DIR
state_init

# A terminal stage means nothing was interrupted — leave it untouched. Not
# just the stage field: no interrupted_stage bookkeeping and no restart log
# line either, or a build that logs a misleading restart line and reaps
# containers on every terminal-stage boot would still read as "untouched".
state_set stage success
recover_if_interrupted
assert_eq "success" "$(state_get stage)" "recovery leaves a terminal stage alone"
assert_eq "" "$(state_get interrupted_stage)" \
    "recovery leaves a terminal stage without writing interrupted_stage"
assert_fail "recovery leaves a terminal stage without logging a restart line" \
    grep -q 'marking interrupted, not resuming' "$STATUS_DIR/update.log"

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

# Recovery must never act on the deployment itself. Widened beyond
# "compose up": deploy.sh's `compose` wrapper is in scope at runtime
# (sourced before recover.sh), so any compose invocation -- e.g. a
# `compose down --remove-orphans` swapped in for the orphan reap -- is a
# reachable violation of "never touches the deployment", not just an "up".
# `(^|[^.])compose[[:space:]]` matches a compose CALL (word followed by a
# space) while leaving the label filters ("com.docker.compose.project=...")
# alone, since those instances are preceded by a dot.
RECOVER_SRC=$(cat /updater/lib/recover.sh)
assert_eq "" "$(printf '%s' "$RECOVER_SRC" \
        | grep -nE 'run_update|run_rollback|recreate_services|(^|[^.])compose[[:space:]]')" \
    "recovery never invokes update, rollback, or any compose command"

# Recovery must actually run before the poll loop can dispatch a new
# request -- unwiring the call from main, or moving it below `while true`,
# must fail here even though every behavioural test above sources
# lib/recover.sh directly and would stay green either way.
assert_eq "1" "$(grep -c '^    recover_if_interrupted$' /updater/updater.sh)" \
    "main calls recover_if_interrupted exactly once"

_recover_call_line=$(grep -n '^    recover_if_interrupted$' /updater/updater.sh \
    | head -1 | cut -d: -f1)
_poll_loop_line=$(grep -n 'while true; do' /updater/updater.sh | head -1 | cut -d: -f1)
_recover_runs_before_poll_loop() {
    [ -n "$_recover_call_line" ] || return 1
    [ -n "$_poll_loop_line" ] || return 1
    [ "$_recover_call_line" -lt "$_poll_loop_line" ]
}
assert_ok "recover_if_interrupted is called before the poll loop begins" \
    _recover_runs_before_poll_loop

rm -rf "$STATUS_DIR"

# ── image retention: narrow, digest-exact, never bulk ───────────────────
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
# An empty keep-set must protect everything rather than delete everything --
# failing open is the only safe direction here.
assert_ok   "empty keep-set protects"   is_protected sha256:ccc "" ""

# ── prune_superseded_images: prove the SELECTION is right, not just that
# the function runs. There is no docker daemon in this environment, so
# `docker image inspect`, `docker images`, and `docker rmi` are stubbed. The
# stub's `docker images` output deliberately includes: the current and
# previous digest for each repo, a genuinely superseded digest (positive
# control), a digest simulated as in-use by a running container, a
# same-family-but-different repo that merely LOOKS like an application image
# ("bndsphere-backend-staging"), and a repo from a different org entirely.
# `docker image inspect` deliberately returns the "sha256:" prefix that real
# Docker uses there (unlike the unprefixed IDs `docker images` prints), so
# this also pins the id-normalisation retention.sh depends on to match them.
PDR=$(mktemp -d); mkdir -p "$PDR/deploy" "$PDR/secrets"; touch "$PDR/docker-compose.yml"
COMPOSE_PROJECT_DIR=$PDR; export COMPOSE_PROJECT_DIR
STATUS_DIR=$(mktemp -d); export STATUS_DIR
state_init

deployed_set \
    current_backend_ref  "ghcr.io/o/bndsphere-backend:v3.0.0" \
    previous_backend_ref "ghcr.io/o/bndsphere-backend:v2.0.0" \
    current_caddy_ref    "ghcr.io/o/bndsphere-caddy:v3.0.0" \
    previous_caddy_ref   "ghcr.io/o/bndsphere-caddy:v2.0.0"

_rt_rmi_log=$(mktemp)
_rt_run() (
    docker() {
        case "$1" in
            image)
                # image inspect --format '{{.Id}}' REF ($5 is the ref)
                case "$5" in
                    *bndsphere-backend:v3.0.0) printf 'sha256:cur_backend' ;;
                    *bndsphere-backend:v2.0.0) printf 'sha256:prev_backend' ;;
                    *bndsphere-caddy:v3.0.0)   printf 'sha256:cur_caddy' ;;
                    *bndsphere-caddy:v2.0.0)   printf 'sha256:prev_caddy' ;;
                    *) return 1 ;;
                esac
                ;;
            images)
                cat <<'IMGS'
ghcr.io/o/bndsphere-backend cur_backend
ghcr.io/o/bndsphere-backend prev_backend
ghcr.io/o/bndsphere-backend stale_backend
ghcr.io/o/bndsphere-backend inuse_backend
ghcr.io/o/bndsphere-caddy cur_caddy
ghcr.io/o/bndsphere-caddy prev_caddy
ghcr.io/o/bndsphere-caddy stale_caddy
ghcr.io/o/bndsphere-backend-staging lookalike_id
otherorg/unrelated-app unrelated_id
IMGS
                ;;
            rmi)
                shift
                printf '%s\n' "$1" >> "$_rt_rmi_log"
                # Simulate the daemon refusing to remove an image still in
                # use by a running container.
                [ "$1" = "inuse_backend" ] && return 1
                return 0
                ;;
        esac
    }
    prune_superseded_images
)
_rt_run
_rt_deleted=$(cat "$_rt_rmi_log")

assert_ok "a genuinely superseded backend digest is selected for deletion (positive control)" \
    sh -c "printf '%s' \"\$1\" | grep -qx stale_backend" _ "$_rt_deleted"
assert_ok "a genuinely superseded caddy digest is selected for deletion (positive control, proves the caddy repo is actually wired in, not just named)" \
    sh -c "printf '%s' \"\$1\" | grep -qx stale_caddy" _ "$_rt_deleted"
assert_fail "the current backend digest is never selected" \
    sh -c "printf '%s' \"\$1\" | grep -qx cur_backend" _ "$_rt_deleted"
assert_fail "the previous backend digest is never selected" \
    sh -c "printf '%s' \"\$1\" | grep -qx prev_backend" _ "$_rt_deleted"
assert_fail "the current caddy digest is never selected" \
    sh -c "printf '%s' \"\$1\" | grep -qx cur_caddy" _ "$_rt_deleted"
assert_fail "the previous caddy digest is never selected" \
    sh -c "printf '%s' \"\$1\" | grep -qx prev_caddy" _ "$_rt_deleted"
assert_fail "a same-family lookalike repo is never enumerated or selected" \
    sh -c "printf '%s' \"\$1\" | grep -qx lookalike_id" _ "$_rt_deleted"
assert_fail "an unrelated repository is never enumerated or selected" \
    sh -c "printf '%s' \"\$1\" | grep -qx unrelated_id" _ "$_rt_deleted"
assert_ok "an in-use image is attempted (not silently ignored) but the delete is left to the daemon's own refusal" \
    sh -c "printf '%s' \"\$1\" | grep -qx inuse_backend" _ "$_rt_deleted"
assert_ok "an in-use image that the daemon refuses to remove is logged as skipped" \
    grep -q "skipped in-use image ghcr.io/o/bndsphere-backend inuse_backend" \
        "$STATUS_DIR/update.log"
assert_ok "a superseded image that the daemon removes is logged as removed" \
    grep -q "removed superseded image ghcr.io/o/bndsphere-backend stale_backend" \
        "$STATUS_DIR/update.log"

rm -f "$_rt_rmi_log"
rm -rf "$PDR" "$STATUS_DIR"

printf '\n%s passed, %s failed\n' "$PASSES" "$FAILURES"
[ "$FAILURES" -eq 0 ]
