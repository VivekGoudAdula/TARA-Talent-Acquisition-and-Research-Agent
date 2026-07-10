"""Email channel — SMTP (smtplib) or SendGrid with HTML templates."""

from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import Settings, get_settings
from app.engagement.channels.base import ChannelDeliveryResult
from app.engagement.personalize_service import PersonalizedMessage
from app.schemas.engagement import EngagementLeadRecord
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class EmailChannel:
  CHANNEL = "Email"

  def __init__(self, settings: Settings | None = None) -> None:
      self._settings = settings or get_settings()

  @property
  def is_configured(self) -> bool:
      if self._settings.email_provider == "sendgrid":
          return bool(self._settings.sendgrid_api_key and self._settings.email_from_address)
      return bool(
          self._settings.smtp_host
          and self._settings.email_from_address
          and (self._settings.smtp_username or self._settings.smtp_password)
      )

  def send(
      self,
      record: EngagementLeadRecord,
      message: PersonalizedMessage,
  ) -> ChannelDeliveryResult:
      from app.engagement.test_routing import TestRecipientRouter

      router = TestRecipientRouter(self._settings)
      original_email = (record.email or "").strip()
      recipient = (
          router.email_to(original_email, entity_type=record.entity_type)
          if router.enabled
          else original_email
      )
      if not recipient:
          return ChannelDeliveryResult(
              channel=self.CHANNEL,
              success=False,
              entity_id=record.entity_id,
              recipient="",
              status="failed",
              error="No email address on record",
          )

      try:
          if self._settings.email_provider == "sendgrid":
              sid = self._send_sendgrid(recipient, message)
          else:
              sid = self._send_smtp(recipient, message)
          return ChannelDeliveryResult(
              channel=self.CHANNEL,
              success=True,
              entity_id=record.entity_id,
              recipient=recipient,
              provider_sid=sid,
              status="sent",
              metadata={
                  "subject": message.email_subject,
                  "original_email": original_email if router.enabled else None,
                  "test_routed": router.enabled,
              },
          )
      except Exception as exc:
          logger.warning("Email failed entity_id=%s: %s", record.entity_id, exc)
          return ChannelDeliveryResult(
              channel=self.CHANNEL,
              success=False,
              entity_id=record.entity_id,
              recipient=recipient,
              status="failed",
              error=str(exc),
          )

  def _send_smtp(self, to_email: str, message: PersonalizedMessage) -> str:
      msg = MIMEMultipart("alternative")
      msg["Subject"] = message.email_subject
      msg["From"] = self._settings.email_from_address
      msg["To"] = to_email
      msg.attach(MIMEText(message.email_text, "plain", "utf-8"))
      msg.attach(MIMEText(message.email_html, "html", "utf-8"))

      with smtplib.SMTP(self._settings.smtp_host, self._settings.smtp_port, timeout=30) as server:
          if self._settings.smtp_use_tls:
              server.starttls()
          if self._settings.smtp_username:
              server.login(self._settings.smtp_username, self._settings.smtp_password)
          server.sendmail(self._settings.email_from_address, [to_email], msg.as_string())
      return f"smtp-{to_email}"

  def _send_sendgrid(self, to_email: str, message: PersonalizedMessage) -> str:
      import httpx

      payload = {
          "personalizations": [{"to": [{"email": to_email}]}],
          "from": {"email": self._settings.email_from_address},
          "subject": message.email_subject,
          "content": [
              {"type": "text/plain", "value": message.email_text},
              {"type": "text/html", "value": message.email_html},
          ],
      }
      response = httpx.post(
          "https://api.sendgrid.com/v3/mail/send",
          headers={
              "Authorization": f"Bearer {self._settings.sendgrid_api_key}",
              "Content-Type": "application/json",
          },
          json=payload,
          timeout=30.0,
      )
      response.raise_for_status()
      return response.headers.get("X-Message-Id", f"sendgrid-{to_email}")
