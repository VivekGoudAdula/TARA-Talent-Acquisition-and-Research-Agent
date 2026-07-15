"""Twilio Polly voice/locale mapping for multi-language callback conversations."""

from __future__ import annotations

# Twilio speech hints improve recognition for Indian languages.
_LANGUAGE_PROFILES: dict[str, dict[str, str | list[str]]] = {
    "english": {
        "polly_voice": "Polly.Aditi",
        "polly_language": "en-IN",
        "hints": ["yes", "no", "loan", "interest", "apply", "transfer", "manager", "hindi", "english"],
    },
    "hindi": {
        "polly_voice": "Polly.Aditi",
        "polly_language": "hi-IN",
        "hints": ["haan", "nahi", "loan", "bima", "apply", "manager", "angrezi", "hindi", "transfer"],
    },
    "tamil": {
        "polly_voice": "Polly.Kajal",
        "polly_language": "ta-IN",
        "hints": ["aam", "illa", "loan", "manager", "english", "tamil"],
    },
    "telugu": {
        "polly_voice": "Polly.Chitra",
        "polly_language": "te-IN",
        "hints": ["avunu", "ledu", "loan", "manager", "english", "telugu"],
    },
    "marathi": {
        "polly_voice": "Polly.Aditi",
        "polly_language": "mr-IN",
        "hints": ["ho", "nahi", "loan", "manager", "english", "marathi"],
    },
    "bengali": {
        "polly_voice": "Polly.Aditi",
        "polly_language": "bn-IN",
        "hints": ["haan", "na", "loan", "manager", "english", "bengali"],
    },
    "kannada": {
        "polly_voice": "Polly.Raveena",
        "polly_language": "kn-IN",
        "hints": ["haudu", "illa", "loan", "manager", "english", "kannada"],
    },
    "malayalam": {
        "polly_voice": "Polly.Raveena",
        "polly_language": "ml-IN",
        "hints": ["athe", "illa", "loan", "manager", "english", "malayalam"],
    },
    "gujarati": {
        "polly_voice": "Polly.Aditi",
        "polly_language": "gu-IN",
        "hints": ["ha", "na", "loan", "manager", "english", "gujarati"],
    },
}

_ALIASES = {
    "en": "english",
    "hi": "hindi",
    "ta": "tamil",
    "te": "telugu",
    "mr": "marathi",
    "bn": "bengali",
    "kn": "kannada",
    "ml": "malayalam",
    "gu": "gujarati",
}

_LANG_SWITCH_PHRASES: dict[str, tuple[str, ...]] = {
    "hindi": ("hindi", "हिंदी", "hindi mein", "hindi me", "speak hindi"),
    "english": ("english", "angrezi", "अंग्रेजी", "speak english", "in english"),
    "tamil": ("tamil", "தமிழ்", "tamil la", "speak tamil"),
    "telugu": ("telugu", "తెలుగు", "telugu lo", "speak telugu"),
    "marathi": ("marathi", "मराठी", "speak marathi"),
    "bengali": ("bengali", "bangla", "বাংলা", "speak bengali"),
    "kannada": ("kannada", "ಕನ್ನಡ", "speak kannada"),
    "malayalam": ("malayalam", "മലയാളം", "speak malayalam"),
    "gujarati": ("gujarati", "ગુજરાતી", "speak gujarati"),
}


def normalize_language(lang: str | None) -> str:
    raw = (lang or "english").strip().lower()
    if raw in _LANGUAGE_PROFILES:
        return raw
    if raw in _ALIASES:
        return _ALIASES[raw]
    for key in _LANGUAGE_PROFILES:
        if key in raw:
            return key
    return "english"


def resolve_voice_locale(lang: str | None) -> dict[str, str | list[str]]:
    key = normalize_language(lang)
    profile = _LANGUAGE_PROFILES[key]
    return {
        "language_key": key,
        "polly_voice": str(profile["polly_voice"]),
        "polly_language": str(profile["polly_language"]),
        "hints": list(profile["hints"]),
    }


def detect_language_switch(user_text: str) -> str | None:
    text = (user_text or "").strip().lower()
    if not text:
        return None
    for lang, phrases in _LANG_SWITCH_PHRASES.items():
        if any(phrase in text for phrase in phrases):
            return lang
    return None
