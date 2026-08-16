"""POST /api/calls with the Plivo client mocked. Bad numbers give 422,
and the SDK is called with the exact expected keyword arguments.
"""

from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def _mock_plivo(client):
    fake_response = MagicMock()
    fake_response.request_uuid = "fake-request-uuid"
    mock_calls = MagicMock()
    mock_calls.create.return_value = fake_response
    client.app.state.plivo_client._client.calls = mock_calls
    return mock_calls


async def test_place_call_returns_request_uuid(client, _mock_plivo):
    resp = await client.post("/api/calls", json={"to": "+917007745038"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["request_uuid"] == "fake-request-uuid"
    assert body["to"] == "+917007745038"


async def test_place_call_invokes_sdk_with_expected_kwargs(client, _mock_plivo):
    await client.post("/api/calls", json={"to": "+917007745038"})
    settings = client.app.state.settings
    urls = client.app.state.urls

    _mock_plivo.create.assert_called_once_with(
        from_=settings.plivo_from_number,
        to_="+917007745038",
        answer_url=urls.answer,
        answer_method="POST",
        hangup_url=urls.hangup,
        fallback_url=urls.fallback,
        ring_timeout=30,
    )


async def test_place_call_rejects_unparseable_number(client, _mock_plivo):
    resp = await client.post("/api/calls", json={"to": "not-a-number"})
    assert resp.status_code == 422
    assert "could not be parsed" in resp.json()["detail"]
    _mock_plivo.create.assert_not_called()


async def test_place_call_normalizes_to_e164(client, _mock_plivo):
    resp = await client.post("/api/calls", json={"to": "+91 7007 745 038"})
    assert resp.status_code == 201
    assert resp.json()["to"] == "+917007745038"


async def test_rate_limit_blocks_after_repeated_calls(client, _mock_plivo):
    for _ in range(3):
        resp = await client.post("/api/calls", json={"to": "+919999999999"})
        assert resp.status_code == 201

    resp = await client.post("/api/calls", json={"to": "+919999999999"})
    assert resp.status_code == 429


async def test_list_calls_includes_placed_call(client, _mock_plivo):
    await client.post("/api/calls", json={"to": "+917007745038"})
    resp = await client.get("/api/calls")
    assert resp.status_code == 200
    uuids = [c["call_uuid"] for c in resp.json()]
    assert "fake-request-uuid" in uuids


async def test_get_unknown_call_is_404(client, _mock_plivo):
    resp = await client.get("/api/calls/does-not-exist")
    assert resp.status_code == 404
