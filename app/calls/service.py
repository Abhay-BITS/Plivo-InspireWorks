"""Orchestration: the layer that owns a webhook end to end. Loads or
creates a session, feeds the machine, renders XML, records the timeline,
and publishes to the WebSocket bus. Route handlers should never do more
than call into this module.
"""

import asyncio
import time
from dataclasses import dataclass

from app.calls.models import CallEvent, CallSession, utcnow
from app.calls.rate_limit import DestinationRateLimiter
from app.calls.store import CallStateStore
from app.config import Settings
from app.ivr.handlers import render_intent
from app.ivr.machine import InputEvent, InputKind, PromptId, PromptIntent, Transition, advance
from app.ivr.states import CallState
from app.observability.logging import get_logger
from app.observability.timeline import Timeline
from app.urls import CallbackUrls

logger = get_logger(__name__)


class EventBus:
    """Fan out CallEvents to every connected WebSocket. A slow or absent
    subscriber never blocks a webhook: publish is fire and forget from
    the caller's perspective, each subscriber gets its own bounded queue,
    and a full queue drops the oldest event rather than back-pressuring
    the publisher.
    """

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[CallEvent]] = set()

    def subscribe(self) -> "asyncio.Queue[CallEvent]":
        queue: asyncio.Queue[CallEvent] = asyncio.Queue(maxsize=200)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: "asyncio.Queue[CallEvent]") -> None:
        self._subscribers.discard(queue)

    def publish(self, event: CallEvent) -> None:
        for queue in list(self._subscribers):
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(event)


@dataclass
class WebhookResult:
    session: CallSession
    xml: str
    transition: Transition | None = None


class CallService:
    def __init__(
        self,
        store: CallStateStore,
        timeline: Timeline,
        bus: EventBus,
        settings: Settings,
        urls: CallbackUrls,
    ) -> None:
        self._store = store
        self._timeline = timeline
        self._bus = bus
        self._settings = settings
        self._urls = urls
        self.rate_limiter = DestinationRateLimiter()

    def _publish(self, event: CallEvent) -> None:
        self._timeline.record(event)
        self._bus.publish(event)

    async def register_outbound_call(self, call_uuid: str, to_number: str) -> CallSession:
        session = CallSession(
            call_uuid=call_uuid,
            to_number=to_number,
            from_number=self._settings.plivo_from_number,
            otp_code=self._settings.otp_code,
        )
        await self._store.put(session)
        return session

    async def _get_or_recover_session(
        self, call_uuid: str, to_number: str = "unknown"
    ) -> CallSession:
        session = await self._store.get(call_uuid)
        if session is not None:
            return session

        logger.warning("unknown call_uuid on webhook, starting a fresh session")
        session = CallSession(
            call_uuid=call_uuid,
            to_number=to_number,
            from_number=self._settings.plivo_from_number,
            otp_code=self._settings.otp_code,
        )
        await self._store.put(session)
        return session

    async def serve_otp_prompt(
        self, call_uuid: str, endpoint: str, to_number: str = "unknown"
    ) -> WebhookResult:
        """Renders the code prompt without going through advance(). Used on
        the very first answer, where there is no prior event to feed the
        machine, and as the guard on /voice/language so that URL cannot be
        reached by guessing it: an unauthenticated session is simply shown
        the code prompt again.
        """
        started = time.perf_counter()
        session = await self._get_or_recover_session(call_uuid, to_number)
        prompt = PromptIntent(
            prompt_id=PromptId.OTP_PROMPT if session.otp_attempts == 0 else PromptId.OTP_RETRY,
            attempt=session.otp_attempts,
        )
        xml = render_intent(prompt, self._settings, self._urls)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        self._publish(
            CallEvent(
                type="xml_served",
                call_uuid=call_uuid,
                payload={"endpoint": endpoint, "xml": xml, "duration_ms": duration_ms},
            )
        )
        return WebhookResult(session=session, xml=xml)

    async def handle_webhook(
        self,
        *,
        endpoint: str,
        call_uuid: str,
        event: InputEvent,
    ) -> WebhookResult:
        started = time.perf_counter()
        session = await self._get_or_recover_session(call_uuid)
        from_state = session.state

        if event.kind == InputKind.DIGITS:
            accepted = self._digits_will_advance(session, event.digits)
            self._publish(
                CallEvent(
                    type="dtmf",
                    call_uuid=call_uuid,
                    payload={
                        "digits": event.digits,
                        "level": from_state.value,
                        "accepted": accepted,
                    },
                )
            )

        transition = advance(session, event)
        session.state = transition.next_state
        session.touch()
        await self._store.put(session)

        if transition.next_state != from_state:
            self._publish(
                CallEvent(
                    type="state_change",
                    call_uuid=call_uuid,
                    payload={
                        "from": from_state.value,
                        "to": transition.next_state.value,
                        "reason": transition.reason,
                    },
                )
            )

        xml = render_intent(transition.prompt, self._settings, self._urls)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        self._publish(
            CallEvent(
                type="xml_served",
                call_uuid=call_uuid,
                payload={"endpoint": endpoint, "xml": xml, "duration_ms": duration_ms},
            )
        )

        return WebhookResult(session=session, transition=transition, xml=xml)

    def _digits_will_advance(self, session: CallSession, digits: str) -> bool:
        """Whether these digits are accepted at the caller's current level,
        computed without mutating state, purely so the dtmf event can report
        accepted/rejected before the real transition runs.
        """
        state = session.state
        if state == CallState.AWAITING_OTP:
            return digits == session.otp_code
        if state == CallState.LANGUAGE_MENU:
            return digits in ("1", "2")
        if state == CallState.ACTION_MENU:
            return digits in ("1", "2", "9")
        return False

    async def finalize_call(self, call_uuid: str, hangup_cause: str) -> None:
        session = await self._get_or_recover_session(call_uuid)
        session.ended_at = utcnow()
        session.hangup_cause = hangup_cause
        session.state = CallState.COMPLETED
        session.touch()
        await self._store.put(session)
        self._publish(
            CallEvent(
                type="call_ended",
                call_uuid=call_uuid,
                payload={
                    "final_state": session.state.value,
                    "duration_seconds": (session.ended_at - session.created_at).total_seconds(),
                    "hangup_cause": hangup_cause,
                },
            )
        )

    async def active_calls(self) -> list[CallSession]:
        return await self._store.all_active()

    async def get_session(self, call_uuid: str) -> CallSession | None:
        return await self._store.get(call_uuid)

    def history(self, call_uuid: str) -> list[CallEvent]:
        return self._timeline.history(call_uuid)
