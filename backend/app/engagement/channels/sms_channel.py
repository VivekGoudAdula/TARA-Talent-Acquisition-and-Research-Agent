"""Twilio SMS channel for engagement outreach."""

from __future__ import annotations

from app.config import Settings, get_settings
from app.engagement.channels.base import ChannelDeliveryResult
from app.engagement.channels.phone_utils import normalize_e164
from app.engagement.channels.twilio_client import TwilioMessagingClient
from app.engagement.compliance.sms_compliance import SmsComplianceGate
from app.engagement.personalize_service import PersonalizedMessage
from app.schemas.engagement import EngagementLeadRecord


class SMSChannel:
  CHANNEL = "SMS"

  def __init__(
      self,
      settings: Settings | None = None,
      twilio: TwilioMessagingClient | None = None,
      compliance: SmsComplianceGate | None = None,
  ) -> None:
      self._settings = settings or get_settings()
      self._twilio = twilio or TwilioMessagingClient(self._settings)
      self._compliance = compliance or SmsComplianceGate(self._settings)

  @property
  def is_configured(self) -> bool:
      return self._twilio.is_configured and bool(self._settings.twilio_from_number)

  def compliance_check(
      self,
      record: EngagementLeadRecord,
      message: PersonalizedMessage,
      *,
      template_key: str = "generic_engagement",
  ):
      return self._compliance.validate(record, message, template_key=template_key)

  def send(
      self,
      record: EngagementLeadRecord,
      message: PersonalizedMessage,
      *,
      template_key: str = "generic_engagement",
      skip_compliance: bool = False,
  ) -> ChannelDeliveryResult:
      from app.engagement.test_routing import TestRecipientRouter

      router = TestRecipientRouter(self._settings)
      original_phone = record.phone
      phone = (
          router.sms_to(record.phone, entity_type=record.entity_type)
          if router.enabled
          else normalize_e164(record.phone)
      )
      if not phone:
          return ChannelDeliveryResult(
              channel=self.CHANNEL,
              success=False,
              entity_id=record.entity_id,
              recipient="",
              status="failed",
              error="Invalid phone number",
          )

      if not skip_compliance:
          compliance = self._compliance.validate(record, message, template_key=template_key)
          if not compliance.allowed:
              return ChannelDeliveryResult(
                  channel=self.CHANNEL,
                  success=False,
                  entity_id=record.entity_id,
                  recipient=phone,
                  status="blocked_dlt",
                  error="; ".join(compliance.reasons),
                  metadata={
                      "dlt_checks": compliance.checks,
                      "template_id": compliance.template_id,
                      "sender_id": compliance.sender_id,
                  },
              )

      ok, sid, status_or_error = self._twilio.send_message(
          to=phone,
          from_=self._settings.twilio_from_number,
          body=message.sms_body,
      )
      return ChannelDeliveryResult(
          channel=self.CHANNEL,
          success=ok,
          entity_id=record.entity_id,
          recipient=phone,
          provider_sid=sid,
          status=status_or_error if ok else "failed",
          error=None if ok else status_or_error,
          metadata={
              "product": record.recommended_product,
              "dlt_template_id": self._compliance._resolve_template_id(template_key),
              "original_phone": original_phone if router.enabled else None,
              "test_routed": router.enabled,
          },
      )
