from urllib.parse import urlsplit

from fastapi import Request

from app.core.settings import web_settings
from app.services.errors import UntrustedOriginError


def ensure_trusted_origin(request: Request) -> None:
    """Reject foreign browser writes while preserving explicit API clients.

    SameSite does not cover sibling origins on the same site, or a foreign
    login response setting a new cookie. Origin wins over Referer; neither
    a null origin nor an untrusted one can fall back to a trusted Referer.

    ``CORS_ORIGIN=*`` is accepted as a match-all, a configuration the settings
    validator confines to debug: the local Vite setup proxies API calls to the
    backend while preserving the browser's Origin, so no fixed trusted list
    can match it.
    """
    configured = web_settings().cors_origin
    wildcard = configured.strip() == "*"
    trusted = {str(request.base_url).rstrip("/"), configured}
    origin = request.headers.get("origin")
    if origin is not None:
        if origin in {"null", "*"} or (not wildcard and origin not in trusted):
            raise UntrustedOriginError
        return
    referer = request.headers.get("referer")
    if referer is not None:
        try:
            parsed = urlsplit(referer)
            referer_origin = f"{parsed.scheme}://{parsed.netloc}"
        except ValueError:
            referer_origin = ""
        if not wildcard and referer_origin not in trusted:
            raise UntrustedOriginError
        return
    if request.headers.get("sec-fetch-site") in {"cross-site", "same-site"}:
        raise UntrustedOriginError
    # Non-browser API clients may have neither origin header nor Fetch Metadata.
