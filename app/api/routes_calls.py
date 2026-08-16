"""Outbound call trigger and the call listing the dashboard polls or
subscribes to. The Plivo client is mocked in tests, so this router is
the only place a real REST call to Plivo is ever made.
"""

from typing import Any

import phonenumbers
from fastapi import APIRouter, Depends, HTTPException
from phonenumbers import NumberParseException
from pydantic import BaseModel

from app.api.deps import get_plivo_client, get_service, get_settings
from app.calls.service import CallService
from app.config import Settings
from app.telephony.client import PlivoClient

router = APIRouter(prefix="/api/calls", tags=["calls"])


class PlaceCallRequest(BaseModel):
    to: str


class PlaceCallResponse(BaseModel):
    request_uuid: str
    to: str


class CallSummary(BaseModel):
    call_uuid: str
    to_number: str
    state: str
    locale: str | None
    otp_attempts: int
    is_authenticated: bool
    created_at: str
    ended_at: str | None


def _normalize_destination(raw: str) -> str:
    try:
        parsed = phonenumbers.parse(raw, None)
    except NumberParseException as exc:
        raise HTTPException(
            status_code=422,
            detail=(
                "That number could not be parsed. Include the country code, "
                "for example +919876543210."
            ),
        ) from exc

    if not phonenumbers.is_valid_number(parsed):
        raise HTTPException(
            status_code=422,
            detail=(
                "That number could not be parsed. Include the country code, "
                "for example +919876543210."
            ),
        )

    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def _to_summary(session: Any) -> CallSummary:
    return CallSummary(
        call_uuid=session.call_uuid,
        to_number=session.to_number,
        state=session.state.value,
        locale=session.locale.value if session.locale else None,
        otp_attempts=session.otp_attempts,
        is_authenticated=session.is_authenticated,
        created_at=session.created_at.isoformat(),
        ended_at=session.ended_at.isoformat() if session.ended_at else None,
    )


@router.post("", response_model=PlaceCallResponse, status_code=201)
async def place_call(
    body: PlaceCallRequest,
    service: CallService = Depends(get_service),
    settings: Settings = Depends(get_settings),
    plivo_client: PlivoClient = Depends(get_plivo_client),
) -> PlaceCallResponse:
    to_number = _normalize_destination(body.to)

    if not service.rate_limiter.allow(to_number):
        raise HTTPException(
            status_code=429,
            detail="Too many calls to this number recently. Wait a minute and try again.",
        )

    result = plivo_client.place_call(to_number)
    await service.register_outbound_call(result.request_uuid, to_number)
    return PlaceCallResponse(request_uuid=result.request_uuid, to=to_number)


@router.get("", response_model=list[CallSummary])
async def list_calls(service: CallService = Depends(get_service)) -> list[CallSummary]:
    sessions = await service.active_calls()
    return [_to_summary(s) for s in sessions]


@router.get("/{call_uuid}", response_model=CallSummary)
async def get_call(call_uuid: str, service: CallService = Depends(get_service)) -> CallSummary:
    session = await service.get_session(call_uuid)
    if session is None:
        raise HTTPException(status_code=404, detail="No call with that id.")
    return _to_summary(session)
