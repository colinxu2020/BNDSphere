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
