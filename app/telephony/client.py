"""Thin wrapper over the Plivo REST client. The only file that talks to
Plivo's HTTP API, kept separate so the outbound route can be tested
against a mock without importing plivo.RestClient anywhere else.
"""

from dataclasses import dataclass

import plivo

from app.config import Settings
from app.urls import CallbackUrls


@dataclass(frozen=True)
class OutboundCallResult:
    request_uuid: str


class PlivoClient:
    def __init__(self, settings: Settings, urls: CallbackUrls) -> None:
        self._settings = settings
        self._urls = urls
        self._client = plivo.RestClient(
            auth_id=settings.plivo_auth_id,
            auth_token=settings.plivo_auth_token,
        )

    def place_call(self, to_number: str) -> OutboundCallResult:
        response = self._client.calls.create(
            from_=self._settings.plivo_from_number,
            to_=to_number,
            answer_url=self._urls.answer,
            answer_method="POST",
            hangup_url=self._urls.hangup,
            fallback_url=self._urls.fallback,
            ring_timeout=30,
        )
        return OutboundCallResult(request_uuid=response.request_uuid)
