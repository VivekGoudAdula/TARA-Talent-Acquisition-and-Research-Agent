"""Core banking document entities (MongoDB)."""

from app.db.entity import DocumentEntity


class Customer(DocumentEntity):
    """Banking customer."""


class Account(DocumentEntity):
    """Customer account."""


class Transaction(DocumentEntity):
    """Account transaction."""


class Product(DocumentEntity):
    """Bank product."""


class CustomerProduct(DocumentEntity):
    """Customer-product relationship."""


class Consent(DocumentEntity):
    """Marketing consent record."""
