import hashlib
import hmac
import json
import logging
import time
from datetime import UTC, datetime
from typing import Any, Final

import httpx

from app.core.settings import SmsSettings, sms_settings, web_settings
from app.services.errors import NotificationChannelUnavailableError

logger = logging.getLogger(__name__)

_HOST: Final[str] = "sms.tencentcloudapi.com"
_SERVICE: Final[str] = "sms"
_ACTION: Final[str] = "SendSms"
_VERSION: Final[str] = "2021-01-11"
_ALGORITHM: Final[str] = "TC3-HMAC-SHA256"
_CONTENT_TYPE: Final[str] = "application/json; charset=utf-8"
# Lowercase and sorted, because that is the form the signature covers.
_SIGNED_HEADER_FIELDS: Final[dict[str, str]] = {
    "content-type": _CONTENT_TYPE,
    "host": _HOST,
    "x-tc-action": _ACTION.lower(),
}
_SIGNED_HEADERS: Final[str] = ";".join(_SIGNED_HEADER_FIELDS)
_TIMEOUT_SECONDS: Final[float] = 10.0


def _hmac_sha256(key: bytes, message: str) -> bytes:
    return hmac.new(key, message.encode(), hashlib.sha256).digest()


def canonical_request(headers: dict[str, str], payload: str) -> str:
    """Tencent's canonical form of a POST to ``/`` with an empty query string.

    Split out from ``build_authorization`` so it can be checked against the
    worked example in Tencent's own signature documentation, which publishes
    the hash of this string but masks the key that would let the finished
    signature be reproduced. Assembling this block is the part that is easy
    to get subtly wrong; the HMAC chain after it is not.

    ``headers`` must already be lowercase and in sorted order.
    """
    canonical_headers = "".join(f"{name}:{value}\n" for name, value in headers.items())
    return "\n".join(
        [
            "POST",
            "/",
            "",
            canonical_headers,
            ";".join(headers),
            hashlib.sha256(payload.encode()).hexdigest(),
        ],
    )


def build_authorization(
    secret_id: str,
    secret_key: str,
    payload: str,
    timestamp: int,
) -> str:
    """Sign a SendSms request with TC3-HMAC-SHA256.

    Tencent's scheme, implemented here rather than pulled in as an SDK: it is
    a fixed recipe over ``hmac``/``hashlib``, and the official package brings
    a synchronous HTTP client along with it for the one call this codebase
    makes.

    ``payload`` must be the exact bytes that will be sent as the body — the
    signature covers its digest, so re-serializing the dict for the request
    would produce a different hash and a 401 from the API.
    """
    date = datetime.fromtimestamp(timestamp, UTC).strftime("%Y-%m-%d")

    request = canonical_request(_SIGNED_HEADER_FIELDS, payload)
    credential_scope = f"{date}/{_SERVICE}/tc3_request"
    string_to_sign = "\n".join(
        [
            _ALGORITHM,
            str(timestamp),
            credential_scope,
            hashlib.sha256(request.encode()).hexdigest(),
        ],
    )

    secret_date = _hmac_sha256(f"TC3{secret_key}".encode(), date)
    secret_service = _hmac_sha256(secret_date, _SERVICE)
    secret_signing = _hmac_sha256(secret_service, "tc3_request")
    signature = hmac.new(
        secret_signing,
        string_to_sign.encode(),
        hashlib.sha256,
    ).hexdigest()

    return (
        f"{_ALGORITHM} Credential={secret_id}/{credential_scope}, "
        f"SignedHeaders={_SIGNED_HEADERS}, Signature={signature}"
    )


def _raise_for_api_error(body: dict[str, Any], phone: str) -> None:
    """Turn Tencent's 200-with-an-error-body into an exception.

    The API answers HTTP 200 for business failures (bad signature, unapproved
    template, blocked number), so ``raise_for_status`` alone would report a
    message that never left the building as delivered.
    """
    response = body.get("Response", {})
    error = response.get("Error")
    if error:
        logger.error(
            "Tencent SMS rejected the request: %s %s",
            error.get("Code"),
            error.get("Message"),
        )
        raise NotificationChannelUnavailableError("sms")

    statuses = response.get("SendStatusSet") or []
    for status in statuses:
        if status.get("Code") != "Ok":
            logger.error(
                "Tencent SMS did not accept %s: %s %s",
                phone,
                status.get("Code"),
                status.get("Message"),
            )
            raise NotificationChannelUnavailableError("sms")
    if not statuses:
        logger.error("Tencent SMS returned no send status for %s", phone)
        raise NotificationChannelUnavailableError("sms")


class SmsSender:
    """Deliver verification codes through Tencent Cloud SMS."""

    async def send_code(self, phone: str, code: str, minutes: int) -> None:
        settings = sms_settings()
        if not settings.configured:
            if web_settings().debug:
                # Local development without credentials: the code goes to the
                # log so the flow is walkable without spending money.
                logger.warning(
                    "Tencent SMS not configured; verification code for %s is %s",
                    phone,
                    code,
                )
                return
            raise NotificationChannelUnavailableError("sms")

        await self._post(settings, phone, code, minutes)

    async def _post(
        self,
        settings: SmsSettings,
        phone: str,
        code: str,
        minutes: int,
    ) -> None:
        # Compact separators keep the signed string and the sent body
        # identical; any reformatting between the two invalidates the
        # signature.
        payload = json.dumps(
            {
                "PhoneNumberSet": [phone],
                "SmsSdkAppId": settings.tencent_sms_sdk_app_id,
                "SignName": settings.tencent_sms_sign_name,
                "TemplateId": settings.tencent_sms_template_id,
                # Template placeholders, in order: the code, then how long it
                # stays valid. The template registered in the Tencent console
                # must take these two parameters in this order.
                "TemplateParamSet": [code, str(minutes)],
            },
            separators=(",", ":"),
        )
        timestamp = int(time.time())
        headers = {
            "Authorization": build_authorization(
                settings.tencent_sms_secret_id,
                settings.tencent_sms_secret_key,
                payload,
                timestamp,
            ),
            "Content-Type": _CONTENT_TYPE,
            "Host": _HOST,
            "X-TC-Action": _ACTION,
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Version": _VERSION,
            "X-TC-Region": settings.tencent_sms_region,
        }

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as http:
                response = await http.post(
                    f"https://{_HOST}",
                    content=payload,
                    headers=headers,
                )
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as err:
            logger.exception("Tencent SMS request failed for %s", phone)
            raise NotificationChannelUnavailableError("sms") from err

        _raise_for_api_error(body, phone)
