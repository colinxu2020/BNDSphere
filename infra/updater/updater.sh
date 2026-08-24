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
. /updater/lib/artifact.sh
. /updater/lib/deploy.sh

COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-bndsphere}"
POLL_INTERVAL="${POLL_INTERVAL:-5}"

main() {
    # Installed before ANY other work, including validate_startup. This
    # process runs as PID 1, and the kernel does not queue signals with
    # default disposition for PID 1 -- it drops them. A TERM arriving before
    # a trap is installed is simply lost, and nothing later in the function
    # can ever catch up on it. release_lock (from lib/state.sh, sourced at
    # the top of this file) is already defined by the time main() is ever
    # called, so it is safe to trap here regardless of where in main() this
    # sits.
    #
    # A signal trap that returns normally RESUMES the interrupted code in
    # POSIX sh (busybox ash) -- it does not exit. TERM/INT must therefore
    # exit explicitly (143 = 128+SIGTERM, 130 = 128+SIGINT), or the sidecar
    # ignores shutdown signals, `docker stop` burns the full grace period
    # into a SIGKILL, and the lock is freed while the loop keeps polling and
    # can still dispatch a deploy after being told to stop. release_lock is
    # `rm -rf`, so it tolerates the EXIT trap running it again afterward.
    trap 'release_lock; exit 143' TERM
    trap 'release_lock; exit 130' INT
    trap release_lock EXIT

    validate_startup
    state_init

    # One process runs per container: any lock directory found here was left
    # by a process that no longer exists. A restart reuses pids, so judging
    # staleness from the recorded pid is unsafe -- clearing unconditionally,
    # before anything can acquire the lock (the poll loop below), is correct
    # here.
    release_lock

    log "updater started (project=$COMPOSE_PROJECT_NAME dir=$COMPOSE_PROJECT_DIR)"

    # Recovery runs before the first poll (Task 8 fills this in).
    recover_if_interrupted

    while true; do
        handle_request
        # A foreground `sleep` blocks trap delivery until it returns: POSIX
        # shells only run a pending trap once the current foreground command
        # completes, so a plain `sleep "$POLL_INTERVAL"` would leave SIGTERM
        # sitting unhandled for up to a whole poll interval. Backgrounding
        # the sleep and waiting on it explicitly lets the trap interrupt
        # `wait` immediately instead.
        sleep "$POLL_INTERVAL" &
        wait "$!"
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

# Replaced in Tasks 6-8.
run_rollback()           { log "run_rollback stub: $1 ($2)"; state_terminal failed not_implemented "stub"; }
recover_if_interrupted() { :; }

# UPDATER_NO_MAIN lets the self-check source this file to get its functions
# (handle_request, the stubs) without launching the infinite poll loop.
[ "${UPDATER_NO_MAIN:-}" ] || main "$@"
