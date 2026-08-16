"""Answer and action webhooks. Every handler does exactly four things:
validate the signature, parse the form, call service.handle_webhook,
return XML with media_type="application/xml". If a handler here grows an
`if digits == "1"`, that logic belongs in app.ivr.machine instead.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.api.deps import get_service, get_settings, get_urls
from app.calls.service import CallService
from app.config import Settings
from app.ivr.machine import InputEvent, InputKind
from app.observability.logging import bind_call_uuid, get_logger
from app.telephony.security import is_valid_request
from app.urls import CallbackUrls

router = APIRouter(prefix="/voice", tags=["voice"])
logger = get_logger(__name__)

XML_MEDIA_TYPE = "application/xml"


async def _verify_signature(request: Request, settings: Settings, absolute_url: str) -> None:
    if not settings.verify_plivo_signature:
        return
    if not await is_valid_request(request, settings.plivo_auth_token, absolute_url):
        logger.warning("rejected webhook with invalid plivo signature")
        raise HTTPException(status_code=403, detail="invalid signature")


def _xml(content: str) -> Response:
    return Response(content=content, media_type=XML_MEDIA_TYPE)


@router.post("/answer")
async def answer(
    request: Request,
    service: CallService = Depends(get_service),
    settings: Settings = Depends(get_settings),
    urls: CallbackUrls = Depends(get_urls),
) -> Response:
    await _verify_signature(request, settings, urls.answer)
    form = await request.form()
    call_uuid = str(form.get("CallUUID", ""))
    bind_call_uuid(call_uuid)

    result = await service.serve_otp_prompt(
        call_uuid, "/voice/answer", str(form.get("To", "unknown"))
    )
    return _xml(result.xml)


@router.post("/otp")
async def otp(
    request: Request,
    service: CallService = Depends(get_service),
    settings: Settings = Depends(get_settings),
    urls: CallbackUrls = Depends(get_urls),
) -> Response:
    await _verify_signature(request, settings, urls.otp)
    form = await request.form()
    call_uuid = str(form.get("CallUUID", ""))
    bind_call_uuid(call_uuid)
    digits = str(form.get("Digits", ""))

    result = await service.handle_webhook(
        endpoint="/voice/otp",
        call_uuid=call_uuid,
        event=InputEvent(InputKind.DIGITS, digits),
    )
    return _xml(result.xml)


@router.post("/otp-timeout")
async def otp_timeout(
    request: Request,
    service: CallService = Depends(get_service),
    settings: Settings = Depends(get_settings),
    urls: CallbackUrls = Depends(get_urls),
) -> Response:
    await _verify_signature(request, settings, urls.otp_timeout)
    form = await request.form()
    call_uuid = str(form.get("CallUUID", ""))
    bind_call_uuid(call_uuid)

    result = await service.handle_webhook(
        endpoint="/voice/otp-timeout",
        call_uuid=call_uuid,
        event=InputEvent(InputKind.NO_INPUT),
    )
    return _xml(result.xml)


@router.post("/language")
async def language(
    request: Request,
    service: CallService = Depends(get_service),
    settings: Settings = Depends(get_settings),
    urls: CallbackUrls = Depends(get_urls),
) -> Response:
    await _verify_signature(request, settings, urls.language)
    form = await request.form()
    call_uuid = str(form.get("CallUUID", ""))
    bind_call_uuid(call_uuid)
    digits = str(form.get("Digits", ""))

    session = await service.get_session(call_uuid)
    if session is None or not session.is_authenticated:
        result = await service.serve_otp_prompt(call_uuid, "/voice/language")
        return _xml(result.xml)

    result = await service.handle_webhook(
        endpoint="/voice/language",
        call_uuid=call_uuid,
        event=InputEvent(InputKind.DIGITS, digits),
    )
    return _xml(result.xml)


@router.post("/language-timeout")
async def language_timeout(
    request: Request,
    service: CallService = Depends(get_service),
    settings: Settings = Depends(get_settings),
    urls: CallbackUrls = Depends(get_urls),
) -> Response:
    await _verify_signature(request, settings, urls.language_timeout)
    form = await request.form()
    call_uuid = str(form.get("CallUUID", ""))
    bind_call_uuid(call_uuid)

    result = await service.handle_webhook(
        endpoint="/voice/language-timeout",
        call_uuid=call_uuid,
        event=InputEvent(InputKind.NO_INPUT),
    )
    return _xml(result.xml)


@router.post("/action")
async def action(
    request: Request,
    service: CallService = Depends(get_service),
    settings: Settings = Depends(get_settings),
    urls: CallbackUrls = Depends(get_urls),
) -> Response:
    await _verify_signature(request, settings, urls.action)
    form = await request.form()
    call_uuid = str(form.get("CallUUID", ""))
    bind_call_uuid(call_uuid)
    digits = str(form.get("Digits", ""))

    result = await service.handle_webhook(
        endpoint="/voice/action",
        call_uuid=call_uuid,
        event=InputEvent(InputKind.DIGITS, digits),
    )
    return _xml(result.xml)


@router.post("/action-timeout")
async def action_timeout(
    request: Request,
    service: CallService = Depends(get_service),
    settings: Settings = Depends(get_settings),
    urls: CallbackUrls = Depends(get_urls),
) -> Response:
    await _verify_signature(request, settings, urls.action_timeout)
    form = await request.form()
    call_uuid = str(form.get("CallUUID", ""))
    bind_call_uuid(call_uuid)

    result = await service.handle_webhook(
        endpoint="/voice/action-timeout",
        call_uuid=call_uuid,
        event=InputEvent(InputKind.NO_INPUT),
    )
    return _xml(result.xml)


@router.post("/action-menu")
async def action_menu(
    request: Request,
    service: CallService = Depends(get_service),
    settings: Settings = Depends(get_settings),
    urls: CallbackUrls = Depends(get_urls),
) -> Response:
    await _verify_signature(request, settings, urls.action_menu)
    form = await request.form()
    call_uuid = str(form.get("CallUUID", ""))
    bind_call_uuid(call_uuid)

    result = await service.handle_webhook(
        endpoint="/voice/action-menu",
        call_uuid=call_uuid,
        event=InputEvent(InputKind.ACTION_DONE),
    )
    return _xml(result.xml)
