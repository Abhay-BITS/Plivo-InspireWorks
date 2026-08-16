"""Renders a PromptIntent into the XML document Plivo receives.

Route handlers call this rather than app.telephony.xml_builder directly,
because rendering needs settings and callback URLs a route handler
should not be assembling by hand. If a route handler starts building
XML itself instead of calling render(), that logic is in the wrong file.
"""

from app.config import Settings
from app.ivr.machine import PromptIntent
from app.telephony import xml_builder
from app.urls import CallbackUrls


def render_intent(intent: PromptIntent, settings: Settings, urls: CallbackUrls) -> str:
    return xml_builder.render(
        intent,
        urls,
        audio_url=settings.action_audio_url,
        associate_number=settings.associate_number,
        caller_id=settings.plivo_from_number,
    )
