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
. /updater/lib/validate.sh

COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-bndsphere}"
POLL_INTERVAL="${POLL_INTERVAL:-5}"

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

# Replaced in Tasks 4-8.
run_update()             { log "run_update stub: $1"; state_terminal failed not_implemented "stub"; }
run_rollback()           { log "run_rollback stub: $1 ($2)"; state_terminal failed not_implemented "stub"; }
recover_if_interrupted() { :; }

main "$@"
