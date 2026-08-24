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
