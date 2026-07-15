"""Personalized outreach copy from Tara intelligence + explainability."""



from __future__ import annotations



from dataclasses import dataclass

from pathlib import Path

from string import Template



from app.config import Settings, get_settings
from app.engagement.banking_copy import (
    format_inr_amount,
    humanize_reasons,
    professional_insight,
    repayment_label,
)
from app.schemas.engagement import EngagementLeadRecord



_TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "lending_offer.html"





@dataclass

class PersonalizedMessage:

    sms_body: str

    whatsapp_body: str

    email_subject: str

    email_text: str

    email_html: str

    whatsapp_content_variables: dict[str, str] | None = None





class PersonalizeService:

    """Build channel-specific messages using professional banking language."""

    def __init__(self, settings: Settings | None = None, db=None) -> None:

        self._settings = settings or get_settings()
        self._db = db

        self._html_template = self._load_template()



    def build(self, record: EngagementLeadRecord) -> PersonalizedMessage:
        bank = self._settings.engagement_bank_name
        name = record.name or "Customer"
        product = record.recommended_product or "Personal Loan"
        reasons = humanize_reasons(record.reason_codes)
        insight = professional_insight(record)
        repayment = repayment_label(record.repayment_capacity)
        eligible_amount = format_inr_amount(self._settings.engagement_default_eligible_amount)
        interest_rate = f"{self._settings.engagement_default_interest_rate:.2f}% p.a."
        offer_valid = self._settings.engagement_offer_valid_until

        apply_url = self._settings.engagement_email_cta_url
        callback_url = self._build_callback_url(record)
        ai_banker_url = f"tel:{self._settings.twilio_from_number}"

        callback_phone = self._format_callback_phone(self._settings.engagement_callback_phone)

        # Simple explainability without jargon
        reasons_lower = [r.strip().lower().replace("_", " ") for r in record.reason_codes]
        if "high income" in reasons_lower or "stable income" in reasons_lower or "stable salary" in reasons_lower:
            why_eligible_str = "strong income profile"
        elif "low debt" in reasons_lower:
            why_eligible_str = "comfortable debt position"
        else:
            why_eligible_str = "consistent banking relationship"

        sms_body = (
            f"Dear {name}, based on your {why_eligible_str}, you are pre-approved for a {product} "
            f"of up to {eligible_amount} at {interest_rate} interest. "
            f"To apply, click: {apply_url} or request a callback by calling support at {callback_phone}. "
            f"Regards, {bank}."
        )

        whatsapp_body = (
            f"Dear {name},\n\n"
            f"Greetings from {bank}! We are delighted to offer you a personalized pre-qualified *{product}*.\n\n"
            f"📈 *Offer Details:*\n"
            f"• *Eligible Amount:* {eligible_amount}\n"
            f"• *Interest Rate:* {interest_rate}\n"
            f"• *Validity:* Until {offer_valid}\n\n"
            f"🔍 *Why you qualify:*\n"
            f"This pre-qualification is based on your {why_eligible_str}.\n\n"
            f"🎁 *Benefits:*\n"
            f"• Instant digital disbursement\n"
            f"• Zero prepayment penalties\n"
            f"• Competitive interest rates\n\n"
            f"To proceed, select an option below:\n\n"
            f"1️⃣ *Apply Now:* {apply_url}\n"
            f"2️⃣ *Request Callback:* {callback_url}\n"
            f"3️⃣ *Connect With Bank:* {ai_banker_url}"
        )

        email_subject = f"{bank} — Pre-qualified {product} for {name}"
        email_text = (
            f"Dear {name},\n\n"
            f"We are pleased to share a pre-qualified {product} offer from {bank}.\n\n"
            f"Eligible amount: {eligible_amount}\n"
            f"Interest rate: {interest_rate}\n"
            f"Offer valid till: {offer_valid}\n\n"
            f"Based on your {why_eligible_str}, you have been selected for this exclusive offer.\n\n"
            f"Apply now: {apply_url}\n"
            f"Request callback: {callback_url}\n"
            f"Connect With Bank: {ai_banker_url}\n\n"
            f"Regards,\n{bank} Relationship Team"
        )

        email_html = self._render_html(
            bank=bank,
            name=name,
            product=product,
            reasons=reasons,
            insight=insight,
            eligible_amount=eligible_amount,
            interest_rate=interest_rate,
            offer_valid_until=offer_valid,
            apply_url=apply_url,
            callback_url=callback_url,
            ai_banker_url=ai_banker_url,
        )

        return PersonalizedMessage(
            sms_body=sms_body,
            whatsapp_body=whatsapp_body,
            email_subject=email_subject,
            email_text=email_text,
            email_html=email_html,
            whatsapp_content_variables={"1": name, "2": product},
        )

    def _build_callback_url(self, record: EngagementLeadRecord) -> str:
        if self._settings.engagement_callback_url and "{token}" not in self._settings.engagement_callback_url:
            return self._settings.engagement_callback_url

        if self._db is not None:
            from app.engagement.callback_links import CallbackLinkService

            return CallbackLinkService(self._db, self._settings).create_link(
                phone=record.phone or "",
                entity_id=record.entity_id,
                entity_type=record.entity_type,
                source_channel="Email",
            )

        from app.engagement.callback_links import resolve_public_api_base
        from urllib.parse import quote

        base = resolve_public_api_base(self._settings)
        phone = quote(record.phone or "", safe="")
        entity_id = quote(record.entity_id or "", safe="")
        entity_type = quote(record.entity_type or "External", safe="")
        return (
            f"{base}/api/engagement/callback/trigger"
            f"?phone={phone}&entity_id={entity_id}&entity_type={entity_type}"
            f"&source_channel=Email"
        )

    def _format_callback_phone(self, phone: str) -> str:
        digits = "".join(ch for ch in phone if ch.isdigit())
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        if len(digits) == 10 and digits.startswith("1800"):
            return f"{digits[:4]}-{digits[4:7]}-{digits[7:]}"
        if len(digits) == 10:
            return f"+91 {digits[:5]} {digits[5:]}"
        return phone.strip() or "+91 1800-209-435"

    def _render_html(
        self,
        *,
        bank: str,
        name: str,
        product: str,
        reasons: str,
        insight: str,
        eligible_amount: str,
        interest_rate: str,
        offer_valid_until: str,
        apply_url: str,
        callback_url: str,
        ai_banker_url: str,
    ) -> str:
        return Template(self._html_template).safe_substitute(
            bank_name=bank,
            customer_name=name,
            product_name=product,
            reason_summary=reasons,
            insight=insight,
            eligible_amount=eligible_amount,
            interest_rate=interest_rate,
            offer_valid_until=offer_valid_until,
            apply_url=apply_url,
            callback_url=callback_url,
            ai_banker_url=ai_banker_url,
        )



    def _load_template(self) -> str:

        if _TEMPLATE_PATH.exists():

            return _TEMPLATE_PATH.read_text(encoding="utf-8")

        return (

            "<html><body><h2>${bank_name}</h2>"

            "<p>Dear ${customer_name},</p>"

            "<p>Pre-qualified offer: <strong>${product_name}</strong></p>"

            "<p>${insight}</p></body></html>"

        )


