"""Dependency accessors reading the singletons main.py attaches to
app.state at startup. Kept in one place so route modules never reach
into request.app.state directly.
"""

from typing import cast

from fastapi import Request

from app.calls.service import CallService
from app.config import Settings
from app.telephony.client import PlivoClient
from app.urls import CallbackUrls


def get_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def get_urls(request: Request) -> CallbackUrls:
    return cast(CallbackUrls, request.app.state.urls)


def get_service(request: Request) -> CallService:
    return cast(CallService, request.app.state.service)


def get_plivo_client(request: Request) -> PlivoClient:
    return cast(PlivoClient, request.app.state.plivo_client)
