"""Simulated other channels — Push, In-App, IVR (demo, no external APIs)."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.engagement.channels.base import ChannelDeliveryResult
from app.engagement.personalize_service import PersonalizedMessage
from app.schemas.engagement import EngagementLeadRecord


class PushNotificationChannel:
    CHANNEL = "Push"

    @property
    def is_configured(self) -> bool:
        return True

    def send(self, record: EngagementLeadRecord, message: PersonalizedMessage) -> ChannelDeliveryResult:
        return ChannelDeliveryResult(
            channel=self.CHANNEL,
            success=True,
            entity_id=record.entity_id,
            recipient=record.phone or record.entity_id,
            provider_sid=f"push-{uuid4().hex[:12]}",
            status="delivered_simulated",
            metadata={
                "title": f"IDBI Bank — {record.recommended_product or 'Loan Offer'}",
                "body": message.sms_body[:120],
                "simulated": True,
            },
        )


class InAppChannel:
    CHANNEL = "InApp"

    @property
    def is_configured(self) -> bool:
        return True

    def send(self, record: EngagementLeadRecord, message: PersonalizedMessage) -> ChannelDeliveryResult:
        return ChannelDeliveryResult(
            channel=self.CHANNEL,
            success=True,
            entity_id=record.entity_id,
            recipient=record.entity_id,
            provider_sid=f"inapp-{uuid4().hex[:12]}",
            status="in_app_banner_simulated",
            metadata={
                "deep_link": f"idbi://offers/{record.entity_id}",
                "preview": message.sms_body[:160],
                "simulated": True,
            },
        )


class IvrMissedCallChannel:
    CHANNEL = "IVR"

    @property
    def is_configured(self) -> bool:
        return True

    def send(self, record: EngagementLeadRecord, message: PersonalizedMessage) -> ChannelDeliveryResult:
        return ChannelDeliveryResult(
            channel=self.CHANNEL,
            success=True,
            entity_id=record.entity_id,
            recipient=record.phone,
            provider_sid=f"ivr-{uuid4().hex[:12]}",
            status="missed_call_callback_simulated",
            metadata={
                "callback_number": "1800-209-435",
                "script": message.sms_body[:200],
                "simulated": True,
                "queued_at": datetime.utcnow().isoformat(),
            },
        )
