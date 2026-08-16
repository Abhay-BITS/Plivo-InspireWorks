"""Three wrong codes then the correct one, through real HTTP routes."""

from xml.etree import ElementTree as ET

from tests.conftest import webhook_form


async def test_wrong_codes_then_correct_reaches_language_menu(client):
    call_uuid = "otp-flow-1"
    await client.post("/voice/answer", data=webhook_form(call_uuid))

    for wrong in ("1111", "2222", "3333"):
        resp = await client.post("/voice/otp", data=webhook_form(call_uuid, Digits=wrong))
        assert resp.status_code == 200
        root = ET.fromstring(resp.text)
        assert root.find("GetDigits") is not None

    resp = await client.post("/voice/otp", data=webhook_form(call_uuid, Digits="0407"))
    root = ET.fromstring(resp.text)
    speak = root.find("GetDigits/Speak")
    assert "espanol" in speak.text.lower() or "english" in speak.text.lower()


async def test_four_attempts_recorded_in_session(client):
    call_uuid = "otp-flow-2"
    await client.post("/voice/answer", data=webhook_form(call_uuid))
    for wrong in ("1111", "2222", "3333"):
        await client.post("/voice/otp", data=webhook_form(call_uuid, Digits=wrong))
    await client.post("/voice/otp", data=webhook_form(call_uuid, Digits="0407"))

    service = client.app.state.service
    session = await service.get_session(call_uuid)
    assert session.otp_attempts == 3
    assert session.is_authenticated
