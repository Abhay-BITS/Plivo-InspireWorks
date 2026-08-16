"""Plivo V3 webhook signature validation.

Validated against the exact URL Plivo called, which is PUBLIC_BASE_URL,
not whatever the ASGI request object thinks its own URL is. Behind a
tunnel or a reverse proxy those two disagree, and building the check from
the request would fail every time. The SDK helper does the HMAC work;
this module only supplies the right inputs.
"""

from fastapi import Request
from plivo.utils import validate_v3_signature

SIGNATURE_HEADER = "X-Plivo-Signature-V3"
NONCE_HEADER = "X-Plivo-Signature-V3-Nonce"


async def is_valid_request(request: Request, auth_token: str, absolute_url: str) -> bool:
    signature = request.headers.get(SIGNATURE_HEADER)
    nonce = request.headers.get(NONCE_HEADER)
    if not signature or not nonce:
        return False

    form = await request.form()
    params = {key: str(value) for key, value in form.items()}

    return bool(
        validate_v3_signature(
            method="POST",
            uri=absolute_url,
            nonce=nonce,
            auth_token=auth_token,
            v3_signature=signature,
            params=params,
        )
    )
