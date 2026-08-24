#!/bin/sh
# The trust boundary. Everything downstream assumes these rejected anything
# dangerous, so these functions are deliberately strict and allow-list only.

VERSION_RE='^v?[0-9]+(\.[0-9]+){0,3}([-+][0-9A-Za-z.-]+)?$'
UUID_RE='^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
VERSION_MAX_LEN=64

# grep -Eq matches per line, so an embedded newline could smuggle a second
# line past a pattern's anchors. Any caller anchoring a pattern with grep
# must reject multi-line input outright first.
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

valid_action() {
    case "${1:-}" in
        update|rollback) return 0 ;;
        *) return 1 ;;
    esac
}

valid_uuid() {
    _u=${1:-}
    _is_single_line "$_u" || return 1
    printf '%s' "$_u" | grep -Eq "$UUID_RE"
}

# Strip a leading 'v' and compare dotted numeric segments, longest-wins.
# Pre-release suffixes are ignored for ordering: the updater only needs "is
# this different and newer", and full semver precedence is not worth the shell.
_version_key() {
    printf '%s' "${1#v}" | sed 's/[-+].*$//'
}

version_newer() {
    _cand=$(_version_key "${1:-}")
    _curr=$(_version_key "${2:-}")

    # Anything non-numeric (e.g. the 'dev' default) is never "newer".
    printf '%s' "$_cand" | grep -Eq '^[0-9]+(\.[0-9]+)*$' || return 1
    printf '%s' "$_curr" | grep -Eq '^[0-9]+(\.[0-9]+)*$' || return 0

    _i=1
    while [ "$_i" -le 4 ]; do
        _a=$(printf '%s' "$_cand" | cut -d. -f"$_i"); _a=${_a:-0}
        _b=$(printf '%s' "$_curr" | cut -d. -f"$_i"); _b=${_b:-0}
        [ "$_a" -gt "$_b" ] && return 0
        [ "$_a" -lt "$_b" ] && return 1
        _i=$((_i + 1))
    done
    return 1   # equal is not newer
}

# Echo "id<TAB>action<TAB>version" or fail. Unknown fields are ignored: the
# request schema is closed, so a compromised backend cannot widen it (spec §8).
read_request() {
    _path=${1:-}
    [ -f "$_path" ] || return 1

    _json=$(cat "$_path") || return 1
    printf '%s' "$_json" | jq -e . >/dev/null 2>&1 || return 1

    _id=$(printf '%s' "$_json" | jq -r '.id // empty')
    _action=$(printf '%s' "$_json" | jq -r '.action // empty')
    _version=$(printf '%s' "$_json" | jq -r '.version // empty')

    valid_uuid "$_id" || return 1
    valid_action "$_action" || return 1
    valid_version "$_version" || return 1

    printf '%s\t%s\t%s\n' "$_id" "$_action" "$_version"
}
