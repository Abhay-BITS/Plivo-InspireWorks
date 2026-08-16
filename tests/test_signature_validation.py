"""A valid Plivo V3 signature passes, a tampered body returns 403."""


import plivo.utils.signature_v3 as sv3
import pytest

from tests.conftest import webhook_form

AUTH_TOKEN = "signature-test-token"


def _sign(uri: str, params: dict, nonce: str = "test-nonce") -> str:
    base_url = sv3.construct_post_url(uri, params).decode("utf-8")
    signature = sv3.get_signature_v3(AUTH_TOKEN.encode("utf-8"), base_url, nonce.encode("utf-8"))
    return signature.decode("utf-8")


@pytest.fixture(autouse=True)
def _signature_env(monkeypatch):
    monkeypatch.setenv("PLIVO_AUTH_TOKEN", AUTH_TOKEN)
    monkeypatch.setenv("VERIFY_PLIVO_SIGNATURE", "true")
    from app.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
    monkeypatch.setenv("VERIFY_PLIVO_SIGNATURE", "false")


async def test_valid_signature_is_accepted(client):
    call_uuid = "sig-valid"
    form = webhook_form(call_uuid)
    signature = _sign(f"{client.base_url}/voice/answer", form)

    resp = await client.post(
        "/voice/answer",
        data=form,
        headers={"X-Plivo-Signature-V3": signature, "X-Plivo-Signature-V3-Nonce": "test-nonce"},
    )
    assert resp.status_code == 200


async def test_tampered_body_is_rejected(client):
    call_uuid = "sig-invalid"
    form = webhook_form(call_uuid)
    signature = _sign(f"{client.base_url}/voice/answer", form)

    tampered = dict(form)
    tampered["Digits"] = "9999"

    resp = await client.post(
        "/voice/answer",
        data=tampered,
        headers={"X-Plivo-Signature-V3": signature, "X-Plivo-Signature-V3-Nonce": "test-nonce"},
    )
    assert resp.status_code == 403


async def test_missing_signature_header_is_rejected(client):
    resp = await client.post("/voice/answer", data=webhook_form("sig-missing"))
    assert resp.status_code == 403
