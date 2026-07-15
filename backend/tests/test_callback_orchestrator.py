"""Unit tests for AI Callback orchestration."""

import unittest
from unittest.mock import MagicMock, patch

from app.engagement.callback_orchestrator import CallbackOrchestrator
from app.engagement.voice_context_service import VoiceContextService
from app.schemas.engagement import EngagementLeadRecord
from app.schemas.voice_session import VoiceAgentContext


class VoiceContextServiceTests(unittest.TestCase):
    def test_builds_callback_context(self) -> None:
        db = MagicMock()
        db.external_leads.find_one.return_value = {
            "preferred_language": "Hindi",
            "campaign": "Festive Offer",
        }
        export = MagicMock()
        export.build_record_for_entity.return_value = EngagementLeadRecord(
            entity_type="External",
            entity_id="lead-001",
            phone="+919876543210",
            name="Ravi Kumar",
            recommended_product="Personal Loan",
            conversion_probability=78.0,
            reason_codes=["stable_salary", "low_debt"],
            repayment_capacity="High",
            talking_points="Strong profile for personal loan.",
            consent=True,
        )

        with patch(
            "app.engagement.voice_context_service.EngagementExportService",
            return_value=export,
        ):
            svc = VoiceContextService(db)
            ctx = svc.load_context(
                entity_id="lead-001",
                entity_type="External",
                phone="+919876543210",
                source_channel="WhatsApp",
            )

        self.assertEqual(ctx.name, "Ravi Kumar")
        self.assertEqual(ctx.lang, "Hindi")
        self.assertEqual(ctx.intent, "callback")
        self.assertEqual(ctx.product, "Personal Loan")
        self.assertEqual(ctx.customer_id, "lead-001")
        self.assertEqual(ctx.eligibility, "Good")
        self.assertEqual(len(ctx.top3_reasons), 2)
        self.assertIn("context", ctx.agent_instructions.lower())
        self.assertIn("transfer", ctx.agent_instructions.lower())
        self.assertIn("WhatsApp", ctx.agent_instructions)


class CallbackOrchestratorTests(unittest.TestCase):
    def test_start_callback_success(self) -> None:
        db = MagicMock()
        db.voice_callback_dedup.find_one.return_value = None
        db.voice_callback_sessions.insert_one.return_value = None
        db.voice_callback_sessions.update_one.return_value = None
        db.voice_callback_dedup.insert_one.return_value = None

        voice = MagicMock()
        voice.is_configured = True
        voice.create_session.return_value = {"session_id": "ext-1"}
        voice.initiate_callback_call.return_value = {"call_sid": "CA123", "status": "queued"}

        context = VoiceAgentContext(
            name="Ravi",
            customer_id="lead-001",
            entity_type="External",
            phone="+919876543210",
            intent="callback",
            product="Personal Loan",
        )

        settings = MagicMock()
        settings.engagement_test_mode = True

        with patch.object(CallbackOrchestrator, "__init__", lambda self, db, voice_bridge=None, settings=None: None):
            orch = CallbackOrchestrator.__new__(CallbackOrchestrator)
            orch._db = db
            orch._voice = voice
            orch._settings = settings
            orch._context_svc = MagicMock()
            orch._context_svc.load_context.return_value = context

            result = orch.start_callback(
                phone="+919876543210",
                entity_id="lead-001",
                entity_type="External",
                source_channel="Email",
            )

        self.assertTrue(result.triggered)
        self.assertEqual(result.call_sid, "CA123")
        self.assertIn("total", result.timing_ms)
        voice.initiate_callback_call.assert_called_once()

    def test_skip_dedup_bypasses_recent_callback(self) -> None:
        db = MagicMock()
        db.voice_callback_dedup.find_one.return_value = {
            "dedup_key": "lead-001:9876543210",
            "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        }
        db.voice_callback_sessions.insert_one.return_value = None
        db.voice_callback_sessions.update_one.return_value = None
        db.voice_callback_dedup.insert_one.return_value = None

        voice = MagicMock()
        voice.is_configured = True
        voice.create_session.return_value = {"session_id": "ext-1"}
        voice.initiate_callback_call.return_value = {"call_sid": "CA456", "status": "queued"}

        context = VoiceAgentContext(
            name="Ravi",
            customer_id="lead-001",
            entity_type="External",
            phone="+919876543210",
            intent="callback",
            product="Personal Loan",
        )

        settings = MagicMock()
        settings.engagement_test_mode = False

        with patch.object(CallbackOrchestrator, "__init__", lambda self, db, voice_bridge=None, settings=None: None):
            orch = CallbackOrchestrator.__new__(CallbackOrchestrator)
            orch._db = db
            orch._voice = voice
            orch._settings = settings
            orch._twilio_voice = MagicMock()
            orch._twilio_voice.is_configured = False
            orch._context_svc = MagicMock()
            orch._context_svc.load_context.return_value = context
            orch._create_session = MagicMock(return_value={})
            orch._place_call = MagicMock(return_value=({"call_sid": "CA456"}, "vanguard"))
            orch._mark_callback = MagicMock()

            blocked = orch.start_callback(
                phone="+919876543210",
                entity_id="lead-001",
                source_channel="Email",
            )
            allowed = orch.start_callback(
                phone="+919876543210",
                entity_id="lead-001",
                source_channel="Email",
                skip_dedup=True,
            )

        self.assertFalse(blocked.triggered)
        self.assertEqual(blocked.reason, "dedup_recent")
        self.assertTrue(allowed.triggered)
        self.assertEqual(allowed.call_sid, "CA456")


if __name__ == "__main__":
    unittest.main()
