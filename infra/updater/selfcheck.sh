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

printf '\n%s passed, %s failed\n' "$PASSES" "$FAILURES"
[ "$FAILURES" -eq 0 ]
