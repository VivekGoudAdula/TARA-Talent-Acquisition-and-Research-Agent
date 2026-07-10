"""KYC Readiness Engine — onboarding readiness assessment for external leads."""

from __future__ import annotations

from app.schemas.external_intelligence_validation import ExternalLeadIntelligenceInput
from app.schemas.external_lead_intelligence import KycReadinessResult


class KycReadinessEngine:
    """Determines whether a lead has sufficient data for KYC onboarding."""

    KYC_DOCUMENT_ITEMS = ("PAN", "Address Proof", "Identity Verification")

    def calculate(self, data: ExternalLeadIntelligenceInput) -> KycReadinessResult:
        missing: list[str] = []
        crm_missing: list[str] = []
        reasons: list[str] = []
        checks_passed = 0
        total_checks = 6

        if self._has_phone(data):
            checks_passed += 1
            reasons.append("Phone available")
        else:
            crm_missing.append("Phone Number")

        if self._has_email(data):
            checks_passed += 1
            reasons.append("Email available")
        else:
            crm_missing.append("Email")

        if data.consent:
            checks_passed += 1
            reasons.append("Consent verified")
        else:
            crm_missing.append("Consent")

        if self._has_identity(data):
            checks_passed += 1
            reasons.append("Identity information available")
        else:
            crm_missing.append("Identity Information")

        if self._has_occupation(data):
            checks_passed += 1
            reasons.append("Occupation available")
        else:
            crm_missing.append("Occupation")

        if self._has_employer(data):
            checks_passed += 1
            reasons.append("Employer available")
        else:
            crm_missing.append("Employer")

        if checks_passed == total_checks and data.consent:
            readiness = "Ready"
            missing = []
        elif checks_passed >= 4:
            readiness = "Partially Ready"
            missing = crm_missing + list(self.KYC_DOCUMENT_ITEMS)
        else:
            readiness = "Not Ready"
            missing = crm_missing + list(self.KYC_DOCUMENT_ITEMS)

        if readiness == "Ready":
            reasons.append("Lead meets CRM KYC readiness criteria")
        elif readiness == "Partially Ready":
            reasons.append("Lead partially ready — document collection required")

        return KycReadinessResult(
            kyc_readiness=readiness,
            kyc_missing_items=missing,
            reason_codes=reasons,
        )

    @staticmethod
    def _has_phone(data: ExternalLeadIntelligenceInput) -> bool:
        return bool(data.phone_number and len(data.phone_number) >= 10)

    @staticmethod
    def _has_email(data: ExternalLeadIntelligenceInput) -> bool:
        return bool(data.email and "@" in data.email)

    @staticmethod
    def _has_identity(data: ExternalLeadIntelligenceInput) -> bool:
        return (
            bool(data.full_name and len(data.full_name.strip()) > 2)
            and data.age >= 18
            and bool(data.gender and data.gender != "Unknown")
        )

    @staticmethod
    def _has_occupation(data: ExternalLeadIntelligenceInput) -> bool:
        return bool(data.occupation and data.occupation.lower() not in ("unknown", ""))

    @staticmethod
    def _has_employer(data: ExternalLeadIntelligenceInput) -> bool:
        return bool(data.employer and data.employer.lower() not in ("unknown", ""))
