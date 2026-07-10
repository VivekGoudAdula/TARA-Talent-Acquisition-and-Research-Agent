"""Digital & channel analytics output schemas."""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class DigitalBankingResult(BaseModel):
    upi_usage_score: Decimal
    net_banking_usage_score: Decimal
    mobile_banking_usage_score: Decimal
    debit_card_usage_score: Decimal
    credit_card_usage_score: Decimal
    atm_usage_score: Decimal
    branch_banking_score: Decimal
    digital_payment_ratio: Decimal
    cash_usage_ratio: Decimal
    digital_adoption_score: Decimal
    digital_maturity: str


class DigitalEngagementResult(BaseModel):
    digital_engagement_score: Decimal
    online_banking_frequency: Decimal
    upi_frequency: Decimal
    card_usage_frequency: Decimal
    mobile_app_dependency: Decimal
    digital_transaction_consistency: Decimal


class CommunicationReadinessResult(BaseModel):
    voice_readiness_score: Decimal
    sms_readiness_score: Decimal
    whatsapp_readiness_score: Decimal
    email_readiness_score: Decimal
    app_notification_readiness_score: Decimal


class ContactPolicy(BaseModel):
    preferred_channel: str
    secondary_channel: str
    preferred_time: str
    preferred_day: str
    maximum_contact_frequency: str


class DigitalChannelProfile(BaseModel):
    customer_id: UUID
    digital_adoption_score: Decimal
    digital_maturity: str
    preferred_channel: str
    secondary_channel: str
    preferred_contact_time: str
    preferred_contact_day: str
    voice_readiness_score: Decimal
    sms_readiness_score: Decimal
    whatsapp_readiness_score: Decimal
    email_readiness_score: Decimal
    engagement_score: Decimal
    digital_banking: DigitalBankingResult | None = None
    digital_engagement: DigitalEngagementResult | None = None
    communication_readiness: CommunicationReadinessResult | None = None
    contact_policy: ContactPolicy | None = None


class DigitalChannelAnalyticsResponse(BaseModel):
    message: str
    channel_profile: DigitalChannelProfile


class DigitalChannelBuildAllResponse(BaseModel):
    message: str
    customers_processed: int
    customers_succeeded: int
    customers_failed: int
