#!/bin/sh
# Artifact acquisition: read the release manifest, pull the images it pins.
#
# VERIFICATION IS THE DIGEST. The manifest records each image as
# repo@sha256:..., and the Docker daemon rejects any content whose digest does
# not match what was asked for — so the registry cannot serve different bytes
# than the release named, and nothing needs to be checked after the fact.
#
# This deliberately replaced a tarball + SHA256SUMS + post-load digest check.
# That scheme could only ever detect download corruption: the sums file
# travelled beside the artifact it vouched for, over the same channel, from
# the same release, so anything able to replace one could replace both. It
# bought no authenticity, and it cost three downloads, a docker load, and a
# re-inspection to get less than content addressing gives for free.

GITHUB_REPO="${GITHUB_REPO:-colinxu2020/BNDSphere}"
WORK_DIR="${WORK_DIR:-/tmp/bndsphere-deploy}"

ASSET_MANIFEST="release-manifest.json"
ASSET_COMPOSE="docker-compose.yml"

asset_url() {
    printf 'https://github.com/%s/releases/download/%s/%s' \
        "$GITHUB_REPO" "$1" "$2"
}

# Download to a temp name and rename only on success, so an interrupted
# transfer can never be mistaken for a complete file.
download_asset() {
    _version=$1; _name=$2; _dest="$WORK_DIR/$_name"
    mkdir -p "$WORK_DIR"
    rm -f "$_dest" "$_dest.part"
    curl -fsSL --retry 3 --retry-delay 2 --max-time 300 \
        -o "$_dest.part" "$(asset_url "$_version" "$_name")" || {
            rm -f "$_dest.part"
            return 1
        }
    mv -f "$_dest.part" "$_dest"
}

fetch_manifest() {
    download_asset "$1" "$ASSET_MANIFEST" || return 1
    jq -e . "$WORK_DIR/$ASSET_MANIFEST" >/dev/null 2>&1 || {
        log "$ASSET_MANIFEST is not valid JSON"
        return 1
    }
    printf '%s/%s' "$WORK_DIR" "$ASSET_MANIFEST"
}

# The release's own compose file. Staged in WORK_DIR, not installed: the
# migration runs against it while the OLD file is still the installed one, so
# a failed migration leaves nothing on the host changed.
fetch_compose() {
    download_asset "$1" "$ASSET_COMPOSE" || return 1
    printf '%s/%s' "$WORK_DIR" "$ASSET_COMPOSE"
}

manifest_field() {
    jq -r "$2 // empty" "$1"
}

acquire_images() {
    _version=$1
    rm -rf "$WORK_DIR"; mkdir -p "$WORK_DIR"

    _manifest=$(fetch_manifest "$_version") || {
        log "could not fetch $ASSET_MANIFEST for $_version"
        return 1
    }

    for _component in backend caddy; do
        _ref=$(manifest_field "$_manifest" ".images.${_component}.ref")
        # A tag-only ref would make the pull below mutable and unverified,
        # which is the entire property this depends on. Refuse it rather than
        # silently pulling whatever the tag points at today.
        case "$_ref" in
            *@sha256:*) ;;
            *)
                log "images.${_component}.ref is not digest-pinned: '$_ref'"
                return 1
                ;;
        esac
        log "pulling $_ref"
        docker pull "$_ref" >/dev/null 2>&1 || {
            log "could not pull $_ref"
            return 1
        }
    done

    printf '%s' "$_manifest"
    return 0
}
