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
#
# NO status filter, deliberately: a one-off that is still RUNNING is the
# dangerous case, not the dead one. `--rm` only removes the container when it
# exits, so a migration whose client disconnected keeps going, stays invisible
# to a `status=exited` filter, and is never reaped — and the next deploy then
# starts a SECOND `alembic upgrade head` concurrently against the same
# database. We have already decided not to resume, so killing it is the
# correct reconciliation; `rm -f` covers running and exited alike.
oneoff_ids() {
    docker ps -aq \
        --filter "label=com.docker.compose.project=$COMPOSE_PROJECT_NAME" \
        --filter "label=com.docker.compose.oneoff=True" 2>/dev/null
}

reap_orphans() {
    _ids=$(oneoff_ids)
    [ -n "$_ids" ] || return 0
    # shellcheck disable=SC2086 # deliberate word splitting over an id list
    docker rm -f $_ids >/dev/null 2>&1 || true
    # Verify, never assume. Discarding the removal status was harmless while
    # this only matched exited containers; now that it matches RUNNING ones it
    # is the whole hazard -- recovery would log a clean reap while an
    # interrupted migration is still live, and the next deploy would start a
    # second `alembic upgrade head` beside it.
    _left=$(oneoff_ids)
    if [ -n "$_left" ]; then
        log "orphaned one-off containers could not be removed: $_left"
        return 1
    fi
    log "reaped orphaned one-off containers"
}

recover_if_interrupted() {
    _stage=$(state_get stage)
    [ -n "$_stage" ] || return 0
    is_terminal "$_stage" && return 0

    log "updater restarted while in stage '$_stage' — marking interrupted, not resuming"

    _reaped=0
    reap_orphans || _reaped=1
    release_lock

    # Mark the request processed so a crash can never cause a silent re-run.
    state_set interrupted_stage "$_stage" \
        last_processed_request_id "$(state_get request_id)" || true

    # A surviving one-off is not just an untidy state to report -- it may be a
    # migration still writing to the database. Refuse to hand control back to
    # main(), which would otherwise go on to start a deploy beside it.
    if [ "$_reaped" -ne 0 ]; then
        state_terminal failed orphan_reap_failed \
            "an orphaned one-off container is still present; refusing to start new work"
        return 1
    fi

    state_terminal failed interrupted \
        "updater restarted during '$_stage'; no work was resumed"
}
