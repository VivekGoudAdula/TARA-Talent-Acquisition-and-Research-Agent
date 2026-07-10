"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    """Central application settings."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    mongodb_uri: str = Field(default="", alias="MONGODB_URI")
    mongodb_db_name: str = Field(default="Tara", alias="MONGODB_DB_NAME")

    app_name: str = "Tara Customer 360 Intelligence Engine"
    app_version: str = "1.0.0"
    log_level: str = "INFO"

    external_leads_excel_path: Path = Field(
        default=Path(__file__).resolve().parent.parent / "external_leads_1000.xlsx"
    )
    customer_master_excel_path: Path = Field(
        default=Path(__file__).resolve().parent.parent / "customer_master_1000.xlsx",
        alias="CUSTOMER_MASTER_EXCEL_PATH",
    )
    transaction_history_excel_path: Path = Field(
        default=Path(__file__).resolve().parent.parent / "transaction_history_15000.xlsx",
        alias="TRANSACTION_HISTORY_EXCEL_PATH",
    )
    loan_history_excel_path: Path = Field(
        default=Path(__file__).resolve().parent.parent / "loan_history_1000.xlsx",
        alias="LOAN_HISTORY_EXCEL_PATH",
    )
    digital_activity_excel_path: Path = Field(
        default=Path(__file__).resolve().parent.parent / "digital_activity_1000.xlsx",
        alias="DIGITAL_ACTIVITY_EXCEL_PATH",
    )

    expected_customer_count: int = Field(default=1000, alias="EXPECTED_CUSTOMER_COUNT")
    expected_lead_count: int = Field(default=1000, alias="EXPECTED_LEAD_COUNT")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o", alias="OPENAI_MODEL")

    azure_openai_endpoint: str = Field(default="", alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: str = Field(default="", alias="AZURE_OPENAI_API_KEY")
    azure_api_version: str = Field(default="2024-12-01-preview", alias="AZURE_API_VERSION")
    azure_gpt_deployment: str = Field(default="gpt-4o", alias="AZURE_GPT_DEPLOYMENT")
    explainability_use_llm: bool = Field(default=True, alias="EXPLAINABILITY_USE_LLM")

    voice_agent_base_url: str = Field(default="http://localhost:9000", alias="VOICE_AGENT_BASE_URL")
    voice_agent_default_agent_id: str = Field(
        default="lending_offer_agent", alias="VOICE_AGENT_DEFAULT_AGENT_ID"
    )

    # Twilio — SMS, WhatsApp, Voice (voice execution via bank/bank + Media Streams)
    twilio_account_sid: str = Field(default="", alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = Field(default="", alias="TWILIO_AUTH_TOKEN")
    twilio_from_number: str = Field(default="", alias="TWILIO_FROM_NUMBER")
    twilio_whatsapp_from: str = Field(default="", alias="TWILIO_WHATSAPP_FROM")
    twilio_whatsapp_content_sid: str = Field(default="", alias="TWILIO_WHATSAPP_CONTENT_SID")
    twilio_whatsapp_use_template: bool = Field(
        default=False,
        alias="TWILIO_WHATSAPP_USE_TEMPLATE",
        description="False = send custom free-form WhatsApp body (sandbox / 24h session)",
    )

    # Rich WhatsApp — Content Template SIDs (create in Twilio Content Editor)
    whatsapp_welcome_media_url: str = Field(default="", alias="WHATSAPP_WELCOME_MEDIA_URL")
    whatsapp_content_main_menu: str = Field(default="", alias="WHATSAPP_CONTENT_MAIN_MENU")
    whatsapp_content_loan_media: str = Field(default="", alias="WHATSAPP_CONTENT_LOAN_MEDIA")
    whatsapp_content_preapproved_buttons: str = Field(
        default="", alias="WHATSAPP_CONTENT_PREAPPROVED_BUTTONS"
    )
    whatsapp_content_credit_card_offer: str = Field(
        default="", alias="WHATSAPP_CONTENT_CREDIT_CARD_OFFER"
    )

    # Email — smtp or sendgrid
    email_provider: str = Field(default="smtp", alias="EMAIL_PROVIDER")
    email_from_address: str = Field(default="", alias="EMAIL_FROM_ADDRESS")
    smtp_host: str = Field(default="", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_username: str = Field(default="", alias="SMTP_USERNAME")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")
    sendgrid_api_key: str = Field(default="", alias="SENDGRID_API_KEY")

    engagement_bank_name: str = Field(default="IDBI Bank", alias="ENGAGEMENT_BANK_NAME")
    engagement_email_cta_url: str = Field(
        default="https://www.idbi.bank.in/",
        alias="ENGAGEMENT_EMAIL_CTA_URL",
    )
    engagement_callback_url: str = Field(
        default="",
        alias="ENGAGEMENT_CALLBACK_URL",
        description="Callback CTA link in email/SMS. Falls back to tel: ENGAGEMENT_CALLBACK_PHONE",
    )
    engagement_callback_phone: str = Field(
        default="+911800209435",
        alias="ENGAGEMENT_CALLBACK_PHONE",
    )
    engagement_default_eligible_amount: int = Field(
        default=1_500_000,
        alias="ENGAGEMENT_DEFAULT_ELIGIBLE_AMOUNT",
    )
    engagement_default_interest_rate: float = Field(
        default=8.25,
        alias="ENGAGEMENT_DEFAULT_INTEREST_RATE",
    )
    engagement_offer_valid_until: str = Field(
        default="31 Jul 2026",
        alias="ENGAGEMENT_OFFER_VALID_UNTIL",
    )
    engagement_test_mode: bool = Field(
        default=False,
        alias="ENGAGEMENT_TEST_MODE",
        description="When true, route WhatsApp/SMS/Email to test recipients from env",
    )
    engagement_whatsapp_override_phone: str = Field(
        default="",
        alias="ENGAGEMENT_WHATSAPP_OVERRIDE_PHONE",
        description="All WhatsApp outreach goes to this number (e.g. +918897371942)",
    )
    engagement_sms_test_phones: str = Field(
        default="",
        alias="ENGAGEMENT_SMS_TEST_PHONES",
        description="Comma-separated phones for SMS round-robin during test mode",
    )
    engagement_email_test_addresses: str = Field(
        default="",
        alias="ENGAGEMENT_EMAIL_TEST_ADDRESSES",
        description="Comma-separated emails for Email round-robin during test mode",
    )
    engagement_test_offset: int = Field(
        default=0,
        ge=0,
        alias="ENGAGEMENT_TEST_OFFSET",
        description="Skip first N customers/leads per type when building outreach batch",
    )

    pipeline_auto_run_on_import: bool = Field(
        default=False,
        alias="PIPELINE_AUTO_RUN_ON_IMPORT",
    )
    sms_dlt_sender_ids: str = Field(
        default="",
        alias="SMS_DLT_SENDER_IDS",
        description="Comma-separated approved sender IDs (defaults to TWILIO_FROM_NUMBER)",
    )
    sms_dlt_template_ids: str = Field(
        default="",
        alias="SMS_DLT_TEMPLATE_IDS",
        description="Comma-separated approved DLT template IDs",
    )
    learning_scheduler_enabled: bool = Field(
        default=False,
        alias="LEARNING_SCHEDULER_ENABLED",
    )
    learning_scheduler_interval_hours: int = Field(
        default=24,
        alias="LEARNING_SCHEDULER_INTERVAL_HOURS",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
