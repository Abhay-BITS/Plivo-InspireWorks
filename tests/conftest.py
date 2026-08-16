import os

os.environ.setdefault("PLIVO_AUTH_ID", "test_auth_id")
os.environ.setdefault("PLIVO_AUTH_TOKEN", "test_auth_token")
os.environ.setdefault("PUBLIC_BASE_URL", "https://test.example.com")
os.environ.setdefault("VERIFY_PLIVO_SIGNATURE", "false")

import pytest

from app.calls.models import CallSession
from app.config import get_settings
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
