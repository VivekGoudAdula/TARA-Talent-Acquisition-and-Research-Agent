"""Build unified ML training records from intelligence layer sources."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.models.customer360_profile import Customer360Profile
from app.models.external_customer_profile import ExternalCustomerProfile
from app.models.external_lead import ExternalLead
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

PROFILE_INTERNAL = "Internal"
PROFILE_EXTERNAL = "External"

TARGET_VERY_HIGH = "Very High"
TARGET_HIGH = "High"
TARGET_MEDIUM = "Medium"
TARGET_LOW = "Low"


@dataclass(frozen=True)
class DatasetRow:
    """Single standardized training record before persistence."""

    record_id: UUID
    profile_type: str
    profile_id: UUID
    age: int | None
    income: Decimal | None
    credit_score: int | None
    financial_health_score: Decimal | None
    repayment_behaviour_score: Decimal | None
    digital_engagement_score: Decimal | None
    financial_capacity_score: Decimal | None
    lead_score: Decimal | None
    lead_quality_score: Decimal | None
    lead_authenticity_score: Decimal | None
    income_confidence_score: Decimal | None
    relationship_score: Decimal | None
    savings_ratio: Decimal | None
    emi_burden: Decimal | None
    cash_flow_score: Decimal | None
    digital_adoption_score: Decimal | None
    customer_value_score: Decimal | None
    occupation: str | None
    employment_type: str | None
    city: str | None
    target_repayment_capacity: str
    created_at: datetime


class DatasetGenerator:
    """
    Assembles training rows from customer_360_profile, external_customer_profile,
    feature_store, and lead_feature_store without inventing new analytics.
    """

    def build_internal_rows(
        self,
        profiles: list[Customer360Profile],
        feature_maps: dict[UUID, dict[str, Decimal | str]],
    ) -> list[DatasetRow]:
        rows: list[DatasetRow] = []
        for profile in profiles:
            features = feature_maps.get(profile.customer_id, {})
            row = self._from_internal_profile(profile, features)
            rows.append(row)
        logger.info("Generated %d internal training rows", len(rows))
        return rows

    def build_external_rows(
        self,
        profiles: list[ExternalCustomerProfile],
        leads: dict[UUID, ExternalLead],
        feature_maps: dict[UUID, dict[str, Decimal | str]],
    ) -> list[DatasetRow]:
        rows: list[DatasetRow] = []
        for profile in profiles:
            lead = leads.get(profile.lead_id)
            features = feature_maps.get(profile.lead_id, {})
            row = self._from_external_profile(profile, lead, features)
            rows.append(row)
        logger.info("Generated %d external training rows", len(rows))
        return rows

    def assign_targets(self, rows: list[DatasetRow]) -> list[DatasetRow]:
        return [
            replace(row, target_repayment_capacity=self._label_target(row))
            for row in rows
        ]

    @staticmethod
    def _attr(obj, name: str, default=None):
        """Safe read for DocumentEntity profiles — fields may exist only in MongoDB."""
        if obj is None:
            return default
        return getattr(obj, name, default)

    def _from_internal_profile(
        self,
        profile: Customer360Profile,
        features: dict[str, Decimal | str],
    ) -> DatasetRow:
        income = self._attr(profile, "monthly_income")
        annual_income = self._attr(profile, "annual_income")
        if income is None and annual_income is not None:
            income = annual_income / Decimal("12")

        savings_ratio = self._savings_ratio(
            self._attr(profile, "monthly_income"),
            self._attr(profile, "monthly_savings"),
        )
        customer_value = self._attr(profile, "engagement_score")
        estimated_value = self._attr(profile, "estimated_customer_value")
        if customer_value is None and estimated_value is not None:
            customer_value = self._normalize_customer_value(estimated_value)

        return DatasetRow(
            record_id=uuid4(),
            profile_type=PROFILE_INTERNAL,
            profile_id=profile.profile_id,
            age=self._attr(profile, "age"),
            income=income,
            credit_score=self._feature_int(features, "credit_score"),
            financial_health_score=self._coalesce(
                self._attr(profile, "financial_health_score"),
                self._feature_decimal(features, "financial_health_score"),
            ),
            repayment_behaviour_score=self._coalesce(
                self._attr(profile, "repayment_behaviour_score"),
                self._feature_decimal(features, "repayment_behaviour_score"),
            ),
            digital_engagement_score=self._coalesce(
                self._attr(profile, "digital_engagement_score"),
                self._feature_decimal(features, "digital_engagement_score"),
            ),
            financial_capacity_score=None,
            lead_score=None,
            lead_quality_score=None,
            lead_authenticity_score=None,
            income_confidence_score=None,
            relationship_score=self._attr(profile, "relationship_strength_score"),
            savings_ratio=savings_ratio,
            emi_burden=self._attr(profile, "emi_burden"),
            cash_flow_score=self._attr(profile, "cash_flow_score"),
            digital_adoption_score=self._attr(profile, "digital_adoption_score"),
            customer_value_score=customer_value,
            occupation=self._attr(profile, "occupation"),
            employment_type=None,
            city=self._attr(profile, "city"),
            target_repayment_capacity=TARGET_LOW,
            created_at=datetime.utcnow(),
        )

    def _from_external_profile(
        self,
        profile: ExternalCustomerProfile,
        lead: ExternalLead | None,
        features: dict[str, Decimal | str],
    ) -> DatasetRow:
        income = None
        credit_score = None
        age = None
        occupation = None
        employment_type = None
        city = None

        if lead is not None:
            if lead.estimated_income is not None:
                income = lead.estimated_income / Decimal("12")
            credit_score = lead.credit_score
            age = lead.age
            occupation = lead.occupation
            employment_type = lead.employer
            city = lead.city

        savings_ratio = self._feature_decimal(features, "savings_ratio")
        monthly_emi = self._attr(profile, "monthly_emi")
        emi_burden = monthly_emi
        if emi_burden is not None and income is not None and income > 0:
            emi_burden = (monthly_emi / income) * Decimal("100")

        return DatasetRow(
            record_id=uuid4(),
            profile_type=PROFILE_EXTERNAL,
            profile_id=profile.profile_id,
            age=age,
            income=income,
            credit_score=credit_score,
            financial_health_score=self._coalesce(
                self._attr(profile, "financial_health_score"),
                self._feature_decimal(features, "financial_health_score"),
            ),
            repayment_behaviour_score=self._coalesce(
                self._attr(profile, "repayment_behaviour_score"),
                self._feature_decimal(features, "repayment_behaviour_score"),
            ),
            digital_engagement_score=self._coalesce(
                self._attr(profile, "digital_engagement_score"),
                self._feature_decimal(features, "digital_engagement_score"),
            ),
            financial_capacity_score=self._coalesce(
                self._attr(profile, "financial_capacity_score"),
                self._feature_decimal(features, "financial_capacity_score"),
            ),
            lead_score=self._coalesce(
                self._attr(profile, "lead_score"),
                self._feature_decimal(features, "lead_score"),
            ),
            lead_quality_score=self._coalesce(
                self._attr(profile, "lead_quality_score"),
                self._feature_decimal(features, "lead_quality_score"),
            ),
            lead_authenticity_score=self._coalesce(
                self._attr(profile, "lead_authenticity_score"),
                self._feature_decimal(features, "lead_authenticity_score"),
            ),
            income_confidence_score=self._coalesce(
                self._attr(profile, "income_confidence_score"),
                self._feature_decimal(features, "income_confidence_score"),
            ),
            relationship_score=self._attr(profile, "relationship_potential"),
            savings_ratio=savings_ratio,
            emi_burden=emi_burden,
            cash_flow_score=self._attr(profile, "financial_stability"),
            digital_adoption_score=self._coalesce(
                self._attr(profile, "digital_adoption"),
                self._attr(profile, "digital_readiness_score"),
            ),
            customer_value_score=self._attr(profile, "cross_sell_potential"),
            occupation=occupation,
            employment_type=employment_type,
            city=city,
            target_repayment_capacity=TARGET_LOW,
            created_at=datetime.utcnow(),
        )

    def _label_target(self, row: DatasetRow) -> str:
        """
        Deterministic business-rule labels (temporary until real repayment outcomes).

        Very High: income > 100k, credit > 760, savings > 35%, EMI < 20%
        High:       income > 75k,  credit > 700, savings > 25%, EMI < 30%
        Medium:     income > 40k,  EMI < 45%, and at least one strength signal
        Low:        default
        """
        income = float(row.income) if row.income is not None else None
        credit = row.credit_score
        savings = float(row.savings_ratio) if row.savings_ratio is not None else None
        emi = float(row.emi_burden) if row.emi_burden is not None else None

        if self._tier_match(
            income=income,
            credit=credit,
            savings=savings,
            emi=emi,
            income_min=100_000,
            credit_min=760,
            savings_min=35.0,
            emi_max=20.0,
        ):
            return TARGET_VERY_HIGH

        if self._tier_match(
            income=income,
            credit=credit,
            savings=savings,
            emi=emi,
            income_min=75_000,
            credit_min=700,
            savings_min=25.0,
            emi_max=30.0,
        ):
            return TARGET_HIGH

        strength = (
            (credit is not None and credit > 650)
            or (savings is not None and savings > 15.0)
            or (
                row.financial_health_score is not None
                and float(row.financial_health_score) > 60.0
            )
            or (
                row.repayment_behaviour_score is not None
                and float(row.repayment_behaviour_score) > 60.0
            )
        )
        if (
            income is not None
            and income > 40_000
            and (emi is None or emi < 45.0)
            and strength
        ):
            return TARGET_MEDIUM

        return TARGET_LOW

    @staticmethod
    def _tier_match(
        *,
        income: float | None,
        credit: int | None,
        savings: float | None,
        emi: float | None,
        income_min: float,
        credit_min: int,
        savings_min: float,
        emi_max: float,
    ) -> bool:
        present = 0
        if income is not None:
            present += 1
            if income <= income_min:
                return False
        if credit is not None:
            present += 1
            if credit <= credit_min:
                return False
        if savings is not None:
            present += 1
            if savings <= savings_min:
                return False
        if emi is not None:
            present += 1
            if emi >= emi_max:
                return False
        return present >= 2

    @staticmethod
    def _savings_ratio(
        monthly_income: Decimal | None,
        monthly_savings: Decimal | None,
    ) -> Decimal | None:
        if monthly_income is None or monthly_income <= 0 or monthly_savings is None:
            return None
        return (monthly_savings / monthly_income) * Decimal("100")

    @staticmethod
    def _normalize_customer_value(value: Decimal) -> Decimal:
        scaled = (value / Decimal("50000")) * Decimal("10")
        return min(Decimal("100"), max(Decimal("0"), scaled))

    @staticmethod
    def _coalesce(primary: Decimal | None, fallback: Decimal | None) -> Decimal | None:
        return primary if primary is not None else fallback

    @staticmethod
    def _feature_decimal(features: dict[str, Decimal | str], name: str) -> Decimal | None:
        value = features.get(name)
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return Decimal(value)
            except Exception:
                return None
        return Decimal(str(value))

    @staticmethod
    def _feature_int(features: dict[str, Decimal | str], name: str) -> int | None:
        value = features.get(name)
        if value is None:
            return None
        try:
            return int(Decimal(str(value)))
        except Exception:
            return None
