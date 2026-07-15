"""Tests for conversational Twilio voice agent."""

import unittest
from unittest.mock import MagicMock

from app.engagement.voice_conversation_agent import VoiceConversationAgent
from app.engagement.voice_locale import detect_language_switch, normalize_language, resolve_voice_locale
from app.schemas.voice_session import VoiceAgentContext


class VoiceLocaleTests(unittest.TestCase):
    def test_normalize_language(self) -> None:
        self.assertEqual(normalize_language("Hindi"), "hindi")
        self.assertEqual(normalize_language("en"), "english")

    def test_resolve_hindi_voice(self) -> None:
        locale = resolve_voice_locale("Hindi")
        self.assertEqual(locale["polly_language"], "hi-IN")

    def test_detect_language_switch(self) -> None:
        self.assertEqual(detect_language_switch("please speak hindi"), "hindi")
        self.assertIsNone(detect_language_switch("yes interested"))


class VoiceConversationAgentTests(unittest.TestCase):
    def _context(self) -> VoiceAgentContext:
        return VoiceAgentContext(
            name="Ravi Kumar",
            lang="Hindi",
            campaign="Festive Offer",
            intent="callback",
            product="Personal Loan",
            top3_reasons=["stable salary", "low debt"],
            confidence=78.0,
            eligibility="Good",
            customer_id="lead-001",
            phone="+919876543210",
            agent_instructions="Greet by name and mention callback.",
        )

    def test_opening_uses_name_and_product(self) -> None:
        db = MagicMock()
        db.voice_callback_sessions.find_one.return_value = {}
        db.voice_callback_sessions.update_one.return_value = None

        settings = MagicMock()
        settings.explainability_use_llm = False
        settings.openai_api_key = ""
        settings.azure_openai_api_key = ""

        agent = VoiceConversationAgent(db, settings=settings)
        turn = agent.generate_opening("sess-1", self._context())

        self.assertIn("Ravi", turn.reply)
        self.assertIn("Personal Loan", turn.reply)
        self.assertIn("कॉलबैक", turn.reply)
        self.assertEqual(turn.action, "continue")
        self.assertEqual(turn.polly_language, "hi-IN")

    def test_opening_english_template(self) -> None:
        ctx = self._context()
        ctx = ctx.model_copy(update={"lang": "English"})
        text = VoiceConversationAgent.build_opening_text(ctx)
        self.assertIn("Hi Ravi Kumar", text)
        self.assertIn("Shall I explain", text)
        self.assertIn("Stable income", text)

    def test_yes_explains_not_transfer(self) -> None:
        db = MagicMock()
        db.voice_callback_sessions.find_one.return_value = {
            "conversation": {
                "active_lang": "english",
                "turns": [
                    {
                        "role": "agent",
                        "text": "Hi Ravi, you requested a callback for Personal Loan. Shall I explain?",
                    }
                ],
                "turn_count": 0,
            }
        }
        db.voice_callback_sessions.update_one.return_value = None

        settings = MagicMock()
        settings.explainability_use_llm = False
        settings.openai_api_key = ""
        settings.azure_openai_api_key = ""

        agent = VoiceConversationAgent(db, settings=settings)
        turn = agent.handle_turn(
            session_id="sess-1",
            context=self._context().model_copy(update={"lang": "English"}),
            user_input="yes",
        )

        self.assertEqual(turn.action, "continue")
        self.assertIn("Personal Loan", turn.reply)

    def test_interested_transfers(self) -> None:
        db = MagicMock()
        db.voice_callback_sessions.find_one.return_value = {
            "conversation": {
                "active_lang": "english",
                "turns": [{"role": "agent", "text": "Hello"}],
                "turn_count": 0,
            }
        }
        db.voice_callback_sessions.update_one.return_value = None

        settings = MagicMock()
        settings.explainability_use_llm = False
        settings.openai_api_key = ""
        settings.azure_openai_api_key = ""

        agent = VoiceConversationAgent(db, settings=settings)
        turn = agent.handle_turn(
            session_id="sess-1",
            context=self._context(),
            user_input="yes I am interested",
        )

        self.assertEqual(turn.action, "transfer_rm")
        self.assertEqual(turn.outcome, "interested")


if __name__ == "__main__":
    unittest.main()
