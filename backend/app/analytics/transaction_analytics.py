"""
Transaction Analytics Engine — deterministic transaction pattern analysis.

Analyses transaction history to produce explainable intelligence KPIs.
Does NOT compute lifestyle scores, segmentation, or risk — those are later modules.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from statistics import mean, pstdev

from app.schemas.banking import TransactionSchema
from app.schemas.customer360 import CustomerAggregate
from app.schemas.transaction_analytics import TransactionAnalyticsProfile
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

LOOKBACK_DAYS = 365
MONEY = Decimal("0.01")
SCORE = Decimal("0.01")
RATIO = Decimal("0.01")

DIGITAL_CHANNELS = frozenset({"UPI", "Net Banking", "Mobile Banking", "Debit Card", "NEFT", "IMPS"})
NIGHT_START_HOUR = 22
NIGHT_END_HOUR = 6


class TransactionAnalytics:
    """
    Enterprise transaction analytics engine.

    Each KPI has a dedicated method with an explicit, auditable business rule.
    """

    def calculate(self, aggregate: CustomerAggregate) -> TransactionAnalyticsProfile:
        """Run all transaction analytics KPIs for one customer."""
        txns = self._window_transactions(aggregate)
        reference = self._reference_date(aggregate)

        profile = TransactionAnalyticsProfile(
            average_transaction_amount=self.average_transaction_amount(txns),
            monthly_transaction_count=self.monthly_transaction_count(txns, reference),
            debit_transaction_count=self.debit_transaction_count(txns),
            credit_transaction_count=self.credit_transaction_count(txns),
            debit_credit_ratio=self.debit_credit_ratio(txns),
            cash_withdrawal_frequency=self.cash_withdrawal_frequency(txns, reference),
            cash_deposit_frequency=self.cash_deposit_frequency(txns, reference),
            upi_transaction_count=self.upi_transaction_count(txns),
            card_transaction_count=self.card_transaction_count(txns),
            net_banking_transaction_count=self.net_banking_transaction_count(txns),
            mobile_banking_transaction_count=self.mobile_banking_transaction_count(txns),
            digital_payment_ratio=self.digital_payment_ratio(txns),
            merchant_diversity=self.merchant_diversity(txns),
            category_diversity=self.category_diversity(txns),
            most_frequent_merchant=self.most_frequent_merchant(txns),
            most_frequent_category=self.most_frequent_category(txns),
            highest_transaction_amount=self.highest_transaction_amount(txns),
            lowest_transaction_amount=self.lowest_transaction_amount(txns),
            largest_credit_transaction=self.largest_credit_transaction(txns),
            largest_debit_transaction=self.largest_debit_transaction(txns),
            transaction_consistency_score=self.transaction_consistency_score(txns, reference),
            income_regularity_score=self.income_regularity_score(txns, reference),
            expense_stability_score=self.expense_stability_score(txns, reference),
            weekend_transaction_percentage=self.weekend_transaction_percentage(txns),
            night_transaction_percentage=self.night_transaction_percentage(txns),
        )

        logger.info(
            "Transaction analytics computed for customer_id=%s: txns=%d digital_ratio=%s consistency=%s",
            aggregate.customer.customer_id,
            len(txns),
            profile.digital_payment_ratio,
            profile.transaction_consistency_score,
        )
        return profile

    @staticmethod
    def _reference_date(aggregate: CustomerAggregate) -> datetime:
        if aggregate.transactions:
            return max(t.date for t in aggregate.transactions)
        return datetime.utcnow()

    def _window_transactions(self, aggregate: CustomerAggregate) -> list[TransactionSchema]:
        reference = self._reference_date(aggregate)
        start = reference - timedelta(days=LOOKBACK_DAYS)
        return [t for t in aggregate.transactions if start <= t.date <= reference]

    @staticmethod
    def _month_key(dt: datetime) -> str:
        return f"{dt.year}-{dt.month:02d}"

    @staticmethod
    def _months_in_window(reference: datetime) -> int:
        return 12

    def average_transaction_amount(self, txns: list[TransactionSchema]) -> Decimal:
        """Rule: Arithmetic mean of transaction amounts in the 12-month window."""
        if not txns:
            return Decimal("0.00")
        total = sum(t.amount for t in txns)
        return (total / Decimal(len(txns))).quantize(MONEY, ROUND_HALF_UP)

    def monthly_transaction_count(self, txns: list[TransactionSchema], reference: datetime) -> Decimal:
        """Rule: Total transactions divided by number of active months (max 12)."""
        if not txns:
            return Decimal("0.00")
        months = {self._month_key(t.date) for t in txns}
        divisor = Decimal(max(len(months), 1))
        return (Decimal(len(txns)) / divisor).quantize(RATIO, ROUND_HALF_UP)

    def debit_transaction_count(self, txns: list[TransactionSchema]) -> int:
        """Rule: Count transactions where transaction_type = DEBIT."""
        return sum(1 for t in txns if t.transaction_type == "DEBIT")

    def credit_transaction_count(self, txns: list[TransactionSchema]) -> int:
        """Rule: Count transactions where transaction_type = CREDIT."""
        return sum(1 for t in txns if t.transaction_type == "CREDIT")

    def debit_credit_ratio(self, txns: list[TransactionSchema]) -> Decimal:
        """Rule: debit_count / credit_count. Returns debit_count if no credits."""
        debits = self.debit_transaction_count(txns)
        credits = self.credit_transaction_count(txns)
        if credits == 0:
            return Decimal(str(debits)).quantize(RATIO, ROUND_HALF_UP)
        return (Decimal(debits) / Decimal(credits)).quantize(RATIO, ROUND_HALF_UP)

    def cash_withdrawal_frequency(self, txns: list[TransactionSchema], reference: datetime) -> Decimal:
        """Rule: ATM withdrawals per month — category='ATM Withdrawal' OR channel='ATM' + DEBIT."""
        withdrawals = [
            t for t in txns
            if t.transaction_type == "DEBIT"
            and (t.category == "ATM Withdrawal" or t.channel == "ATM")
        ]
        months = self._months_in_window(reference)
        return (Decimal(len(withdrawals)) / Decimal(months)).quantize(RATIO, ROUND_HALF_UP)

    def cash_deposit_frequency(self, txns: list[TransactionSchema], reference: datetime) -> Decimal:
        """Rule: Cash deposits per month — channel='ATM' + CREDIT, excluding salary."""
        deposits = [
            t for t in txns
            if t.transaction_type == "CREDIT"
            and t.channel == "ATM"
            and t.category != "Salary"
        ]
        months = self._months_in_window(reference)
        return (Decimal(len(deposits)) / Decimal(months)).quantize(RATIO, ROUND_HALF_UP)

    def upi_transaction_count(self, txns: list[TransactionSchema]) -> int:
        """Rule: Count transactions where channel = UPI."""
        return sum(1 for t in txns if t.channel == "UPI")

    def card_transaction_count(self, txns: list[TransactionSchema]) -> int:
        """Rule: Count transactions where channel = Debit Card."""
        return sum(1 for t in txns if t.channel == "Debit Card")

    def net_banking_transaction_count(self, txns: list[TransactionSchema]) -> int:
        """Rule: Count transactions where channel = Net Banking."""
        return sum(1 for t in txns if t.channel == "Net Banking")

    def mobile_banking_transaction_count(self, txns: list[TransactionSchema]) -> int:
        """Rule: Count transactions where channel = Mobile Banking."""
        return sum(1 for t in txns if t.channel == "Mobile Banking")

    def digital_payment_ratio(self, txns: list[TransactionSchema]) -> Decimal:
        """Rule: (digital channel txns / total txns) × 100."""
        if not txns:
            return Decimal("0.00")
        digital = sum(1 for t in txns if t.channel in DIGITAL_CHANNELS)
        return (Decimal(digital) / Decimal(len(txns)) * Decimal("100")).quantize(RATIO, ROUND_HALF_UP)

    def merchant_diversity(self, txns: list[TransactionSchema]) -> int:
        """Rule: Count of distinct non-null merchant names."""
        merchants = {t.merchant for t in txns if t.merchant}
        return len(merchants)

    def category_diversity(self, txns: list[TransactionSchema]) -> int:
        """Rule: Count of distinct transaction categories."""
        return len({t.category for t in txns})

    def most_frequent_merchant(self, txns: list[TransactionSchema]) -> str | None:
        """Rule: Merchant appearing most frequently in transaction history."""
        merchants = [t.merchant for t in txns if t.merchant]
        if not merchants:
            return None
        return Counter(merchants).most_common(1)[0][0]

    def most_frequent_category(self, txns: list[TransactionSchema]) -> str | None:
        """Rule: Category appearing most frequently in transaction history."""
        if not txns:
            return None
        return Counter(t.category for t in txns).most_common(1)[0][0]

    def highest_transaction_amount(self, txns: list[TransactionSchema]) -> Decimal:
        """Rule: Maximum transaction amount in window."""
        if not txns:
            return Decimal("0.00")
        return max(t.amount for t in txns).quantize(MONEY, ROUND_HALF_UP)

    def lowest_transaction_amount(self, txns: list[TransactionSchema]) -> Decimal:
        """Rule: Minimum transaction amount in window."""
        if not txns:
            return Decimal("0.00")
        return min(t.amount for t in txns).quantize(MONEY, ROUND_HALF_UP)

    def largest_credit_transaction(self, txns: list[TransactionSchema]) -> Decimal:
        """Rule: Maximum amount among CREDIT transactions."""
        credits = [t.amount for t in txns if t.transaction_type == "CREDIT"]
        if not credits:
            return Decimal("0.00")
        return max(credits).quantize(MONEY, ROUND_HALF_UP)

    def largest_debit_transaction(self, txns: list[TransactionSchema]) -> Decimal:
        """Rule: Maximum amount among DEBIT transactions."""
        debits = [t.amount for t in txns if t.transaction_type == "DEBIT"]
        if not debits:
            return Decimal("0.00")
        return max(debits).quantize(MONEY, ROUND_HALF_UP)

    def transaction_consistency_score(self, txns: list[TransactionSchema], reference: datetime) -> Decimal:
        """
        Rule: 100 − (CV of monthly transaction counts × 100), floored at 0.
        Higher score = more stable monthly transaction volume.
        """
        monthly_counts = self._monthly_counts(txns)
        return self._stability_score([Decimal(c) for c in monthly_counts.values()])

    def income_regularity_score(self, txns: list[TransactionSchema], reference: datetime) -> Decimal:
        """
        Rule: Combines salary presence rate and salary amount stability.
          50% — months_with_salary / 12 × 100
          50% — stability score of monthly salary credit amounts
        """
        salary_by_month: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for t in txns:
            if t.category == "Salary" and t.transaction_type == "CREDIT":
                salary_by_month[self._month_key(t.date)] += t.amount

        presence_score = Decimal(len(salary_by_month)) / Decimal("12") * Decimal("100")
        amount_stability = self._stability_score(list(salary_by_month.values())) if salary_by_month else Decimal("0")

        composite = presence_score * Decimal("0.50") + amount_stability * Decimal("0.50")
        return composite.quantize(SCORE, ROUND_HALF_UP)

    def expense_stability_score(self, txns: list[TransactionSchema], reference: datetime) -> Decimal:
        """
        Rule: Stability of monthly debit totals — 100 − (CV × 100).
        Higher score = more predictable monthly spending.
        """
        monthly_debits: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for t in txns:
            if t.transaction_type == "DEBIT":
                monthly_debits[self._month_key(t.date)] += t.amount
        return self._stability_score(list(monthly_debits.values()))

    def weekend_transaction_percentage(self, txns: list[TransactionSchema]) -> Decimal:
        """Rule: (Saturday + Sunday transactions / total) × 100."""
        if not txns:
            return Decimal("0.00")
        weekend = sum(1 for t in txns if t.date.weekday() >= 5)
        return (Decimal(weekend) / Decimal(len(txns)) * Decimal("100")).quantize(RATIO, ROUND_HALF_UP)

    def night_transaction_percentage(self, txns: list[TransactionSchema]) -> Decimal:
        """Rule: Transactions between 22:00–06:00 as percentage of total."""
        if not txns:
            return Decimal("0.00")
        night = sum(1 for t in txns if self._is_night(t.date))
        return (Decimal(night) / Decimal(len(txns)) * Decimal("100")).quantize(RATIO, ROUND_HALF_UP)

    @staticmethod
    def _is_night(dt: datetime) -> bool:
        hour = dt.hour
        return hour >= NIGHT_START_HOUR or hour < NIGHT_END_HOUR

    @staticmethod
    def _monthly_counts(txns: list[TransactionSchema]) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for t in txns:
            counts[f"{t.date.year}-{t.date.month:02d}"] += 1
        return dict(counts)

    @staticmethod
    def _stability_score(values: list[Decimal]) -> Decimal:
        """CV-based stability: 100 − (population_std_dev / mean × 100), min 0."""
        if len(values) < 2:
            return Decimal("100.00")
        float_vals = [float(v) for v in values]
        avg = mean(float_vals)
        if avg == 0:
            return Decimal("100.00")
        cv = pstdev(float_vals) / avg
        score = max(0.0, 100.0 - cv * 100.0)
        return Decimal(str(round(score, 2))).quantize(SCORE, ROUND_HALF_UP)
