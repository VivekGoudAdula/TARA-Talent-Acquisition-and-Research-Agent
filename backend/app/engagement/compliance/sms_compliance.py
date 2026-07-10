"""SMS DLT compliance gate — consent, approved templates, sender validation."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.config import Settings, get_settings
from app.engagement.personalize_service import PersonalizedMessage
from app.schemas.engagement import EngagementLeadRecord


@dataclass
class SmsComplianceResult:
    allowed: bool
    checks: dict[str, bool]
    reasons: list[str]
    template_id: str | None = None
    sender_id: str | None = None


class SmsComplianceGate:
    """
    Demonstrates production banking SMS readiness without a live DLT portal.

    Validates: marketing consent, approved sender ID, template match, message length.
    """

    DEFAULT_TEMPLATES: dict[str, str] = {
        "lending_offer": r"Dear .+, .+ IDBI Bank .+ loan .+ offer .+",
        "kyc_nudge": r"Dear .+, thank you for your interest .+",
        "rm_confirmation": r"Dear .+, thank you for your interest .+ Relationship Manager .+",
        "generic_engagement": r"Dear .+, .+ IDBI Bank .+",
    }

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        raw_senders = getattr(self._settings, "sms_dlt_sender_ids", "") or ""
        self._approved_senders = [s.strip() for s in raw_senders.split(",") if s.strip()]
        if not self._approved_senders and self._settings.twilio_from_number:
            self._approved_senders = [self._settings.twilio_from_number]

        raw_templates = getattr(self._settings, "sms_dlt_template_ids", "") or ""
        self._approved_template_ids = [t.strip() for t in raw_templates.split(",") if t.strip()]
        if not self._approved_template_ids:
            self._approved_template_ids = [
                "IDBI_LENDING_OFFER_V1",
                "IDBI_KYC_NUDGE_V1",
                "IDBI_RM_CONFIRM_V1",
            ]

    def validate(
        self,
        record: EngagementLeadRecord,
        message: PersonalizedMessage,
        *,
        template_key: str = "generic_engagement",
    ) -> SmsComplianceResult:
        template_id = self._resolve_template_id(template_key)
        sender = self._settings.twilio_from_number or ""
        if getattr(self._settings, "engagement_test_mode", False):
            return SmsComplianceResult(
                allowed=True,
                checks={
                    "consent": True,
                    "sender_registered": True,
                    "template_approved": True,
                    "template_match": True,
                    "length_ok": True,
                    "phone_valid": True,
                },
                reasons=[],
                template_id=template_id,
                sender_id=sender,
            )

        checks: dict[str, bool] = {}
        reasons: list[str] = []

        checks["consent"] = bool(record.consent)
        if not checks["consent"]:
            reasons.append("Marketing consent not granted for SMS outreach")

        sender = self._settings.twilio_from_number or ""
        checks["sender_registered"] = bool(sender) and (
            not self._approved_senders or sender in self._approved_senders
        )
        if not checks["sender_registered"]:
            reasons.append(f"Sender {sender!r} not in approved DLT sender list")

        template_id = self._resolve_template_id(template_key)
        checks["template_approved"] = template_id in self._approved_template_ids
        if not checks["template_approved"]:
            reasons.append(f"Template {template_id} not in approved DLT registry")

        body = self._apply_template_vars(message.sms_body, record.name)
        pattern = self.DEFAULT_TEMPLATES.get(template_key, self.DEFAULT_TEMPLATES["generic_engagement"])
        checks["template_match"] = bool(re.search(pattern, body, re.IGNORECASE | re.DOTALL))
        if not checks["template_match"]:
            reasons.append("Message body does not match approved DLT template pattern")

        checks["length_ok"] = len(body) <= 1600
        if not checks["length_ok"]:
            reasons.append("SMS exceeds maximum permitted length (1600 chars)")

        digits = "".join(c for c in (record.phone or "") if c.isdigit())
        checks["phone_valid"] = len(digits) >= 10
        if not checks["phone_valid"]:
            reasons.append("Invalid recipient phone number")

        allowed = all(checks.values())
        return SmsComplianceResult(
            allowed=allowed,
            checks=checks,
            reasons=reasons,
            template_id=template_id,
            sender_id=sender,
        )

    def _resolve_template_id(self, template_key: str) -> str:
        mapping = {
            "lending_offer": "IDBI_LENDING_OFFER_V1",
            "kyc_nudge": "IDBI_KYC_NUDGE_V1",
            "rm_confirmation": "IDBI_RM_CONFIRM_V1",
            "generic_engagement": "IDBI_LENDING_OFFER_V1",
        }
        return mapping.get(template_key, "IDBI_LENDING_OFFER_V1")

    @staticmethod
    def _apply_template_vars(body: str, name: str) -> str:
        return body.replace("{name}", name or "Customer")
