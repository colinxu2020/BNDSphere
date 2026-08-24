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

TERMINAL_STAGES="idle success rollback_success failed"

state_file()    { printf '%s/state.json' "$STATUS_DIR"; }
deployed_file() { printf '%s/deployed.json' "$STATUS_DIR"; }
lock_file()     { printf '%s/updater.lock' "$STATUS_DIR"; }

state_init() {
    mkdir -p "$STATUS_DIR"
    # Test validity, not mere existence: a truncated or corrupt file must be
    # replaced, or the sidecar boots blank forever -- the exact failure this
    # guard exists to prevent.
    [ -f "$(state_file)" ] && jq -e . "$(state_file)" >/dev/null 2>&1 && return 0
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

    # An unpaired trailing key would otherwise be dropped silently. Tasks 4-8
    # call this constantly on the critical path, so a typo losing a field
    # must fail loudly instead.
    [ "$(( $# % 2 ))" -eq 0 ] || {
        log "state_set: odd argument count ($#), refusing"
        return 1
    }

    # Refuse to write when the read or any merge step failed or produced
    # nothing: a swallowed failure here would otherwise truncate state.json
    # to empty, exactly what the merge-not-replace contract forbids.
    _json=$(cat "$_file") && [ -n "$_json" ] || {
        log "state_set: $_file missing or unreadable, refusing to write"
        return 1
    }

    while [ "$#" -ge 2 ]; do
        _json=$(printf '%s' "$_json" \
            | jq -c --arg k "$1" --arg v "$2" '.[$k] = $v') && [ -n "$_json" ] || {
            log "state_set: jq failed merging key '$1', refusing to write"
            return 1
        }
        shift 2
    done

    _json=$(printf '%s' "$_json" | jq -c --arg t "$_now" '.updated_at = $t') \
        && [ -n "$_json" ] || {
        log "state_set: jq failed stamping updated_at, refusing to write"
        return 1
    }

    printf '%s' "$_json" | atomic_write "$_file"
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
