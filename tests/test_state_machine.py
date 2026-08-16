"""Table driven coverage of app.ivr.machine.advance. Every state crossed
with valid, invalid, empty, and repeated input, asserting the machine
never returns a state outside CallState.
"""

import pytest

from app.calls.models import Locale
from app.ivr.machine import InputEvent, InputKind, advance
from app.ivr.states import CallState

ALL_STATES = set(CallState)


def test_otp_correct_code_reaches_language_menu(make_session):
    session = make_session(state=CallState.AWAITING_OTP)
    result = advance(session, InputEvent(InputKind.DIGITS, "0407"))
    assert result.next_state == CallState.LANGUAGE_MENU
    assert session.is_authenticated


@pytest.mark.parametrize("digits", ["0000", "9999", "040", "04070"])
def test_otp_wrong_code_stays_at_otp_and_increments_attempts(make_session, digits):
    session = make_session(state=CallState.AWAITING_OTP)
    result = advance(session, InputEvent(InputKind.DIGITS, digits))
    assert result.next_state == CallState.AWAITING_OTP
    assert session.otp_attempts == 1
    assert not session.is_authenticated


def test_otp_no_input_stays_at_otp_and_increments_attempts(make_session):
    session = make_session(state=CallState.AWAITING_OTP)
    result = advance(session, InputEvent(InputKind.NO_INPUT))
    assert result.next_state == CallState.AWAITING_OTP
    assert session.otp_attempts == 1


def test_otp_repeated_wrong_attempts_never_authenticate(make_session):
    session = make_session(state=CallState.AWAITING_OTP)
    for _ in range(5):
        result = advance(session, InputEvent(InputKind.DIGITS, "1111"))
        assert result.next_state == CallState.AWAITING_OTP
    assert session.otp_attempts == 5
    assert not session.is_authenticated


@pytest.mark.parametrize(
    "digits,expected_locale",
    [("1", Locale.EN), ("2", Locale.ES)],
)
def test_language_menu_valid_selection(make_session, digits, expected_locale):
    session = make_session(state=CallState.LANGUAGE_MENU)
    result = advance(session, InputEvent(InputKind.DIGITS, digits))
    assert result.next_state == CallState.ACTION_MENU
    assert session.locale == expected_locale


@pytest.mark.parametrize("digits", ["0", "3", "12", ""])
def test_language_menu_invalid_selection_replays(make_session, digits):
    session = make_session(state=CallState.LANGUAGE_MENU)
    result = advance(session, InputEvent(InputKind.DIGITS, digits))
    assert result.next_state == CallState.LANGUAGE_MENU
    assert session.locale is None


def test_language_menu_no_input_replays(make_session):
    session = make_session(state=CallState.LANGUAGE_MENU)
    result = advance(session, InputEvent(InputKind.NO_INPUT))
    assert result.next_state == CallState.LANGUAGE_MENU


@pytest.mark.parametrize(
    "digits,expected_state",
    [("1", CallState.PLAYING_AUDIO), ("2", CallState.TRANSFERRING), ("9", CallState.LANGUAGE_MENU)],
)
def test_action_menu_valid_selections(make_session, digits, expected_state):
    session = make_session(state=CallState.ACTION_MENU, locale=Locale.EN)
    result = advance(session, InputEvent(InputKind.DIGITS, digits))
    assert result.next_state == expected_state


@pytest.mark.parametrize("digits", ["0", "3", "99", ""])
def test_action_menu_invalid_selection_replays(make_session, digits):
    session = make_session(state=CallState.ACTION_MENU, locale=Locale.EN)
    result = advance(session, InputEvent(InputKind.DIGITS, digits))
    assert result.next_state == CallState.ACTION_MENU


def test_action_menu_no_input_replays(make_session):
    session = make_session(state=CallState.ACTION_MENU, locale=Locale.EN)
    result = advance(session, InputEvent(InputKind.NO_INPUT))
    assert result.next_state == CallState.ACTION_MENU


def test_playing_audio_returns_to_action_menu(make_session):
    session = make_session(state=CallState.PLAYING_AUDIO, locale=Locale.EN)
    result = advance(session, InputEvent(InputKind.ACTION_DONE))
    assert result.next_state == CallState.ACTION_MENU


def test_transferring_returns_to_action_menu(make_session):
    session = make_session(state=CallState.TRANSFERRING, locale=Locale.ES)
    result = advance(session, InputEvent(InputKind.ACTION_DONE))
    assert result.next_state == CallState.ACTION_MENU


@pytest.mark.parametrize("state", sorted(CallState, key=str))
def test_advance_never_returns_an_undefined_state(make_session, state):
    session = make_session(state=state, locale=Locale.EN)
    result = advance(session, InputEvent(InputKind.DIGITS, "5"))
    assert result.next_state in ALL_STATES
