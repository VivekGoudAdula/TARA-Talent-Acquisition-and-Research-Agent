"""Custom application exceptions."""

from uuid import UUID


class AppException(Exception):
    """Base application exception."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class CustomerNotFoundError(AppException):
    """Raised when a customer_id does not exist in core banking tables."""

    def __init__(self, customer_id: UUID) -> None:
        super().__init__(f"Customer not found: {customer_id}")
        self.customer_id = customer_id


class ProfileNotFoundError(AppException):
    """Raised when a Customer360 profile does not exist."""

    def __init__(self, customer_id: UUID) -> None:
        super().__init__(f"Customer360 profile not found for customer: {customer_id}")
        self.customer_id = customer_id


class BehaviourSummaryNotFoundError(AppException):
    """Raised when behaviour summary has not been built for a profile."""

    def __init__(self, profile_id: UUID) -> None:
        super().__init__(f"Behaviour summary not found for profile: {profile_id}")
        self.profile_id = profile_id


class UnifiedProfileNotFoundError(AppException):
    """Raised when a profile_id is not found in internal or external tables."""

    def __init__(self, profile_id: UUID) -> None:
        super().__init__(f"Profile not found: {profile_id}")
        self.profile_id = profile_id


class LeadNotFoundError(AppException):
    """Raised when an external lead does not exist."""

    def __init__(self, lead_id: UUID) -> None:
        super().__init__(f"External lead not found: {lead_id}")
        self.lead_id = lead_id


class ExternalProfileNotFoundError(AppException):
    """Raised when an enriched external profile does not exist."""

    def __init__(self, lead_id: UUID) -> None:
        super().__init__(f"External customer profile not found for lead: {lead_id}")
        self.lead_id = lead_id


class ExternalAnalyticsNotFoundError(AppException):
    """Raised when external lead analytics have not been computed."""

    def __init__(self, lead_id: UUID) -> None:
        super().__init__(f"External lead analytics not found for lead: {lead_id}")
        self.lead_id = lead_id


class ExternalIntelligenceNotFoundError(AppException):
    """Raised when external lead intelligence validation has not been run."""

    def __init__(self, lead_id: UUID) -> None:
        super().__init__(f"External lead intelligence not found for lead: {lead_id}")
        self.lead_id = lead_id


class MLDatasetNotFoundError(AppException):
    """Raised when the ML training dataset has not been built yet."""

    def __init__(self) -> None:
        super().__init__("ML training dataset not found — run POST /api/ml/dataset/build first")


class RepaymentModelNotFoundError(AppException):
    """Raised when the repayment capacity model has not been trained yet."""

    def __init__(self) -> None:
        super().__init__(
            "Repayment capacity model not found — run POST /api/ml/repayment/train first"
        )


class ConversionModelNotFoundError(AppException):
    """Raised when the lead conversion model has not been trained yet."""

    def __init__(self) -> None:
        super().__init__(
            "Lead conversion model not found — run POST /api/ml/conversion/train first"
        )


class ConversionDataNotFoundError(AppException):
    """Raised when no external leads exist for conversion model training."""

    def __init__(self) -> None:
        super().__init__(
            "No external leads found for conversion training — import leads first"
        )


class ExplainabilityReportNotFoundError(AppException):
    """Raised when no explainability report exists for a customer."""

    def __init__(self, customer_id: UUID) -> None:
        super().__init__(f"Explainability report not found for customer: {customer_id}")
        self.customer_id = customer_id
