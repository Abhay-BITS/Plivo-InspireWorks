"""All four leaf paths: English audio, English transfer, Spanish audio,
Spanish transfer. The Spanish branch must return es-ES and Spanish text,
not English content with a Spanish tag.
"""

from xml.etree import ElementTree as ET

from tests.conftest import webhook_form


async def _authenticate(client, call_uuid: str) -> None:
    await client.post("/voice/answer", data=webhook_form(call_uuid))
    await client.post("/voice/otp", data=webhook_form(call_uuid, Digits="0407"))


async def test_english_audio_path(client):
    call_uuid = "nav-en-audio"
    await _authenticate(client, call_uuid)
    await client.post("/voice/language", data=webhook_form(call_uuid, Digits="1"))
    resp = await client.post("/voice/action", data=webhook_form(call_uuid, Digits="1"))
    root = ET.fromstring(resp.text)
    assert root.find("Play") is not None
    assert root.find("Redirect") is not None


async def test_english_transfer_path(client):
    call_uuid = "nav-en-transfer"
    await _authenticate(client, call_uuid)
    await client.post("/voice/language", data=webhook_form(call_uuid, Digits="1"))
    resp = await client.post("/voice/action", data=webhook_form(call_uuid, Digits="2"))
    root = ET.fromstring(resp.text)
    dial = root.find("Dial")
    assert dial is not None
    assert dial.get("callerId") == "+918035454161"
    assert dial.find("Number").text == "02264236412"


async def test_spanish_audio_path_is_actually_spanish(client):
    call_uuid = "nav-es-audio"
    await _authenticate(client, call_uuid)
    resp = await client.post("/voice/language", data=webhook_form(call_uuid, Digits="2"))
    root = ET.fromstring(resp.text)
    speak = root.find("GetDigits/Speak")
    assert speak.get("language") == "es-ES"
    assert "asociado" in speak.text.lower()

    resp = await client.post("/voice/action", data=webhook_form(call_uuid, Digits="1"))
    root = ET.fromstring(resp.text)
    assert root.find("Play") is not None


async def test_spanish_transfer_path(client):
    call_uuid = "nav-es-transfer"
    await _authenticate(client, call_uuid)
    await client.post("/voice/language", data=webhook_form(call_uuid, Digits="2"))
    resp = await client.post("/voice/action", data=webhook_form(call_uuid, Digits="2"))
    root = ET.fromstring(resp.text)
    dial = root.find("Dial")
    assert dial is not None
    speak = root.find("Speak")
    assert speak.get("language") == "es-ES"


async def test_press_nine_returns_to_language_menu(client):
    call_uuid = "nav-back"
    await _authenticate(client, call_uuid)
    await client.post("/voice/language", data=webhook_form(call_uuid, Digits="1"))
    resp = await client.post("/voice/action", data=webhook_form(call_uuid, Digits="9"))
    root = ET.fromstring(resp.text)
    speak = root.find("GetDigits/Speak")
    assert "espanol" in speak.text.lower()


async def test_audio_finishing_returns_to_action_menu(client):
    call_uuid = "nav-audio-return"
    await _authenticate(client, call_uuid)
    await client.post("/voice/language", data=webhook_form(call_uuid, Digits="1"))
    await client.post("/voice/action", data=webhook_form(call_uuid, Digits="1"))
    resp = await client.post("/voice/action-menu", data=webhook_form(call_uuid))
    root = ET.fromstring(resp.text)
    speak = root.find("GetDigits/Speak")
    assert "audio" in speak.text.lower()


async def test_invalid_action_digit_replays_with_apology(client):
    call_uuid = "nav-invalid"
    await _authenticate(client, call_uuid)
    await client.post("/voice/language", data=webhook_form(call_uuid, Digits="1"))
    resp = await client.post("/voice/action", data=webhook_form(call_uuid, Digits="5"))
    root = ET.fromstring(resp.text)
    speak = root.find("GetDigits/Speak")
    assert "sorry" in speak.text.lower()
