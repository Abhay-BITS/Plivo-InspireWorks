"""Absolute callback URL construction.

Every URL handed to Plivo must be absolute against PUBLIC_BASE_URL. Relative
resolution against a tunnel host only breaks in an environment we do not
control locally, and signature validation needs the exact absolute URL Plivo
called, so there is no path where a relative URL is acceptable here.
"""

from app.config import Settings


class CallbackUrls:
    def __init__(self, settings: Settings) -> None:
        self._base = settings.public_base_url

    def _abs(self, path: str) -> str:
        return f"{self._base}{path}"

    @property
    def answer(self) -> str:
        return self._abs("/voice/answer")

    @property
    def otp(self) -> str:
        return self._abs("/voice/otp")

    @property
    def otp_timeout(self) -> str:
        return self._abs("/voice/otp-timeout")

    @property
    def language(self) -> str:
        return self._abs("/voice/language")

    @property
    def language_timeout(self) -> str:
        return self._abs("/voice/language-timeout")

    @property
    def action_menu(self) -> str:
        return self._abs("/voice/action-menu")

    @property
    def action(self) -> str:
        return self._abs("/voice/action")

    @property
    def action_timeout(self) -> str:
        return self._abs("/voice/action-timeout")

    @property
    def hangup(self) -> str:
        return self._abs("/events/hangup")

    @property
    def fallback(self) -> str:
        return self._abs("/events/fallback")

    @property
    def dial_status(self) -> str:
        return self._abs("/events/dial-status")
