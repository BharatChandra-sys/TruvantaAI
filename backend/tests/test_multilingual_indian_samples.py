# Ownership notice: Bodapati Bharat chandra
import pytest

from app.analysis.multilingual import _detect_script, normalize_claim


@pytest.mark.parametrize(
    "text,expected_script",
    [
        ("यह खबर पूरी तरह झूठी है और लोगों को गुमराह कर रही है", "devanagari"),
        ("ఈ వార్త పూర్తిగా తప్పుడు సమాచారం", "telugu"),
        ("இந்த செய்தி முற்றிலும் பொய்யானது", "tamil"),
        ("یہ خبر غلط معلومات پھیلا رہی ہے", "arabic"),
        ("এই খবরটি সম্পূর্ণ ভুয়া", "bengali"),
    ],
)
def test_detect_script_for_indian_samples(text, expected_script):
    assert _detect_script(text) == expected_script


def test_normalize_claim_translates_hindi_sample(monkeypatch):
    sample = "यह खबर पूरी तरह झूठी है और लोगों को गुमराह कर रही है"

    monkeypatch.setattr("app.analysis.multilingual.detect_language", lambda _t: "hi")
    monkeypatch.setattr(
        "app.analysis.multilingual.translate_to_english",
        lambda _text, _lang: ("This news is completely fake and misleading people", "Hindi"),
    )

    normalized, lang_name, translated = normalize_claim(sample)

    assert translated is True
    assert lang_name == "Hindi"
    assert "fake" in normalized.lower()


def test_normalize_claim_translates_telugu_sample(monkeypatch):
    sample = "ఈ వార్త పూర్తిగా తప్పుడు సమాచారం"

    monkeypatch.setattr("app.analysis.multilingual.detect_language", lambda _t: "te")
    monkeypatch.setattr(
        "app.analysis.multilingual.translate_to_english",
        lambda _text, _lang: ("This claim contains false information", "Telugu"),
    )

    normalized, lang_name, translated = normalize_claim(sample)

    assert translated is True
    assert lang_name == "Telugu"
    assert "false" in normalized.lower()


def test_normalize_claim_keeps_english_unchanged():
    text = "This is a factual claim about vaccine safety."
    normalized, lang_name, translated = normalize_claim(text)

    assert normalized == text
    assert lang_name == "English"
    assert translated is False
