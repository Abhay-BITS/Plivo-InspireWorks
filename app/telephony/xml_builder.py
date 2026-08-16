"""Every XML document the app can emit, built with plivoxml rather than
hand concatenated strings so escaping is always correct.

Retries is pinned at 1 on every GetDigits: one collection attempt with no
internal Plivo retry. Plivo's own retry would replay the prompt without
telling the app, which would make otp_attempts and the timeline lie about
what the caller actually heard. Every re-prompt in this system passes
through the state machine and is visible in the timeline because of this.
"""

from plivo import plivoxml

from app.calls.models import Locale
from app.ivr.machine import PromptId, PromptIntent
from app.telephony import prompts
from app.telephony.prompts import VOICE_BY_LOCALE
from app.urls import CallbackUrls

NUM_DIGITS_DEFAULT = 1
GET_DIGITS_TIMEOUT = 8
GET_DIGITS_RETRIES = 1


def _menu_document(
    *,
    speak_lines: list[tuple[str, str, str]],
    action_url: str,
    timeout_url: str,
    num_digits: int,
) -> str:
    """speak_lines is a list of (text, language, voice) spoken inside GetDigits."""
    response = plivoxml.ResponseElement()
    get_digits = plivoxml.GetDigitsElement(
        action=action_url,
        method="POST",
        num_digits=num_digits,
        timeout=GET_DIGITS_TIMEOUT,
        retries=GET_DIGITS_RETRIES,
        valid_digits="0123456789",
    )
    for text, language, voice in speak_lines:
        get_digits.add_speak(text, voice=voice, language=language)
    response.add(get_digits)
    response.add_redirect(timeout_url)
    return str(response.to_string(False))


def otp_document(attempt: int, urls: CallbackUrls) -> str:
    language, voice = VOICE_BY_LOCALE[Locale.EN]
    text = prompts.otp_prompt(attempt)
    return _menu_document(
        speak_lines=[(text, language, voice)],
        action_url=urls.otp,
        timeout_url=urls.otp_timeout,
        num_digits=4,
    )


def language_menu_document(urls: CallbackUrls, retry: bool = False) -> str:
    en_language, en_voice = VOICE_BY_LOCALE[Locale.EN]
    es_language, es_voice = VOICE_BY_LOCALE[Locale.ES]
    text = prompts.language_retry() if retry else prompts.language_menu()
    return _menu_document(
        speak_lines=[(text, en_language, en_voice)],
        action_url=urls.language,
        timeout_url=urls.language_timeout,
        num_digits=NUM_DIGITS_DEFAULT,
    )


def action_menu_document(locale: Locale, urls: CallbackUrls, retry: bool = False) -> str:
    language, voice = VOICE_BY_LOCALE[locale]
    text = prompts.action_retry(locale) if retry else prompts.action_menu(locale)
    return _menu_document(
        speak_lines=[(text, language, voice)],
        action_url=urls.action,
        timeout_url=urls.action_timeout,
        num_digits=NUM_DIGITS_DEFAULT,
    )


def play_audio_document(locale: Locale, audio_url: str, urls: CallbackUrls) -> str:
    response = plivoxml.ResponseElement()
    response.add_play(audio_url)
    response.add_redirect(urls.action_menu)
    return str(response.to_string(False))


def transfer_document(
    locale: Locale,
    associate_number: str,
    caller_id: str,
    urls: CallbackUrls,
) -> str:
    language, voice = VOICE_BY_LOCALE[locale]
    response = plivoxml.ResponseElement()
    response.add_speak(prompts.transfer_line(locale), voice=voice, language=language)
    dial = plivoxml.DialElement(
        action=urls.dial_status,
        method="POST",
        caller_id=caller_id,
        timeout=30,
        redirect=False,
    )
    dial.add_number(associate_number)
    response.add(dial)
    response.add_speak(prompts.transfer_failed_line(locale), voice=voice, language=language)
    response.add_redirect(urls.action_menu)
    return str(response.to_string(False))


def error_document() -> str:
    language, voice = VOICE_BY_LOCALE[Locale.EN]
    response = plivoxml.ResponseElement()
    response.add_speak(prompts.goodbye_line(), voice=voice, language=language)
    response.add_hangup()
    return str(response.to_string(False))


def render(
    intent: PromptIntent,
    urls: CallbackUrls,
    *,
    audio_url: str,
    associate_number: str,
    caller_id: str,
) -> str:
    """Single entry point handlers.py calls to turn a PromptIntent into XML."""
    if intent.prompt_id in (PromptId.OTP_PROMPT, PromptId.OTP_RETRY):
        return otp_document(intent.attempt, urls)
    if intent.prompt_id == PromptId.LANGUAGE_MENU:
        return language_menu_document(urls)
    if intent.prompt_id == PromptId.LANGUAGE_RETRY:
        return language_menu_document(urls, retry=True)
    if intent.prompt_id == PromptId.ACTION_MENU:
        assert intent.locale is not None
        return action_menu_document(intent.locale, urls)
    if intent.prompt_id == PromptId.ACTION_RETRY:
        assert intent.locale is not None
        return action_menu_document(intent.locale, urls, retry=True)
    if intent.prompt_id == PromptId.PLAY_AUDIO:
        assert intent.locale is not None
        return play_audio_document(intent.locale, audio_url, urls)
    if intent.prompt_id == PromptId.TRANSFER:
        assert intent.locale is not None
        return transfer_document(intent.locale, associate_number, caller_id, urls)
    return error_document()
