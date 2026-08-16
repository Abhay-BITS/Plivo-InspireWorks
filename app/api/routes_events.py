"""Hangup, dial status, and fallback callbacks. These are Plivo event
notifications, not menu turns, so most of them acknowledge with a plain
200 rather than a GetDigits document. fallback_url is the one exception:
Plivo treats its response as call instructions if answer_url never
responded, so it has to be valid XML, not an event acknowledgement.
"""

from fastapi import APIRouter, Depends, Request, Response

from app.api.deps import get_service, get_settings, get_urls
from app.calls.service import CallService
from app.config import Settings
from app.observability.logging import bind_call_uuid, get_logger
from app.telephony.security import is_valid_request
from app.telephony.xml_builder import error_document
from app.urls import CallbackUrls

router = APIRouter(prefix="/events", tags=["events"])
logger = get_logger(__name__)


async def _verify(request: Request, settings: Settings, absolute_url: str) -> bool:
    if not settings.verify_plivo_signature:
        return True
    return await is_valid_request(request, settings.plivo_auth_token, absolute_url)


@router.post("/hangup")
async def hangup(
    request: Request,
    service: CallService = Depends(get_service),
    settings: Settings = Depends(get_settings),
    urls: CallbackUrls = Depends(get_urls),
) -> Response:
    if not await _verify(request, settings, urls.hangup):
        return Response(status_code=403)

    form = await request.form()
    call_uuid = str(form.get("CallUUID", ""))
    bind_call_uuid(call_uuid)
    hangup_cause = str(form.get("HangupCause", "unknown"))

    await service.finalize_call(call_uuid, hangup_cause)
    return Response(status_code=200)


@router.post("/dial-status")
async def dial_status(
    request: Request,
    service: CallService = Depends(get_service),
    settings: Settings = Depends(get_settings),
    urls: CallbackUrls = Depends(get_urls),
) -> Response:
    if not await _verify(request, settings, urls.dial_status):
        return Response(status_code=403)

    form = await request.form()
    call_uuid = str(form.get("CallUUID", ""))
    bind_call_uuid(call_uuid)
    logger.info("dial status: %s", form.get("DialStatus", "unknown"))
    return Response(status_code=200)


@router.post("/fallback")
async def fallback(
    request: Request,
    settings: Settings = Depends(get_settings),
    urls: CallbackUrls = Depends(get_urls),
) -> Response:
    if not await _verify(request, settings, urls.fallback):
        return Response(status_code=403)

    form = await request.form()
    call_uuid = str(form.get("CallUUID", ""))
    bind_call_uuid(call_uuid)
    logger.warning("answer_url did not respond in time, serving fallback apology")
    return Response(content=error_document(), media_type="application/xml")
