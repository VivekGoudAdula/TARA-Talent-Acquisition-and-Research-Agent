"""Voice channel — delegates to Vanguard Voice platform (Twilio Media Streams)."""

from __future__ import annotations

from app.engagement.channels.base import ChannelDeliveryResult
from app.engagement.voice_bridge import VoiceBridge, VoiceBridgeError
from app.schemas.engagement import EngagementLeadRecord


class VoiceChannel:
  CHANNEL = "Voice"

  def __init__(self, voice_bridge: VoiceBridge | None = None) -> None:
      self._voice = voice_bridge or VoiceBridge()

  @property
  def is_configured(self) -> bool:
      return self._voice.is_configured

  def push_campaign(
      self,
      *,
      records: list[EngagementLeadRecord],
      campaign_name: str,
      agent_id: str,
      csv_text: str,
      start_campaign: bool = False,
  ) -> dict:
      return self._voice.push_campaign(
          records=records,
          campaign_name=campaign_name,
          agent_id=agent_id,
          csv_text=csv_text,
          start_campaign=start_campaign,
      )

  def health(self) -> dict:
      return self._voice.health_check()

  def to_delivery_result(self, record: EngagementLeadRecord, *, queued: bool, detail: str) -> ChannelDeliveryResult:
      return ChannelDeliveryResult(
          channel=self.CHANNEL,
          success=queued,
          entity_id=record.entity_id,
          recipient=record.phone,
          status="queued" if queued else "failed",
          error=None if queued else detail,
          metadata={"detail": detail},
      )

  def validate_ready(self) -> tuple[bool, str | None]:
      if not self.is_configured:
          return False, "VOICE_AGENT_BASE_URL not configured"
      health = self.health()
      if not health.get("reachable"):
          return False, health.get("detail", "Voice platform unreachable")
      return True, None

  def raise_if_not_ready(self) -> None:
      ok, reason = self.validate_ready()
      if not ok:
          raise VoiceBridgeError(reason or "Voice channel not ready")
