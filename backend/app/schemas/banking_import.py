"""Response schema for internal banking Excel import."""

from pydantic import BaseModel, Field


class BankingImportResponse(BaseModel):
    message: str
    customers: int = 0
    products: int = 0
    accounts: int = 0
    transactions: int = 0
    customer_products: int = 0
    consent: int = 0
    customer_master_path: str | None = None
    transaction_history_path: str | None = None
    loan_history_path: str | None = None
    digital_activity_path: str | None = None
