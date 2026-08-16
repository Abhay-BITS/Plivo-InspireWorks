import os

os.environ.setdefault("PLIVO_AUTH_ID", "MATESTXXXXXXXXXXXXXX")
os.environ.setdefault("PLIVO_AUTH_TOKEN", "test_auth_token")
os.environ.setdefault("PUBLIC_BASE_URL", "https://test.example.com")
os.environ.setdefault("VERIFY_PLIVO_SIGNATURE", "false")

import httpx
import pytest

from app.calls.models import CallSession
from app.config import get_settings
from app.main import create_app
from app.urls import CallbackUrls


@pytest.fixture
def settings():
    return get_settings()


@pytest.fixture
def urls(settings):
    return CallbackUrls(settings)


@pytest.fixture
def make_session(settings):
    def _make(call_uuid: str = "test-uuid-1", **overrides):
        defaults = dict(
            call_uuid=call_uuid,
            to_number="+917007745038",
            from_number=settings.plivo_from_number,
            otp_code=settings.otp_code,
        )
        defaults.update(overrides)
        return CallSession(**defaults)

    return _make


@pytest.fixture
async def client():
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://test.example.com") as ac:
        async with app.router.lifespan_context(app):
            ac.app = app
            yield ac


def webhook_form(call_uuid: str, **extra) -> dict:
    form = {"CallUUID": call_uuid, "To": "+917007745038", "From": "+918035454161"}
    form.update(extra)
    return form
