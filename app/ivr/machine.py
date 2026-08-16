"""The IVR as a pure function. No FastAPI, no Plivo SDK, no I/O.

Read this file to understand the whole product: what the caller can do at
each state, and what they hear next. Everything above this file is plumbing
that gets an InputEvent here and turns a Transition into a response.
"""

from dataclasses import dataclass
from enum import StrEnum

from app.calls.models import CallSession, Locale, utcnow
from app.ivr.states import CallState


class InputKind(StrEnum):
    DIGITS = "digits"
    NO_INPUT = "no_input"
    ACTION_DONE = "action_done"


@dataclass(frozen=True)
class InputEvent:
    kind: InputKind
    digits: str = ""


class PromptId(StrEnum):
    OTP_PROMPT = "otp_prompt"
    OTP_RETRY = "otp_retry"
    LANGUAGE_MENU = "language_menu"
    LANGUAGE_RETRY = "language_retry"
    ACTION_MENU = "action_menu"
    ACTION_RETRY = "action_retry"
    PLAY_AUDIO = "play_audio"
    TRANSFER = "transfer"
    GOODBYE = "goodbye"


@dataclass(frozen=True)
class PromptIntent:
    prompt_id: PromptId
    locale: Locale | None = None
    attempt: int = 0


@dataclass(frozen=True)
class Transition:
    next_state: CallState
    reason: str
    prompt: PromptIntent


def _otp_prompt(attempt: int) -> PromptIntent:
    prompt_id = PromptId.OTP_PROMPT if attempt == 0 else PromptId.OTP_RETRY
    return PromptIntent(prompt_id=prompt_id, attempt=attempt)


def advance(session: CallSession, event: InputEvent) -> Transition:
    """Pure state transition. Never returns an undefined state: every
    branch below ends in a CallState member, and the fallback path
    re-serves the current level rather than inventing a new one.
    """
    state = session.state

    if state == CallState.AWAITING_OTP:
        return _advance_otp(session, event)
    if state == CallState.LANGUAGE_MENU:
        return _advance_language(session, event)
    if state == CallState.ACTION_MENU:
        return _advance_action_menu(session, event)
    if state == CallState.PLAYING_AUDIO:
        return Transition(
            next_state=CallState.ACTION_MENU,
            reason="audio finished, returning to action menu",
            prompt=PromptIntent(prompt_id=PromptId.ACTION_MENU, locale=session.locale),
        )
    if state == CallState.TRANSFERRING:
        return Transition(
            next_state=CallState.ACTION_MENU,
            reason="transfer resolved, returning to action menu",
            prompt=PromptIntent(prompt_id=PromptId.ACTION_MENU, locale=session.locale),
        )

    return Transition(
        next_state=CallState.FAILED,
        reason=f"advance called on terminal state {state}",
        prompt=PromptIntent(prompt_id=PromptId.GOODBYE),
    )


def _advance_otp(session: CallSession, event: InputEvent) -> Transition:
    if event.kind == InputKind.NO_INPUT:
        session.otp_attempts += 1
        return Transition(
            next_state=CallState.AWAITING_OTP,
            reason="no input at code prompt",
            prompt=_otp_prompt(session.otp_attempts),
        )

    if event.kind == InputKind.DIGITS and event.digits == session.otp_code:
        session.authenticated_at = utcnow()
        return Transition(
            next_state=CallState.LANGUAGE_MENU,
            reason="correct code",
            prompt=PromptIntent(prompt_id=PromptId.LANGUAGE_MENU),
        )

    session.otp_attempts += 1
    reason = "wrong code" if event.kind == InputKind.DIGITS else "unexpected event at code prompt"
    return Transition(
        next_state=CallState.AWAITING_OTP,
        reason=reason,
        prompt=_otp_prompt(session.otp_attempts),
    )


def _advance_language(session: CallSession, event: InputEvent) -> Transition:
    if event.kind == InputKind.NO_INPUT:
        return Transition(
            next_state=CallState.LANGUAGE_MENU,
            reason="no input at language menu",
            prompt=PromptIntent(prompt_id=PromptId.LANGUAGE_RETRY),
        )

    if event.kind == InputKind.DIGITS and event.digits == "1":
        session.locale = Locale.EN
        return Transition(
            next_state=CallState.ACTION_MENU,
            reason="English selected",
            prompt=PromptIntent(prompt_id=PromptId.ACTION_MENU, locale=Locale.EN),
        )
    if event.kind == InputKind.DIGITS and event.digits == "2":
        session.locale = Locale.ES
        return Transition(
            next_state=CallState.ACTION_MENU,
            reason="Spanish selected",
            prompt=PromptIntent(prompt_id=PromptId.ACTION_MENU, locale=Locale.ES),
        )

    return Transition(
        next_state=CallState.LANGUAGE_MENU,
        reason="invalid language selection",
        prompt=PromptIntent(prompt_id=PromptId.LANGUAGE_RETRY),
    )


def _advance_action_menu(session: CallSession, event: InputEvent) -> Transition:
    locale = session.locale

    if event.kind == InputKind.ACTION_DONE:
        return Transition(
            next_state=CallState.ACTION_MENU,
            reason="returned to action menu",
            prompt=PromptIntent(prompt_id=PromptId.ACTION_MENU, locale=locale),
        )

    if event.kind == InputKind.NO_INPUT:
        return Transition(
            next_state=CallState.ACTION_MENU,
            reason="no input at action menu",
            prompt=PromptIntent(prompt_id=PromptId.ACTION_RETRY, locale=locale),
        )

    if event.kind == InputKind.DIGITS and event.digits == "1":
        return Transition(
            next_state=CallState.PLAYING_AUDIO,
            reason="audio requested",
            prompt=PromptIntent(prompt_id=PromptId.PLAY_AUDIO, locale=locale),
        )
    if event.kind == InputKind.DIGITS and event.digits == "2":
        return Transition(
            next_state=CallState.TRANSFERRING,
            reason="transfer requested",
            prompt=PromptIntent(prompt_id=PromptId.TRANSFER, locale=locale),
        )
    if event.kind == InputKind.DIGITS and event.digits == "9":
        session.locale = None
        return Transition(
            next_state=CallState.LANGUAGE_MENU,
            reason="back to language menu",
            prompt=PromptIntent(prompt_id=PromptId.LANGUAGE_MENU),
        )

    return Transition(
        next_state=CallState.ACTION_MENU,
        reason="invalid action selection",
        prompt=PromptIntent(prompt_id=PromptId.ACTION_RETRY, locale=locale),
    )
