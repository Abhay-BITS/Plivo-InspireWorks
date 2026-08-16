"""Interleave webhooks for two CallUUIDs and assert neither session
contaminates the other. The store is keyed by CallUUID precisely so two
calls in flight at once cannot cross-talk.
"""

import asyncio

from tests.conftest import webhook_form


async def test_two_interleaved_calls_hold_independent_state(client):
    call_a = "concurrent-a"
    call_b = "concurrent-b"

    await client.post("/voice/answer", data=webhook_form(call_a))
    await client.post("/voice/answer", data=webhook_form(call_b))

    await client.post("/voice/otp", data=webhook_form(call_a, Digits="1111"))
    await client.post("/voice/otp", data=webhook_form(call_b, Digits="0407"))
    await client.post("/voice/otp", data=webhook_form(call_a, Digits="0407"))

    service = client.app.state.service
    session_a = await service.get_session(call_a)
    session_b = await service.get_session(call_b)

    assert session_a.otp_attempts == 1
    assert session_b.otp_attempts == 0
    assert session_a.is_authenticated
    assert session_b.is_authenticated

    await client.post("/voice/language", data=webhook_form(call_a, Digits="1"))
    await client.post("/voice/language", data=webhook_form(call_b, Digits="2"))

    session_a = await service.get_session(call_a)
    session_b = await service.get_session(call_b)
    assert session_a.locale.value == "en"
    assert session_b.locale.value == "es"


async def test_concurrent_webhooks_for_different_calls_do_not_race(client):
    call_uuids = [f"race-{i}" for i in range(10)]
    for uuid in call_uuids:
        await client.post("/voice/answer", data=webhook_form(uuid))

    await asyncio.gather(
        *(
            client.post("/voice/otp", data=webhook_form(uuid, Digits="0407"))
            for uuid in call_uuids
        )
    )

    service = client.app.state.service
    for uuid in call_uuids:
        session = await service.get_session(uuid)
        assert session.call_uuid == uuid
        assert session.is_authenticated
        assert session.otp_attempts == 0


async def test_dashboard_lists_both_active_calls(client):
    call_a = "concurrent-list-a"
    call_b = "concurrent-list-b"
    await client.post("/voice/answer", data=webhook_form(call_a))
    await client.post("/voice/answer", data=webhook_form(call_b))

    resp = await client.get("/api/calls")
    uuids = {c["call_uuid"] for c in resp.json()}
    assert call_a in uuids
    assert call_b in uuids
