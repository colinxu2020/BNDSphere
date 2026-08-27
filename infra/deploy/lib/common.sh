#!/bin/sh
# Shared primitives: logging, atomic writes, input validation, preflight.

# ---------------------------------------------------------------- logging

# stdout IS the log. This runs as a GitHub Actions step, which captures,
# timestamps and retains it, and the run page is what an operator opens. The
# sidecar kept its own rotated update.log because nothing was watching a
# daemon; a job does not need one.
log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1"; }

die() {
    printf 'FATAL: %s\n' "$1" >&2
    exit 1
}

# ------------------------------------------------------------ atomic write

# versions.env is written through this, always. The job can be cancelled at
# any instant, including mid-deploy; a half-written versions.env would make
# the stack unstartable by ANY means, rollback included. Partial files must be
# unobservable, not merely rare.
atomic_write() {
    _dest=$1
    _tmp="${_dest}.tmp.$$"
    cat > "$_tmp" || { rm -f "$_tmp"; return 1; }
    # rename(2) within one filesystem is atomic: a reader sees the old
    # complete file or the new complete file, never a splice of the two.
    mv -f "$_tmp" "$_dest"
}

# -------------------------------------------------------------- validation

# The trust boundary. The version reaches release-asset URLs and Docker tags,
# and arrives from workflow_dispatch, so it is attacker-controlled by anyone
# holding a token with actions:write. Allow-list only.
#
# No '+' build metadata: release.yml uses the version verbatim as a Docker
# tag, and Docker's reference grammar has no '+', so such a release cannot be
# built in the first place.
VERSION_RE='^v?[0-9]+(\.[0-9]+){0,3}(-[0-9A-Za-z.-]+)?$'
VERSION_MAX_LEN=64

# grep -Eq matches per line, so an embedded newline could smuggle a second
# line past an anchored pattern. Reject multi-line input outright first.
_is_single_line() {
    [ "$(printf '%s' "${1:-}" | wc -l)" -eq 0 ]
}

valid_version() {
    _v=${1:-}
    [ -n "$_v" ] || return 1
    [ "${#_v}" -le "$VERSION_MAX_LEN" ] || return 1
    _is_single_line "$_v" || return 1
    # printf '%s' (not echo) so a leading '-' is data, never an option.
    printf '%s' "$_v" | grep -Eq "$VERSION_RE"
}

# --------------------------------------------------------------- preflight

validate_startup() {
    [ -n "${COMPOSE_PROJECT_DIR:-}" ] \
        || die "COMPOSE_PROJECT_DIR is unset. It must be the absolute path of the deployment on this host."

    case "$COMPOSE_PROJECT_DIR" in
        /*) ;;
        *) die "COMPOSE_PROJECT_DIR must be absolute, got: $COMPOSE_PROJECT_DIR" ;;
    esac

    # Compose bind-mount sources (./secrets/*) are resolved by the Docker
    # daemon against this directory. A wrong value makes secrets resolve to
    # nothing and the stack comes up broken in a way that looks like an
    # application bug, so check before anything is recreated.
    [ -d "$COMPOSE_PROJECT_DIR" ] \
        || die "COMPOSE_PROJECT_DIR does not exist at $COMPOSE_PROJECT_DIR"
    [ -f "$COMPOSE_PROJECT_DIR/docker-compose.yml" ] \
        || die "No docker-compose.yml in $COMPOSE_PROJECT_DIR"
    [ -d "$COMPOSE_PROJECT_DIR/secrets" ] \
        || die "No secrets/ in $COMPOSE_PROJECT_DIR"
    # The compose wrapper passes this explicitly. Missing, it would be the
    # deployment's whole interpolation environment going absent: CORS_ORIGIN
    # and OSS_* blank, CADDY_PORT silently back to 80.
    [ -f "$COMPOSE_PROJECT_DIR/.env" ] \
        || die "No .env in $COMPOSE_PROJECT_DIR. Run deploy/bootstrap.sh first."
    return 0
}
