"""
Financial Analytics Engine — deterministic KPI calculation.

Business rules are fully explainable and suitable for banking audit trails.
No ML, no LLM — only rule-based computation from CustomerAggregate data.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from statistics import mean, pstdev

from app.schemas.customer360 import CustomerAggregate
from app.schemas.financial_profile import FinancialProfile
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

MONEY_PRECISION = Decimal("0.01")
RATIO_PRECISION = Decimal("0.01")
SCORE_PRECISION = Decimal("0.01")

LOOKBACK_DAYS = 365

# Estimated monthly EMI burden as a fraction of monthly income per active loan product.
# Source: SBI retail lending benchmarks for explainable pre-approval analytics.
LOAN_EMI_INCOME_FRACTION: dict[str, Decimal] = {
    "Personal Loan": Decimal("0.02"),
    "Home Loan": Decimal("0.04"),
    "Car Loan": Decimal("0.025"),
    "Gold Loan": Decimal("0.01"),
    "Education Loan": Decimal("0.015"),
}

LOAN_PRODUCT_NAMES = frozenset(LOAN_EMI_INCOME_FRACTION.keys())


class FinancialAnalyticsEngine:
    """
    Computes financial KPIs from a CustomerAggregate.

    Input:  Customer, Accounts, Transactions, Products, Consent
    Output: FinancialProfile with all deterministic metrics
    """

    def calculate(self, aggregate: CustomerAggregate) -> FinancialProfile:
        """Run the full financial analytics pipeline for one customer."""
        reference_date = self._reference_date(aggregate)
        window_start = reference_date - timedelta(days=LOOKBACK_DAYS)

        salary_by_month = self._monthly_salary_totals(aggregate, window_start, reference_date)
        expense_by_month = self._monthly_expense_totals(aggregate, window_start, reference_date)

        monthly_income = self._average_monthly_income(salary_by_month, aggregate)
        monthly_expense = self._average_monthly_expense(expense_by_month)
        monthly_savings = (monthly_income - monthly_expense).quantize(MONEY_PRECISION, ROUND_HALF_UP)
        savings_ratio = self._savings_ratio(monthly_savings, monthly_income)
        average_balance = self._average_account_balance(aggregate)

        monthly_emi = self._estimate_monthly_emi(aggregate, monthly_income)
        debt_ratio = self._debt_ratio(monthly_emi, monthly_income)
        emi_burden = debt_ratio  # same percentage; named separately for downstream CRM use
        investment_ratio = self._investment_ratio(aggregate, monthly_income, window_start, reference_date)

        cash_flow_score = self._cash_flow_score(salary_by_month, expense_by_month, savings_ratio)
        liquidity_score = self._liquidity_score(average_balance, monthly_expense, monthly_income)

        profile = FinancialProfile(
            monthly_income=monthly_income,
            monthly_expense=monthly_expense,
            monthly_savings=monthly_savings,
            savings_ratio=savings_ratio,
            average_balance=average_balance,
            cash_flow_score=cash_flow_score,
            liquidity_score=liquidity_score,
            debt_ratio=debt_ratio,
            investment_ratio=investment_ratio,
            emi_burden=emi_burden,
        )

        logger.info(
            "Financial analytics computed for customer_id=%s: income=%s expense=%s savings_ratio=%s cash_flow=%s",
            aggregate.customer.customer_id,
            monthly_income,
            monthly_expense,
            savings_ratio,
            cash_flow_score,
        )
        return profile

    @staticmethod
    def _reference_date(aggregate: CustomerAggregate) -> datetime:
        """Use the latest transaction date as the analytics anchor, else today."""
        if aggregate.transactions:
            return max(txn.date for txn in aggregate.transactions)
        return datetime.utcnow()

    @staticmethod
    def _month_key(dt: datetime) -> str:
        return f"{dt.year}-{dt.month:02d}"

    def _monthly_salary_totals(
        self,
        aggregate: CustomerAggregate,
        window_start: datetime,
        reference_date: datetime,
    ) -> dict[str, Decimal]:
        """
        Rule: Salary credits = transactions where category='Salary' AND type='CREDIT'
        within the 12-month lookback window, summed per calendar month.
        """
        totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for txn in aggregate.transactions:
            if txn.date < window_start or txn.date > reference_date:
                continue
            if txn.category == "Salary" and txn.transaction_type == "CREDIT":
                totals[self._month_key(txn.date)] += txn.amount
        return dict(totals)

    def _monthly_expense_totals(
        self,
        aggregate: CustomerAggregate,
        window_start: datetime,
        reference_date: datetime,
    ) -> dict[str, Decimal]:
        """
        Rule: Monthly expenses = sum of all DEBIT transactions per calendar month.
        """
        totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for txn in aggregate.transactions:
            if txn.date < window_start or txn.date > reference_date:
                continue
            if txn.transaction_type == "DEBIT":
                totals[self._month_key(txn.date)] += txn.amount
        return dict(totals)

    def _average_monthly_income(
        self,
        salary_by_month: dict[str, Decimal],
        aggregate: CustomerAggregate,
    ) -> Decimal:
        """
        Rule: Average monthly salary over months with salary credits in last 12 months.
        Fallback: annual_income / 12 from customer master if no salary credits detected.
        """
        if salary_by_month:
            values = list(salary_by_month.values())
            avg = sum(values) / Decimal(len(values))
            return avg.quantize(MONEY_PRECISION, ROUND_HALF_UP)

        fallback = aggregate.customer.annual_income / Decimal("12")
        logger.debug(
            "No salary credits detected for customer_id=%s; using annual_income/12 fallback",
            aggregate.customer.customer_id,
        )
        return fallback.quantize(MONEY_PRECISION, ROUND_HALF_UP)

    @staticmethod
    def _average_monthly_expense(expense_by_month: dict[str, Decimal]) -> Decimal:
        """Rule: Mean of monthly debit totals across months with expense activity."""
        if not expense_by_month:
            return Decimal("0.00")
        values = list(expense_by_month.values())
        avg = sum(values) / Decimal(len(values))
        return avg.quantize(MONEY_PRECISION, ROUND_HALF_UP)

    @staticmethod
    def _savings_ratio(monthly_savings: Decimal, monthly_income: Decimal) -> Decimal:
        """Rule: (monthly_savings / monthly_income) × 100. Returns 0 if income is zero."""
        if monthly_income <= 0:
            return Decimal("0.00")
        ratio = (monthly_savings / monthly_income) * Decimal("100")
        return ratio.quantize(RATIO_PRECISION, ROUND_HALF_UP)

    @staticmethod
    def _average_account_balance(aggregate: CustomerAggregate) -> Decimal:
        """Rule: Arithmetic mean of current balance across all accounts."""
        if not aggregate.accounts:
            return Decimal("0.00")
        total = sum(account.balance for account in aggregate.accounts)
        return (total / Decimal(len(aggregate.accounts))).quantize(MONEY_PRECISION, ROUND_HALF_UP)

    def _estimate_monthly_emi(self, aggregate: CustomerAggregate, monthly_income: Decimal) -> Decimal:
        """
        Rule: For each Active loan product held by the customer, estimate EMI as
        (monthly_income × product-specific income fraction). Summed across all loans.
        """
        if monthly_income <= 0:
            return Decimal("0.00")

        total_emi = Decimal("0")
        for holding in aggregate.products:
            if holding.status != "Active":
                continue
            product_name = holding.product.product_name if holding.product else None
            if product_name not in LOAN_PRODUCT_NAMES:
                continue
            fraction = LOAN_EMI_INCOME_FRACTION[product_name]
            total_emi += monthly_income * fraction

        return total_emi.quantize(MONEY_PRECISION, ROUND_HALF_UP)

    @staticmethod
    def _debt_ratio(monthly_emi: Decimal, monthly_income: Decimal) -> Decimal:
        """Rule: (monthly EMI / monthly income) × 100."""
        if monthly_income <= 0:
            return Decimal("0.00")
        return ((monthly_emi / monthly_income) * Decimal("100")).quantize(RATIO_PRECISION, ROUND_HALF_UP)

    def _investment_ratio(
        self,
        aggregate: CustomerAggregate,
        monthly_income: Decimal,
        window_start: datetime,
        reference_date: datetime,
    ) -> Decimal:
        """
        Rule: Sum of Investment-category DEBIT transactions in 12-month window,
        expressed as a percentage of total monthly income (annualised monthly basis).
        """
        if monthly_income <= 0:
            return Decimal("0.00")

        investment_total = Decimal("0")
        for txn in aggregate.transactions:
            if txn.date < window_start or txn.date > reference_date:
                continue
            if txn.category == "Investment" and txn.transaction_type == "DEBIT":
                investment_total += txn.amount

        # Express total 12-month investment relative to one month's income
        ratio = (investment_total / monthly_income) * Decimal("100")
        return ratio.quantize(RATIO_PRECISION, ROUND_HALF_UP)

    def _cash_flow_score(
        self,
        salary_by_month: dict[str, Decimal],
        expense_by_month: dict[str, Decimal],
        savings_ratio: Decimal,
    ) -> Decimal:
        """
        Rule: Weighted composite 0–100 score:
          40% — Income stability  (lower month-to-month variance → higher score)
          30% — Expense stability (lower month-to-month variance → higher score)
          30% — Savings ratio     (higher savings → higher score, capped at 50% → 100 pts)
        """
        income_stability = self._stability_score(list(salary_by_month.values()))
        expense_stability = self._stability_score(list(expense_by_month.values()))
        savings_score = min(Decimal("100"), max(Decimal("0"), savings_ratio * Decimal("2")))

        composite = (
            income_stability * Decimal("0.40")
            + expense_stability * Decimal("0.30")
            + savings_score * Decimal("0.30")
        )
        return composite.quantize(SCORE_PRECISION, ROUND_HALF_UP)

    @staticmethod
    def _stability_score(monthly_values: list[Decimal]) -> Decimal:
        """
        Rule: Stability = 100 − (coefficient_of_variation × 100), floored at 0.
        CV = population_std_dev / mean. Fewer than 2 data points → perfect stability (100).
        """
        if len(monthly_values) < 2:
            return Decimal("100.00")

        float_values = [float(v) for v in monthly_values]
        avg = mean(float_values)
        if avg == 0:
            return Decimal("100.00")

        cv = pstdev(float_values) / avg
        score = max(0.0, 100.0 - (cv * 100.0))
        return Decimal(str(round(score, 2))).quantize(SCORE_PRECISION, ROUND_HALF_UP)

    def _liquidity_score(
        self,
        average_balance: Decimal,
        monthly_expense: Decimal,
        monthly_income: Decimal,
    ) -> Decimal:
        """
        Rule: Weighted composite 0–100 score:
          40% — Emergency fund coverage (balance covers N months of expenses; 6 months = 100)
          35% — Cash availability      (balance vs 3× monthly income; ratio capped at 100)
          25% — Absolute balance tier  (₹5,00,000+ = 100, linear below)
        """
        emergency_months = (
            float(average_balance / monthly_expense) if monthly_expense > 0 else 10.0
        )
        emergency_score = min(100.0, (emergency_months / 6.0) * 100.0)

        if monthly_income > 0:
            cash_ratio = float(average_balance / (monthly_income * Decimal("3")))
            cash_score = min(100.0, cash_ratio * 100.0)
        else:
            cash_score = 0.0

        balance_score = min(100.0, float(average_balance / Decimal("500000")) * 100.0)

        composite = emergency_score * 0.40 + cash_score * 0.35 + balance_score * 0.25
        return Decimal(str(round(composite, 2))).quantize(SCORE_PRECISION, ROUND_HALF_UP)
