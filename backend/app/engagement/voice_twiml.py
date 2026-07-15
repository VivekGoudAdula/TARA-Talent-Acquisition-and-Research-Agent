"""TwiML builders for AI callback conversational calls."""

from __future__ import annotations

from xml.sax.saxutils import escape

from app.engagement.voice_locale import resolve_voice_locale
from app.schemas.voice_session import VoiceAgentContext


def _hints_attr(hints: list[str] | None) -> str:
    if not hints:
        return ""
    return f' hints="{escape(", ".join(hints))}"'


def build_simple_callback_twiml(context: VoiceAgentContext) -> str:
    """One-shot greeting TwiML — works with inline TwiML (no webhook needed)."""
    from app.engagement.voice_conversation_agent import VoiceConversationAgent

    locale = resolve_voice_locale(context.lang)
    greeting = escape(VoiceConversationAgent.build_opening_text(context, context.lang))

    voice = escape(locale["polly_voice"])
    language = escape(locale["polly_language"])
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<Response><Say voice="{voice}" language="{language}">{greeting}</Say></Response>'
    )


def build_conversation_twiml(
    *,
    say_text: str,
    gather_url: str,
    outcome_url: str,
    polly_voice: str,
    polly_language: str,
    speech_hints: list[str] | None = None,
) -> str:
    """Speak agent line, then listen for customer speech (no nested prompt)."""
    spoken = escape(say_text)
    voice = escape(polly_voice)
    language = escape(polly_language)
    hints = _hints_attr(speech_hints)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="{voice}" language="{language}">{spoken}</Say>
  <Gather input="speech dtmf" timeout="15" speechTimeout="3" action="{escape(gather_url)}" method="POST" actionOnEmptyResult="true" language="{language}"{hints} />
  <Redirect method="POST">{escape(outcome_url)}</Redirect>
</Response>"""


def build_redirect_twiml(*, say_text: str, redirect_url: str, polly_voice: str, polly_language: str) -> str:
    spoken = escape(say_text)
    voice = escape(polly_voice)
    language = escape(polly_language)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="{voice}" language="{language}">{spoken}</Say>
  <Redirect method="POST">{escape(redirect_url)}</Redirect>
</Response>"""


def build_end_twiml(*, say_text: str, polly_voice: str, polly_language: str) -> str:
    spoken = escape(say_text)
    voice = escape(polly_voice)
    language = escape(polly_language)
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<Response><Say voice="{voice}" language="{language}">{spoken}</Say></Response>'
    )
