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

printf '\n%s passed, %s failed\n' "$PASSES" "$FAILURES"
[ "$FAILURES" -eq 0 ]
