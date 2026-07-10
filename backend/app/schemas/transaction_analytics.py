"""Transaction intelligence KPI schemas."""

from decimal import Decimal

from pydantic import BaseModel, Field


class TransactionAnalyticsProfile(BaseModel):
    """Complete transaction analytics output — deterministic, explainable KPIs."""

    average_transaction_amount: Decimal = Field(description="Mean amount across all transactions in window")
    monthly_transaction_count: Decimal = Field(description="Average number of transactions per month")
    debit_transaction_count: int = Field(description="Total debit transactions in window")
    credit_transaction_count: int = Field(description="Total credit transactions in window")
    debit_credit_ratio: Decimal = Field(description="debit_count / credit_count")
    cash_withdrawal_frequency: Decimal = Field(description="Average ATM withdrawals per month")
    cash_deposit_frequency: Decimal = Field(description="Average cash deposits per month")
    upi_transaction_count: int = Field(description="Transactions via UPI channel")
    card_transaction_count: int = Field(description="Transactions via Debit Card channel")
    net_banking_transaction_count: int = Field(description="Transactions via Net Banking channel")
    mobile_banking_transaction_count: int = Field(description="Transactions via Mobile Banking channel")
    digital_payment_ratio: Decimal = Field(description="Digital channel txns / total × 100")
    merchant_diversity: int = Field(description="Count of unique merchants")
    category_diversity: int = Field(description="Count of unique categories")
    most_frequent_merchant: str | None = Field(description="Merchant with highest transaction count")
    most_frequent_category: str | None = Field(description="Category with highest transaction count")
    highest_transaction_amount: Decimal = Field(description="Largest transaction by amount")
    lowest_transaction_amount: Decimal = Field(description="Smallest transaction by amount")
    largest_credit_transaction: Decimal = Field(description="Largest credit transaction amount")
    largest_debit_transaction: Decimal = Field(description="Largest debit transaction amount")
    transaction_consistency_score: Decimal = Field(description="Monthly txn count stability 0–100")
    income_regularity_score: Decimal = Field(description="Salary credit consistency 0–100")
    expense_stability_score: Decimal = Field(description="Monthly expense variance score 0–100")
    weekend_transaction_percentage: Decimal = Field(description="Weekend txns / total × 100")
    night_transaction_percentage: Decimal = Field(description="Night txns (22:00–06:00) / total × 100")


class TransactionAnalyticsResponse(BaseModel):
    message: str
    analytics: TransactionAnalyticsProfile


class TransactionBuildAllResponse(BaseModel):
    message: str
    customers_processed: int
    customers_succeeded: int
    customers_failed: int
