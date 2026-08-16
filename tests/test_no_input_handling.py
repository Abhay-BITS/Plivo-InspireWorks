"""Hit every timeout endpoint directly and assert each re prompts its own
level rather than advancing or hanging up. This is section 6.2 of the
brief: GetDigits does not call the action URL on no input, it falls
through to Redirect, which is why every level needs its own timeout
endpoint feeding NO_INPUT back into the machine.
"""

from xml.etree import ElementTree as ET

from tests.conftest import webhook_form


async def test_otp_timeout_reprompts_code(client):
    call_uuid = "timeout-otp"
    await client.post("/voice/answer", data=webhook_form(call_uuid))
    resp = await client.post("/voice/otp-timeout", data=webhook_form(call_uuid))
    root = ET.fromstring(resp.text)
    get_digits = root.find("GetDigits")
    assert get_digits is not None
    assert get_digits.get("numDigits") == "4"


async def test_otp_timeout_does_not_authenticate(client):
    call_uuid = "timeout-otp-2"
    await client.post("/voice/answer", data=webhook_form(call_uuid))
    await client.post("/voice/otp-timeout", data=webhook_form(call_uuid))

    resp = await client.post("/voice/language", data=webhook_form(call_uuid, Digits="1"))
    root = ET.fromstring(resp.text)
    assert root.find("GetDigits").get("numDigits") == "4"


async def test_language_timeout_reprompts_language_menu(client):
    call_uuid = "timeout-language"
    await client.post("/voice/answer", data=webhook_form(call_uuid))
    await client.post("/voice/otp", data=webhook_form(call_uuid, Digits="0407"))
    resp = await client.post("/voice/language-timeout", data=webhook_form(call_uuid))
    root = ET.fromstring(resp.text)
    speak = root.find("GetDigits/Speak")
    assert "espanol" in speak.text.lower()


async def test_action_timeout_reprompts_action_menu(client):
    call_uuid = "timeout-action"
    await client.post("/voice/answer", data=webhook_form(call_uuid))
    await client.post("/voice/otp", data=webhook_form(call_uuid, Digits="0407"))
    await client.post("/voice/language", data=webhook_form(call_uuid, Digits="1"))
    resp = await client.post("/voice/action-timeout", data=webhook_form(call_uuid))
    root = ET.fromstring(resp.text)
    speak = root.find("GetDigits/Speak")
    assert "associate" in speak.text.lower()


async def test_repeated_otp_timeouts_never_hang_up(client):
    call_uuid = "timeout-repeat"
    await client.post("/voice/answer", data=webhook_form(call_uuid))
    for _ in range(4):
        resp = await client.post("/voice/otp-timeout", data=webhook_form(call_uuid))
        root = ET.fromstring(resp.text)
        assert root.find("Hangup") is None
        assert root.find("GetDigits") is not None
