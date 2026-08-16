"""Structural assertions on served XML. String equality is not used because
whitespace and attribute order are not the contract; nesting is.
"""

from xml.etree import ElementTree as ET

from app.calls.models import Locale
from app.telephony import xml_builder


def test_otp_prompt_is_child_of_get_digits(urls):
    doc = xml_builder.otp_document(0, urls)
    root = ET.fromstring(doc)
    get_digits = root.find("GetDigits")
    assert get_digits is not None
    assert get_digits.find("Speak") is not None
    assert root.find("Speak") is None, "prompt must not be a sibling of GetDigits"


def test_otp_document_has_redirect_after_get_digits(urls):
    doc = xml_builder.otp_document(0, urls)
    root = ET.fromstring(doc)
    children = list(root)
    tags = [child.tag for child in children]
    assert tags.index("Redirect") > tags.index("GetDigits")


def test_otp_get_digits_config(urls):
    doc = xml_builder.otp_document(0, urls)
    root = ET.fromstring(doc)
    get_digits = root.find("GetDigits")
    assert get_digits.get("numDigits") == "4"
    assert get_digits.get("retries") == "1"
    assert get_digits.get("action") == urls.otp
    redirect = root.find("Redirect")
    assert redirect.text == urls.otp_timeout


def test_language_menu_speaks_both_languages(urls):
    doc = xml_builder.language_menu_document(urls)
    root = ET.fromstring(doc)
    speak_text = root.find("GetDigits/Speak").text
    assert "1" in speak_text
    assert "2" in speak_text
    assert "espanol" in speak_text.lower()


def test_action_menu_english_document(urls):
    doc = xml_builder.action_menu_document(Locale.EN, urls)
    root = ET.fromstring(doc)
    speak = root.find("GetDigits/Speak")
    assert speak.get("language") == "en-US"
    redirect = root.find("Redirect")
    assert redirect.text == urls.action_timeout


def test_action_menu_spanish_is_actually_spanish(urls):
    doc = xml_builder.action_menu_document(Locale.ES, urls)
    root = ET.fromstring(doc)
    speak = root.find("GetDigits/Speak")
    assert speak.get("language") == "es-ES"
    assert "asociado" in speak.text.lower()


def test_every_menu_document_has_redirect_after_get_digits(urls):
    docs = [
        xml_builder.otp_document(0, urls),
        xml_builder.language_menu_document(urls),
        xml_builder.action_menu_document(Locale.EN, urls),
    ]
    for doc in docs:
        root = ET.fromstring(doc)
        tags = [child.tag for child in root]
        assert "GetDigits" in tags
        assert "Redirect" in tags
        assert tags.index("Redirect") > tags.index("GetDigits")


def test_play_audio_redirects_back_to_action_menu(urls):
    doc = xml_builder.play_audio_document(Locale.EN, "https://example.com/a.mp3", urls)
    root = ET.fromstring(doc)
    assert root.find("Play").text == "https://example.com/a.mp3"
    assert root.find("Redirect").text == urls.action_menu


def test_transfer_document_has_fallback_after_dial(urls):
    doc = xml_builder.transfer_document(Locale.EN, "02264236412", "+918035454161", urls)
    root = ET.fromstring(doc)
    tags = [child.tag for child in root]
    dial_index = tags.index("Dial")
    assert "Speak" in tags[dial_index + 1 :]
    assert "Redirect" in tags[dial_index + 1 :]
    dial = root.find("Dial")
    assert dial.get("callerId") == "+918035454161"
    assert dial.get("redirect") == "false"
    assert dial.find("Number").text == "02264236412"


def test_error_document_speaks_and_hangs_up():
    doc = xml_builder.error_document()
    root = ET.fromstring(doc)
    assert root.find("Speak") is not None
    assert root.find("Hangup") is not None
