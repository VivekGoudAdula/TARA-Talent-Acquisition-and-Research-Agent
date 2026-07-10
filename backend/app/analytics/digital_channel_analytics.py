"""
Digital & Channel Analytics Engine — deterministic channel and engagement analysis.

Measures how customers interact with the bank digitally and physically.
Does NOT recommend products or use ML/LLM.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from statistics import pstdev

from app.schemas.behaviour_analytics import BehaviourProfile
from app.schemas.customer360 import CustomerAggregate
from app.schemas.digital_channel_analytics import (
    CommunicationReadinessResult,
    ContactPolicy,
    DigitalBankingResult,
    DigitalChannelProfile,
    DigitalEngagementResult,
)
from app.schemas.digital_channel_input import DigitalChannelAnalyticsInput
from app.schemas.relationship_analytics import RelationshipProfile
from app.schemas.transaction_analytics import TransactionAnalyticsProfile
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

SCORE = Decimal("0.01")
LOOKBACK_DAYS = 365

DIGITAL_CHANNELS = frozenset({"UPI", "Net Banking", "Mobile Banking", "Debit Card", "NEFT", "IMPS"})
CASH_CHANNELS = frozenset({"ATM"})
CREDIT_CHANNEL = "Debit Card"  # proxy when credit card txns not separate

MATURITY_LEVELS = (
    (Decimal("75"), "Digital First"),
    (Decimal("50"), "Digital"),
    (Decimal("25"), "Emerging Digital"),
    (Decimal("0"), "Traditional"),
)

TIME_BUCKETS = (
    (range(6, 12), "Morning"),
    (range(12, 17), "Afternoon"),
    (range(17, 22), "Evening"),
    (range(22, 24), "Night"),
    (range(0, 6), "Night"),
)


def _window_transactions(aggregate: CustomerAggregate) -> list:
    if not aggregate.transactions:
        return []
    reference = max(t.date for t in aggregate.transactions)
    start = reference - timedelta(days=LOOKBACK_DAYS)
    return [t for t in aggregate.transactions if start <= t.date <= reference]


def _channel_share(txns: list, channel: str) -> Decimal:
    if not txns:
        return Decimal("0.00")
    count = sum(1 for t in txns if t.channel == channel)
    return (Decimal(count) / Decimal(len(txns)) * Decimal("100")).quantize(SCORE, ROUND_HALF_UP)


def _channel_share_multi(txns: list, channels: set[str]) -> Decimal:
    if not txns:
        return Decimal("0.00")
    count = sum(1 for t in txns if t.channel in channels)
    return (Decimal(count) / Decimal(len(txns)) * Decimal("100")).quantize(SCORE, ROUND_HALF_UP)


def _maturity_level(adoption_score: Decimal) -> str:
    for threshold, label in MATURITY_LEVELS:
        if adoption_score >= threshold:
            return label
    return "Traditional"


class DigitalBankingAnalyzer:
    """Analyzes usage of digital vs physical banking channels."""

    def analyze(
        self,
        aggregate: CustomerAggregate,
        transaction: TransactionAnalyticsProfile,
    ) -> DigitalBankingResult:
        txns = _window_transactions(aggregate)
        digital_ratio = transaction.digital_payment_ratio
        cash_ratio = (
            _channel_share_multi(txns, CASH_CHANNELS)
            + _channel_share(txns, "ATM")
        ) / Decimal("2") if txns else Decimal("0")

        upi = _channel_share(txns, "UPI")
        net = _channel_share(txns, "Net Banking")
        mobile = _channel_share(txns, "Mobile Banking")
        debit = _channel_share(txns, "Debit Card")
        atm = _channel_share(txns, "ATM")
        branch = max(Decimal("0"), Decimal("100") - digital_ratio - atm).quantize(SCORE, ROUND_HALF_UP)

        adoption = (
            digital_ratio * Decimal("0.50")
            + upi * Decimal("0.20")
            + mobile * Decimal("0.20")
            + net * Decimal("0.10")
        ).quantize(SCORE, ROUND_HALF_UP)

        return DigitalBankingResult(
            upi_usage_score=upi,
            net_banking_usage_score=net,
            mobile_banking_usage_score=mobile,
            debit_card_usage_score=debit,
            credit_card_usage_score=debit * Decimal("0.6"),
            atm_usage_score=atm,
            branch_banking_score=branch,
            digital_payment_ratio=digital_ratio,
            cash_usage_ratio=cash_ratio.quantize(SCORE, ROUND_HALF_UP),
            digital_adoption_score=adoption,
            digital_maturity=_maturity_level(adoption),
        )


class ContactTimeAnalyzer:
    """Infers preferred contact time and day from transaction timestamps."""

    def analyze(self, aggregate: CustomerAggregate) -> tuple[str, str, str | None]:
        txns = _window_transactions(aggregate)
        if not txns:
            return "Afternoon", "Weekday", None

        time_counts: Counter[str] = Counter()
        for t in txns:
            hour = t.date.hour
            for hours, label in TIME_BUCKETS:
                if hour in hours:
                    time_counts[label] += 1
                    break

        preferred_time = time_counts.most_common(1)[0][0] if time_counts else "Afternoon"

        weekday_count = sum(1 for t in txns if t.date.weekday() < 5)
        weekend_count = len(txns) - weekday_count
        preferred_day = "Weekend" if weekend_count > weekday_count else "Weekday"

        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        day_counter = Counter(day_names[t.date.weekday()] for t in txns)
        top_day, top_count = day_counter.most_common(1)[0]
        specific_day = top_day if top_count >= max(3, len(txns) // 8) else None

        return preferred_time, preferred_day, specific_day


class DigitalEngagementAnalyzer:
    """Measures digital engagement intensity and consistency."""

    def analyze(
        self,
        aggregate: CustomerAggregate,
        transaction: TransactionAnalyticsProfile,
        digital_banking: DigitalBankingResult,
    ) -> DigitalEngagementResult:
        txns = _window_transactions(aggregate)
        months: dict[str, int] = {}
        for t in txns:
            if t.channel in DIGITAL_CHANNELS:
                key = f"{t.date.year}-{t.date.month:02d}"
                months[key] = months.get(key, 0) + 1

        consistency = Decimal("100")
        if len(months) >= 2:
            values = list(months.values())
            avg = sum(values) / len(values)
            if avg > 0:
                cv = pstdev(values) / avg
                consistency = Decimal(str(max(0.0, round(100.0 - cv * 100.0, 2))))

        online_freq = (
            _channel_share(txns, "Net Banking") + _channel_share(txns, "Mobile Banking")
        ) / Decimal("2")
        upi_freq = min(Decimal("100"), transaction.upi_transaction_count / Decimal("12") * Decimal("5"))
        card_freq = min(Decimal("100"), transaction.card_transaction_count / Decimal("12") * Decimal("5"))

        engagement = (
            digital_banking.digital_adoption_score * Decimal("0.35")
            + online_freq * Decimal("0.20")
            + upi_freq * Decimal("0.20")
            + consistency * Decimal("0.15")
            + transaction.transaction_consistency_score * Decimal("0.10")
        ).quantize(SCORE, ROUND_HALF_UP)

        return DigitalEngagementResult(
            digital_engagement_score=engagement,
            online_banking_frequency=online_freq,
            upi_frequency=upi_freq,
            card_usage_frequency=card_freq,
            mobile_app_dependency=digital_banking.mobile_banking_usage_score,
            digital_transaction_consistency=consistency.quantize(SCORE, ROUND_HALF_UP),
        )


class CommunicationReadinessAnalyzer:
    """Scores readiness for each communication channel (0–100)."""

    def analyze(
        self,
        aggregate: CustomerAggregate,
        digital_banking: DigitalBankingResult,
        behaviour: BehaviourProfile,
    ) -> CommunicationReadinessResult:
        consent = aggregate.consent
        digital_factor = digital_banking.digital_adoption_score / Decimal("100")

        email_base = Decimal("100") if consent and consent.marketing_email else Decimal("20")
        sms_base = Decimal("100") if consent and consent.marketing_sms else Decimal("20")
        voice_base = Decimal("100") if consent and consent.marketing_voice else Decimal("20")
        whatsapp_base = Decimal("100") if consent and consent.marketing_whatsapp else Decimal("20")

        email = (email_base * (Decimal("0.6") + digital_factor * Decimal("0.4"))).quantize(SCORE, ROUND_HALF_UP)
        sms = (sms_base * (Decimal("0.7") + digital_factor * Decimal("0.3"))).quantize(SCORE, ROUND_HALF_UP)
        voice = (voice_base * (Decimal("0.8") - digital_factor * Decimal("0.2"))).quantize(SCORE, ROUND_HALF_UP)
        whatsapp = (
            whatsapp_base * (Decimal("0.5") + digital_factor * Decimal("0.5"))
        ).quantize(SCORE, ROUND_HALF_UP)
        app_notif = (
            digital_banking.mobile_banking_usage_score * Decimal("0.7")
            + behaviour.shopping_score * Decimal("0.3")
        ).quantize(SCORE, ROUND_HALF_UP)

        return CommunicationReadinessResult(
            voice_readiness_score=min(Decimal("100"), max(Decimal("0"), voice)),
            sms_readiness_score=min(Decimal("100"), max(Decimal("0"), sms)),
            whatsapp_readiness_score=min(Decimal("100"), max(Decimal("0"), whatsapp)),
            email_readiness_score=min(Decimal("100"), max(Decimal("0"), email)),
            app_notification_readiness_score=min(Decimal("100"), max(Decimal("0"), app_notif)),
        )


class ChannelPreferenceAnalyzer:
    """Infers preferred and secondary communication channels."""

    def analyze(
        self,
        readiness: CommunicationReadinessResult,
        digital_banking: DigitalBankingResult,
        relationship: RelationshipProfile,
        aggregate: CustomerAggregate,
    ) -> tuple[str, str]:
        candidates: list[tuple[str, Decimal]] = [
            ("Voice", readiness.voice_readiness_score),
            ("WhatsApp", readiness.whatsapp_readiness_score),
            ("SMS", readiness.sms_readiness_score),
            ("Email", readiness.email_readiness_score),
            ("Mobile App", readiness.app_notification_readiness_score),
        ]

        if digital_banking.branch_banking_score > Decimal("40"):
            candidates.append(("Branch", digital_banking.branch_banking_score))
        if relationship.relationship_tier in ("Gold", "Platinum", "Diamond"):
            candidates.append(("Relationship Manager", Decimal("85")))

        ranked = sorted(candidates, key=lambda x: x[1], reverse=True)
        primary = ranked[0][0]
        secondary = ranked[1][0] if len(ranked) > 1 else "SMS"

        if digital_banking.digital_maturity == "Digital First" and readiness.app_notification_readiness_score >= Decimal("70"):
            primary = "Mobile App"
            secondary = "WhatsApp" if readiness.whatsapp_readiness_score >= readiness.sms_readiness_score else "SMS"

        return primary, secondary


class ContactPolicyGenerator:
    """Generates recommended communication policy (not product recommendations)."""

    @staticmethod
    def generate(
        preferred_channel: str,
        secondary_channel: str,
        preferred_time: str,
        preferred_day: str,
        engagement_score: Decimal,
    ) -> ContactPolicy:
        if engagement_score >= Decimal("80"):
            frequency = "3 per week"
        elif engagement_score >= Decimal("50"):
            frequency = "2 per week"
        else:
            frequency = "1 per week"

        return ContactPolicy(
            preferred_channel=preferred_channel,
            secondary_channel=secondary_channel,
            preferred_time=preferred_time,
            preferred_day=preferred_day,
            maximum_contact_frequency=frequency,
        )


class DigitalChannelAnalytics:
    """Orchestrates all digital and channel analytics modules."""

    def __init__(self) -> None:
        self._digital_banking = DigitalBankingAnalyzer()
        self._contact_time = ContactTimeAnalyzer()
        self._engagement = DigitalEngagementAnalyzer()
        self._readiness = CommunicationReadinessAnalyzer()
        self._channel_pref = ChannelPreferenceAnalyzer()
        self._policy = ContactPolicyGenerator()

    def calculate(self, data: DigitalChannelAnalyticsInput) -> DigitalChannelProfile:
        customer_id = data.aggregate.customer.customer_id

        digital_banking = self._digital_banking.analyze(data.aggregate, data.transaction)
        preferred_time, preferred_day, _specific = self._contact_time.analyze(data.aggregate)
        engagement = self._engagement.analyze(data.aggregate, data.transaction, digital_banking)
        readiness = self._readiness.analyze(data.aggregate, digital_banking, data.behaviour)
        primary, secondary = self._channel_pref.analyze(
            readiness, digital_banking, data.relationship, data.aggregate
        )
        policy = self._policy.generate(
            primary, secondary, preferred_time, preferred_day, engagement.digital_engagement_score
        )

        profile = DigitalChannelProfile(
            customer_id=customer_id,
            digital_adoption_score=digital_banking.digital_adoption_score,
            digital_maturity=digital_banking.digital_maturity,
            preferred_channel=primary,
            secondary_channel=secondary,
            preferred_contact_time=preferred_time,
            preferred_contact_day=preferred_day,
            voice_readiness_score=readiness.voice_readiness_score,
            sms_readiness_score=readiness.sms_readiness_score,
            whatsapp_readiness_score=readiness.whatsapp_readiness_score,
            email_readiness_score=readiness.email_readiness_score,
            engagement_score=engagement.digital_engagement_score,
            digital_banking=digital_banking,
            digital_engagement=engagement,
            communication_readiness=readiness,
            contact_policy=policy,
        )

        logger.info(
            "Digital channel analytics for customer_id=%s maturity=%s channel=%s engagement=%s",
            customer_id,
            profile.digital_maturity,
            profile.preferred_channel,
            profile.engagement_score,
        )
        return profile
