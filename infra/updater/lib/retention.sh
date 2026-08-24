#!/bin/sh
# Image retention -- deliberately the narrowest thing that works.
#
# Current AND previous must always survive: rollback restores the previous
# images from the local store, so this is a correctness requirement, not an
# optimisation.
#
# There is no bulk deletion here and there must never be. The host may run
# unrelated workloads. Accumulating a few hundred MB of superseded images is a
# far cheaper mistake than deleting an image someone needed (spec section
# 18.3). Only the two application repositories below are ever named; the
# database's images are entirely out of scope and never enumerated.

RETAINED_REPOS="bndsphere-backend bndsphere-caddy"

# is_protected DIGEST CURRENT PREVIOUS
is_protected() {
    _digest=$1; _current=$2; _previous=$3
    # Fail open: with nothing recorded to protect, protect everything.
    [ -z "$_current" ] && [ -z "$_previous" ] && return 0
    [ "$_digest" = "$_current" ] && return 0
    [ "$_digest" = "$_previous" ] && return 0
    return 1
}

# image_id REF -- resolves a ref (tag) to a local image ID, normalized to the
# bare-hex form `docker images --no-trunc` prints (no "sha256:" prefix), so
# the two can be compared with plain string equality. `docker image inspect`
# and `docker images` do not agree on that prefix; comparing them unnormalized
# would make every current/previous match silently fail.
image_id() {
    _iid=$(docker image inspect --format '{{.Id}}' "$1" 2>/dev/null)
    printf '%s' "${_iid#sha256:}"
}

prune_superseded_images() {
    for _repo in $RETAINED_REPOS; do
        case "$_repo" in
            bndsphere-backend)
                _cur=$(deployed_get current_backend_ref)
                _prev=$(deployed_get previous_backend_ref)
                ;;
            bndsphere-caddy)
                _cur=$(deployed_get current_caddy_ref)
                _prev=$(deployed_get previous_caddy_ref)
                ;;
        esac
        _cur_id=$(image_id "$_cur")
        _prev_id=$(image_id "$_prev")

        # docker has no repository filter that survives a registry-host
        # prefix, so this lists every local image and keeps only the rows
        # whose repository IS this application repo -- either the whole
        # name, or the final path segment of a registry-qualified one. A
        # substring test would also catch a merely similar name
        # ("bndsphere-backend-staging") that is not ours to touch.
        docker images --no-trunc --format '{{.Repository}} {{.ID}}' \
            | while read -r _repo_name _id; do
                case "$_repo_name" in
                    "$_repo" | *"/$_repo") ;;
                    *) continue ;;
                esac
                if is_protected "$_id" "$_cur_id" "$_prev_id"; then
                    continue
                fi
                # No force flag on the delete call: an image the daemon
                # reports as in use is skipped, never yanked out from under a
                # running container.
                if docker rmi "$_id" >/dev/null 2>&1; then
                    log "removed superseded image $_repo_name $_id"
                else
                    log "skipped in-use image $_repo_name $_id"
                fi
            done
    done
}
