"""Every string the caller hears. Keyed by locale and prompt id, and
nowhere else, so a copy change or a new language never touches a route
handler.
"""

from app.calls.models import Locale

VOICE_BY_LOCALE: dict[Locale, tuple[str, str]] = {
    Locale.EN: ("en-US", "Polly.Joanna"),
    Locale.ES: ("es-ES", "Polly.Conchita"),
}


def otp_prompt(attempt: int) -> str:
    if attempt == 0:
        return "Welcome. Please enter your four digit access code."
    if attempt == 1:
        return "That code was not correct. Please enter your four digit access code."
    if attempt == 2:
        return "That code was not correct. Please try again with your four digit access code."
    return (
        "That code was not correct. The code is four digits, the day then the month. "
        "Please enter it now."
    )


def language_menu() -> str:
    return (
        "For English, press 1. "
        "Para espanol, presione 2."
    )


def language_retry() -> str:
    return (
        "Sorry, that was not a valid choice. "
        "For English, press 1. Para espanol, presione 2."
    )


def action_menu(locale: Locale) -> str:
    if locale == Locale.ES:
        return (
            "Para escuchar un mensaje de audio, presione 1. "
            "Para hablar con un asociado, presione 2. "
            "Para volver al menu anterior, presione 9."
        )
    return (
        "To hear an audio message, press 1. "
        "To speak with a live associate, press 2. "
        "To go back to the previous menu, press 9."
    )


def action_retry(locale: Locale) -> str:
    prefix_en = "Sorry, that was not a valid choice. "
    prefix_es = "Lo sentimos, esa no fue una opcion valida. "
    if locale == Locale.ES:
        return prefix_es + action_menu(locale)
    return prefix_en + action_menu(locale)


def transfer_line(locale: Locale) -> str:
    if locale == Locale.ES:
        return "Le transferimos con un asociado. Por favor espere."
    return "Transferring you to a live associate. Please hold."


def transfer_failed_line(locale: Locale) -> str:
    if locale == Locale.ES:
        return "No pudimos comunicarlo con un asociado en este momento."
    return "We could not reach an associate right now."


def goodbye_line() -> str:
    return "We are sorry, something went wrong on our end. Goodbye."
