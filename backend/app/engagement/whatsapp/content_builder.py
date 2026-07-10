"""Build Twilio Content variables for rich WhatsApp templates."""

from __future__ import annotations

from app.config import Settings, get_settings
from app.schemas.engagement import EngagementLeadRecord


class WhatsAppContentBuilder:
    """
    Variable schemas must match your Twilio Content Templates.

    Create templates in Twilio Console → Messaging → Content Editor:
    - main_menu: twilio/list-picker
    - loan_media: twilio/media
    - preapproved_buttons: twilio/quick-reply
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def welcome_caption(self, record: EngagementLeadRecord) -> str:
        bank = self._settings.engagement_bank_name
        return (
            f"Welcome to {bank}, {record.name}!\n\n"
            f"Your relationship manager is ready to assist with loans, "
            f"accounts, and personalized banking services."
        )

    def main_menu_variables(self, record: EngagementLeadRecord) -> dict[str, str]:
        bank = self._settings.engagement_bank_name
        return {
            "1": record.name,
            "2": bank,
        }

    def loan_media_variables(self, record: EngagementLeadRecord) -> dict[str, str]:
        """Variables for idbi_loan_media: name, amount, rate, eligibility score."""
        score = (
            f"{record.conversion_probability:.0f}"
            if record.conversion_probability is not None
            else "75"
        )
        return {
            "1": record.name,
            "2": "5,00,000",
            "3": "10.5",
            "4": score,
        }

    def carousel_variables(self, record: EngagementLeadRecord) -> dict[str, str]:
        """Deprecated — use loan_media_variables. Kept for backward compatibility."""
        return self.loan_media_variables(record)

    def preapproved_buttons_variables(self, record: EngagementLeadRecord) -> dict[str, str]:
        """Variables for idbi_preapproved_loan call-to-action template."""
        product = record.recommended_product or "Personal Loan"
        score = (
            f"{record.conversion_probability:.0f}"
            if record.conversion_probability is not None
            else "75"
        )
        return {
            "1": record.name,
            "2": product,
            "3": "500000",
            "4": "10.5",
            "5": score,
        }

    def loan_media_fallback_text(self, record: EngagementLeadRecord) -> str:
        product = record.recommended_product or "Personal Loan"
        score = (
            f"{record.conversion_probability:.0f}%"
            if record.conversion_probability is not None
            else "High"
        )
        return (
            f"*{self._settings.engagement_bank_name}*\n\n"
            f"Hi {record.name}, you're eligible for a *{product}*!\n\n"
            f"Eligible Amount: ₹5,00,000\n"
            f"Interest Rate: 10.5%\n"
            f"AI Eligibility Score: {score}\n\n"
            f"Reply *YES* to apply, *INFO* for details, or *NO* to decline."
        )

    def carousel_fallback_text(self, record: EngagementLeadRecord) -> str:
        return self.loan_media_fallback_text(record)

    def main_menu_fallback_text(self, record: EngagementLeadRecord) -> str:
        bank = self._settings.engagement_bank_name
        return (
            f"*{bank} Main Menu*\n\n"
            f"1. Loan offers\n"
            f"2. Credit card offers\n"
            f"3. Account services\n"
            f"4. Speak to advisor\n\n"
            f"Reply with a number to continue."
        )

    def credit_card_offer_variables(self, record: EngagementLeadRecord) -> dict[str, str]:
        """Variables for idbi_credit_card_offer quick-reply template."""
        card = "IDBI Aspire Credit Card"
        if record.recommended_product and "card" in record.recommended_product.lower():
            card = record.recommended_product
        score = (
            f"{record.conversion_probability:.0f}"
            if record.conversion_probability is not None
            else "75"
        )
        return {
            "1": record.name,
            "2": card,
            "3": "200000",
            "4": "Zero annual fee for first year",
            "5": score,
        }

    def credit_card_offer_fallback_text(self, record: EngagementLeadRecord) -> str:
        vars_ = self.credit_card_offer_variables(record)
        return (
            f"*{self._settings.engagement_bank_name}*\n\n"
            f"Hi {vars_['1']}, you're pre-approved for the *{vars_['2']}*!\n\n"
            f"Credit Limit: Rs {vars_['3']}\n"
            f"Key Benefit: {vars_['4']}\n"
            f"Eligibility Score: {vars_['5']}\n\n"
            f"Reply *Apply Now* or *View Benefits*."
        )

    def preapproved_fallback_text(self, record: EngagementLeadRecord) -> str:
        product = record.recommended_product or "Personal Loan"
        score = (
            f"{record.conversion_probability:.0f}%"
            if record.conversion_probability is not None
            else "High"
        )
        return (
            f"*{self._settings.engagement_bank_name}*\n\n"
            f"Hi {record.name}, you're *pre-approved* for a *{product}*!\n\n"
            f"Eligible Amount: ₹5,00,000\n"
            f"Interest Rate: 10.5%\n"
            f"AI Eligibility Score: {score}\n\n"
            f"Reply *Talk to us* for a callback from our AI specialist."
        )
