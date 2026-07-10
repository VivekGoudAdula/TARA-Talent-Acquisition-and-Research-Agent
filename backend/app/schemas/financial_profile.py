"""Financial KPI schemas for the Customer360 analytics layer."""

from decimal import Decimal

from pydantic import BaseModel, Field


class FinancialProfile(BaseModel):
    """
    Deterministic financial KPIs computed from banking transaction data.

    All values are derived via explainable business rules — no ML or LLM.
    """

    monthly_income: Decimal = Field(description="Average monthly salary credits over last 12 months")
    monthly_expense: Decimal = Field(description="Average monthly debit spend over last 12 months")
    monthly_savings: Decimal = Field(description="monthly_income minus monthly_expense")
    savings_ratio: Decimal = Field(description="(monthly_savings / monthly_income) × 100")
    average_balance: Decimal = Field(description="Mean balance across all customer accounts")
    cash_flow_score: Decimal = Field(description="Composite score 0–100 based on income/expense stability and savings")
    liquidity_score: Decimal = Field(description="Composite score 0–100 based on balance and emergency coverage")
    debt_ratio: Decimal = Field(description="(estimated monthly EMI / monthly_income) × 100")
    investment_ratio: Decimal = Field(description="(investment spend / monthly_income) × 100 over 12 months")
    emi_burden: Decimal = Field(description="estimated monthly EMI as percentage of monthly income")


class FinancialAnalyticsResponse(BaseModel):
    """API wrapper returned after computing and persisting financial KPIs."""

    message: str
    financial_profile: FinancialProfile
