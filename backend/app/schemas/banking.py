"""Pydantic schemas for core banking entities used in aggregation."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CustomerSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customer_id: UUID
    first_name: str
    last_name: str
    gender: str
    date_of_birth: date
    age: int
    phone_number: str
    email: str
    occupation: str
    annual_income: Decimal
    city: str
    state: str
    preferred_language: str
    is_existing_customer: bool
    created_at: datetime
    updated_at: datetime


class AccountSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    account_id: UUID
    customer_id: UUID
    account_number: str
    account_type: str
    branch: str
    ifsc: str
    balance: Decimal
    opened_date: date
    status: str


class TransactionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transaction_id: UUID
    account_id: UUID
    date: datetime
    amount: Decimal
    merchant: str | None
    category: str
    transaction_type: str
    channel: str


class ProductSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: UUID
    product_name: str
    product_type: str
    description: str | None


class CustomerProductSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    customer_product_id: UUID
    customer_id: UUID
    product_id: UUID
    opened_date: date
    status: str
    product: ProductSchema | None = None


class ConsentSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    consent_id: UUID
    customer_id: UUID
    marketing_email: bool
    marketing_sms: bool
    marketing_voice: bool
    marketing_whatsapp: bool
    terms_accepted: bool
    consent_timestamp: datetime
