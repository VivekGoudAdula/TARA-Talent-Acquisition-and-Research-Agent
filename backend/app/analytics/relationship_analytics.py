"""
Banking Relationship Analytics Engine — measures relationship depth and health.

Deterministic, explainable rules only. Does NOT recommend products or use ML/LLM.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

from app.schemas.behaviour_analytics import BehaviourProfile
from app.schemas.customer360 import CustomerAggregate
from app.schemas.financial_profile import FinancialProfile
from app.schemas.relationship_analytics import (
    AccountAnalyticsResult,
    ProductPortfolioResult,
    RelationshipProfile,
)
from app.schemas.relationship_input import RelationshipAnalyticsInput
from app.schemas.transaction_analytics import TransactionAnalyticsProfile
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

SCORE = Decimal("0.01")
MONEY = Decimal("0.01")
YEARS = Decimal("0.01")

# Full SBI retail product catalog used for penetration and gap analysis
SBI_PRODUCT_CATALOG: tuple[str, ...] = (
    "Savings Account",
    "Current Account",
    "Salary Account",
    "Credit Card",
    "Personal Loan",
    "Home Loan",
    "Car Loan",
    "Gold Loan",
    "Education Loan",
    "Fixed Deposit",
    "Recurring Deposit",
    "Life Insurance",
    "Health Insurance",
    "Mutual Fund",
)

LOAN_PRODUCTS = frozenset(
    {"Personal Loan", "Home Loan", "Car Loan", "Gold Loan", "Education Loan"}
)
INSURANCE_PRODUCTS = frozenset({"Life Insurance", "Health Insurance"})


class AccountAnalytics:
    """Analyzes account holdings and account-level relationship signals."""

    def analyze(self, aggregate: CustomerAggregate, reference: date | None = None) -> AccountAnalyticsResult:
        today = reference or date.today()
        accounts = aggregate.accounts

        savings = sum(1 for a in accounts if a.account_type == "Savings")
        salary = sum(1 for a in accounts if a.account_type == "Salary")
        current = sum(1 for a in accounts if a.account_type == "Current")
        dormant = sum(1 for a in accounts if a.status == "Dormant")
        closed = sum(1 for a in accounts if a.status == "Inactive")

        ages = [_years_between(a.opened_date, today) for a in accounts]
        avg_age = sum(ages, Decimal("0")) / Decimal(max(len(ages), 1)) if ages else Decimal("0")

        return AccountAnalyticsResult(
            number_of_accounts=len(accounts),
            savings_accounts=savings,
            salary_accounts=salary,
            current_accounts=current,
            dormant_accounts=dormant,
            closed_accounts=closed,
            average_account_age_years=avg_age.quantize(YEARS, ROUND_HALF_UP),
            oldest_account_years=max(ages, default=Decimal("0")).quantize(YEARS, ROUND_HALF_UP),
            newest_account_years=min(ages, default=Decimal("0")).quantize(YEARS, ROUND_HALF_UP),
        )


class ProductPortfolioAnalyzer:
    """Analyzes owned banking products and portfolio composition."""

    def analyze(self, aggregate: CustomerAggregate) -> ProductPortfolioResult:
        active = [p for p in aggregate.products if p.status == "Active"]
        names = {
            p.product.product_name
            for p in active
            if p.product is not None
        }

        return ProductPortfolioResult(
            number_of_active_products=len(active),
            savings_account_count=_count(names, "Savings Account"),
            current_account_count=_count(names, "Current Account"),
            credit_card_count=_count(names, "Credit Card"),
            loan_count=sum(1 for n in names if n in LOAN_PRODUCTS),
            insurance_count=sum(1 for n in names if n in INSURANCE_PRODUCTS),
            mutual_fund_count=_count(names, "Mutual Fund"),
            fixed_deposit_count=_count(names, "Fixed Deposit"),
            recurring_deposit_count=_count(names, "Recurring Deposit"),
            demat_account_count=_count(names, "Demat Account"),
        )

    @staticmethod
    def owned_product_names(aggregate: CustomerAggregate) -> set[str]:
        return {
            p.product.product_name
            for p in aggregate.products
            if p.status == "Active" and p.product is not None
        }


class ProductGapAnalyzer:
    """Identifies products not yet owned by the customer."""

    def analyze(self, aggregate: CustomerAggregate) -> list[str]:
        owned = ProductPortfolioAnalyzer.owned_product_names(aggregate)
        return [product for product in SBI_PRODUCT_CATALOG if product not in owned]

    @staticmethod
    def penetration_score(owned_count: int, catalog_size: int = len(SBI_PRODUCT_CATALOG)) -> Decimal:
        """Rule: (active products / catalog size) × 100."""
        if catalog_size == 0:
            return Decimal("0.00")
        return (Decimal(owned_count) / Decimal(catalog_size) * Decimal("100")).quantize(SCORE, ROUND_HALF_UP)


class RelationshipStrengthAnalyzer:
    """Computes relationship strength, loyalty, stability, and dependency scores."""

    def analyze(
        self,
        relationship_age: Decimal,
        penetration: Decimal,
        engagement: Decimal,
        diversity: Decimal,
        financial: FinancialProfile,
        transaction: TransactionAnalyticsProfile,
        aggregate: CustomerAggregate,
        account_analytics: AccountAnalyticsResult,
    ) -> dict[str, Decimal]:
        age_score = min(Decimal("100"), relationship_age / Decimal("10") * Decimal("100"))

        loyalty = (
            age_score * Decimal("0.35")
            + penetration * Decimal("0.25")
            + engagement * Decimal("0.20")
            + (Decimal("100") if aggregate.customer.is_existing_customer else Decimal("50")) * Decimal("0.20")
        ).quantize(SCORE, ROUND_HALF_UP)

        stability = (
            transaction.transaction_consistency_score * Decimal("0.35")
            + transaction.income_regularity_score * Decimal("0.35")
            + max(Decimal("0"), Decimal("100") - Decimal(account_analytics.dormant_accounts) * Decimal("20"))
            * Decimal("0.30")
        ).quantize(SCORE, ROUND_HALF_UP)

        bank_dependency = (
            transaction.digital_payment_ratio * Decimal("0.30")
            + min(Decimal("100"), transaction.monthly_transaction_count) * Decimal("0.30")
            + min(Decimal("100"), financial.average_balance / Decimal("500000") * Decimal("100")) * Decimal("0.20")
            + (Decimal("100") if account_analytics.salary_accounts > 0 else Decimal("40")) * Decimal("0.20")
        ).quantize(SCORE, ROUND_HALF_UP)

        primary_banking = (
            (Decimal("100") if account_analytics.salary_accounts > 0 else Decimal("30")) * Decimal("0.40")
            + min(Decimal("100"), transaction.monthly_transaction_count) * Decimal("0.30")
            + penetration * Decimal("0.30")
        ).quantize(SCORE, ROUND_HALF_UP)

        strength = (
            age_score * Decimal("0.20")
            + penetration * Decimal("0.25")
            + engagement * Decimal("0.25")
            + loyalty * Decimal("0.15")
            + stability * Decimal("0.15")
        ).quantize(SCORE, ROUND_HALF_UP)

        return {
            "loyalty_score": loyalty,
            "relationship_stability": stability,
            "bank_dependency_score": bank_dependency,
            "primary_banking_score": primary_banking,
            "relationship_strength_score": strength,
            "product_diversity_score": diversity,
        }


class EngagementAnalyzer:
    """Measures customer engagement with banking channels and accounts."""

    @staticmethod
    def monthly_active_days(transaction: TransactionAnalyticsProfile, aggregate: CustomerAggregate) -> Decimal:
        if not aggregate.transactions:
            return Decimal("0")
        days = {t.date.date() for t in aggregate.transactions}
        months = {f"{d.year}-{d.month:02d}" for d in days}
        return (Decimal(len(days)) / Decimal(max(len(months), 1))).quantize(SCORE, ROUND_HALF_UP)

    @staticmethod
    def account_usage_frequency(
        transaction: TransactionAnalyticsProfile,
        number_of_accounts: int,
    ) -> Decimal:
        if number_of_accounts == 0:
            return Decimal("0")
        return (transaction.monthly_transaction_count / Decimal(number_of_accounts)).quantize(SCORE, ROUND_HALF_UP)

    @staticmethod
    def engagement_score(
        transaction: TransactionAnalyticsProfile,
        behaviour: BehaviourProfile,
        monthly_active_days: Decimal,
        account_usage: Decimal,
    ) -> Decimal:
        """
        Rule: Weighted engagement composite:
          30% transaction volume, 25% digital adoption, 20% active days,
          15% account usage, 10% behaviour investment signal
        """
        txn_score = min(Decimal("100"), transaction.monthly_transaction_count)
        digital = transaction.digital_payment_ratio
        active_days_score = min(Decimal("100"), monthly_active_days * Decimal("3"))
        usage_score = min(Decimal("100"), account_usage * Decimal("5"))
        invest_signal = min(Decimal("100"), behaviour.investment_score)

        composite = (
            txn_score * Decimal("0.30")
            + digital * Decimal("0.25")
            + active_days_score * Decimal("0.20")
            + usage_score * Decimal("0.15")
            + invest_signal * Decimal("0.10")
        )
        return composite.quantize(SCORE, ROUND_HALF_UP)


class CustomerValueAnalyzer:
    """Estimates customer value and assigns relationship tier."""

    @staticmethod
    def estimated_value(
        financial: FinancialProfile,
        active_products: int,
        relationship_age: Decimal,
    ) -> Decimal:
        """
        Rule: ECV = (avg_balance × 2) + (annual_income × 0.10) + (products × ₹50,000)
              + (relationship_age × ₹25,000)
        """
        annual_income = financial.monthly_income * Decimal("12")
        value = (
            financial.average_balance * Decimal("2")
            + annual_income * Decimal("0.10")
            + Decimal(active_products) * Decimal("50000")
            + relationship_age * Decimal("25000")
        )
        return value.quantize(MONEY, ROUND_HALF_UP)

    @staticmethod
    def relationship_tier(
        strength_score: Decimal,
        estimated_value: Decimal,
        active_products: int,
    ) -> str:
        """
        Rule: Tier from composite index:
          40% strength score, 35% value band, 25% product count
        """
        value_band = min(Decimal("100"), estimated_value / Decimal("1000000") * Decimal("100"))
        product_band = min(Decimal("100"), Decimal(active_products) / Decimal("8") * Decimal("100"))
        index = (
            strength_score * Decimal("0.40")
            + value_band * Decimal("0.35")
            + product_band * Decimal("0.25")
        )
        if index >= Decimal("90"):
            return "Diamond"
        if index >= Decimal("75"):
            return "Platinum"
        if index >= Decimal("60"):
            return "Gold"
        if index >= Decimal("40"):
            return "Silver"
        return "Bronze"


def _years_between(start: date, end: date) -> Decimal:
    days = (end - start).days
    return Decimal(max(days, 0)) / Decimal("365.25")


def _count(names: set[str], product: str) -> int:
    return 1 if product in names else 0


class RelationshipAnalytics:
    """
    Orchestrates all relationship analytics modules.

    Measures relationship health — does NOT recommend products.
    """

    def __init__(self) -> None:
        self._accounts = AccountAnalytics()
        self._portfolio = ProductPortfolioAnalyzer()
        self._gap = ProductGapAnalyzer()
        self._strength = RelationshipStrengthAnalyzer()
        self._engagement = EngagementAnalyzer()
        self._value = CustomerValueAnalyzer()

    def calculate(self, data: RelationshipAnalyticsInput) -> RelationshipProfile:
        aggregate = data.aggregate
        customer_id = aggregate.customer.customer_id
        today = date.today()

        relationship_age = _years_between(
            aggregate.customer.created_at.date(),
            today,
        ).quantize(YEARS, ROUND_HALF_UP)

        account_result = self._accounts.analyze(aggregate, today)
        portfolio = self._portfolio.analyze(aggregate)
        missing = self._gap.analyze(aggregate)
        penetration = self._gap.penetration_score(portfolio.number_of_active_products)

        owned_types = ProductPortfolioAnalyzer.owned_product_names(aggregate)
        diversity = (
            Decimal(len(owned_types)) / Decimal(len(SBI_PRODUCT_CATALOG)) * Decimal("100")
        ).quantize(SCORE, ROUND_HALF_UP)

        active_days = self._engagement.monthly_active_days(data.transaction, aggregate)
        account_usage = self._engagement.account_usage_frequency(
            data.transaction, account_result.number_of_accounts
        )
        engagement = self._engagement.engagement_score(
            data.transaction, data.behaviour, active_days, account_usage
        )

        strength_metrics = self._strength.analyze(
            relationship_age,
            penetration,
            engagement,
            diversity,
            data.financial,
            data.transaction,
            aggregate,
            account_result,
        )

        ecv = self._value.estimated_value(
            data.financial, portfolio.number_of_active_products, relationship_age
        )
        tier = self._value.relationship_tier(
            strength_metrics["relationship_strength_score"],
            ecv,
            portfolio.number_of_active_products,
        )

        profile = RelationshipProfile(
            customer_id=customer_id,
            number_of_accounts=account_result.number_of_accounts,
            number_of_products=portfolio.number_of_active_products,
            relationship_age=relationship_age,
            relationship_strength_score=strength_metrics["relationship_strength_score"],
            loyalty_score=strength_metrics["loyalty_score"],
            product_penetration_score=penetration,
            product_diversity_score=strength_metrics["product_diversity_score"],
            bank_dependency_score=strength_metrics["bank_dependency_score"],
            relationship_tier=tier,
            estimated_customer_value=ecv,
            missing_products=missing,
            engagement_score=engagement,
            relationship_stability=strength_metrics["relationship_stability"],
            primary_banking_score=strength_metrics["primary_banking_score"],
            account_analytics=account_result,
            product_portfolio=portfolio,
        )

        logger.info(
            "Relationship analytics for customer_id=%s tier=%s strength=%s products=%d",
            customer_id,
            tier,
            profile.relationship_strength_score,
            portfolio.number_of_active_products,
        )
        return profile
