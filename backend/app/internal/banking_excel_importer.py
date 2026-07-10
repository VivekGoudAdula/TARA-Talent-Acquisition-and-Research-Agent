"""Internal banking data import from Excel workbooks (IDBI Innovate architecture)."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from uuid import UUID, uuid5

import pandas as pd

from app.external.excel_importer import CITY_STATE_MAP, OCCUPATION_ALIASES
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

INTERNAL_BANKING_NAMESPACE = UUID("8f3e2a10-7c4d-4e5f-9a1b-2d3c4e5f6071")
PRODUCT_NAMESPACE = UUID("9a4b3c20-8d5e-4f60-ab2c-3e4d5f607182")

CITY_LANGUAGE_MAP: dict[str, str] = {
    "Hyderabad": "Telugu",
    "Bangalore": "Kannada",
    "Mumbai": "Marathi",
    "Delhi": "Hindi",
    "Chennai": "Tamil",
    "Pune": "Marathi",
    "Ahmedabad": "Gujarati",
    "Kolkata": "Bengali",
    "Lucknow": "Hindi",
    "Jaipur": "Hindi",
    "Patna": "Hindi",
    "Indore": "Hindi",
    "Visakhapatnam": "Telugu",
    "Vijayawada": "Telugu",
}

STANDARD_PRODUCTS: list[tuple[str, str, str]] = [
    ("Savings Account", "Deposit", "Regular savings account"),
    ("Current Account", "Deposit", "Business current account"),
    ("Personal Loan", "Loan", "Unsecured personal loan"),
    ("Home Loan", "Loan", "Housing finance"),
    ("Car Loan", "Loan", "Vehicle finance"),
    ("Gold Loan", "Loan", "Gold-backed loan"),
    ("Education Loan", "Loan", "Education finance"),
    ("Credit Card", "Card", "Revolving credit card"),
    ("Fixed Deposit", "Deposit", "Term deposit"),
    ("Recurring Deposit", "Deposit", "Monthly recurring deposit"),
]

LOAN_TYPE_MAP: dict[str, str] = {
    "personal loan": "Personal Loan",
    "home loan": "Home Loan",
    "car loan": "Car Loan",
    "auto loan": "Car Loan",
    "gold loan": "Gold Loan",
    "education loan": "Education Loan",
    "business loan": "Personal Loan",
    "mortgage loan": "Home Loan",
}


@dataclass
class BankingImportBundle:
    """All banking collections produced from internal Excel sources."""

    customers: list[dict] = field(default_factory=list)
    products: list[dict] = field(default_factory=list)
    accounts: list[dict] = field(default_factory=list)
    transactions: list[dict] = field(default_factory=list)
    customer_products: list[dict] = field(default_factory=list)
    consent: list[dict] = field(default_factory=list)
    digital_activity: list[dict] = field(default_factory=list)


class BankingExcelImporter:
    """Transforms internal Excel workbooks into MongoDB-ready banking documents."""

    def import_all(
        self,
        *,
        customer_master_path: Path,
        transaction_history_path: Path,
        loan_history_path: Path,
        digital_activity_path: Path,
    ) -> BankingImportBundle:
        bundle = BankingImportBundle()
        bundle.products = self._seed_products()

        customer_df = pd.read_excel(customer_master_path, engine="openpyxl")
        loan_df = pd.read_excel(loan_history_path, engine="openpyxl")
        digital_df = pd.read_excel(digital_activity_path, engine="openpyxl")
        txn_df = pd.read_excel(transaction_history_path, engine="openpyxl")

        customer_refs: dict[str, UUID] = {}
        account_refs: dict[str, UUID] = {}
        now = datetime.utcnow()

        for _, row in customer_df.iterrows():
            ref = str(row["CustomerID"]).strip()
            customer_id = self._uuid(ref)
            customer_refs[ref] = customer_id

            city = str(row["City"]).strip().title()
            state = CITY_STATE_MAP.get(city, "Unknown")
            occupation = self._normalize_occupation(str(row["Occupation"]))
            age = int(row["Age"])
            annual_income = Decimal(str(int(row["AnnualIncome"])))
            relationship_years = int(row.get("RelationshipYears", 0) or 0)
            salary_account = str(row.get("SalaryAccount", "Yes")).strip().lower() in {
                "yes",
                "y",
                "true",
                "1",
            }

            first, last = self._derive_name(ref)
            opened = date.today() - timedelta(days=max(relationship_years, 1) * 365)

            bundle.customers.append(
                {
                    "customer_id": str(customer_id),
                    "first_name": first,
                    "last_name": last,
                    "gender": str(row["Gender"]).strip().title(),
                    "date_of_birth": datetime.combine(
                        date(date.today().year - age, 6, 15), datetime.min.time()
                    ),
                    "age": age,
                    "phone_number": self._derive_phone(ref),
                    "email": self._derive_email(first, last, ref),
                    "occupation": occupation,
                    "annual_income": str(annual_income),
                    "city": city,
                    "state": state,
                    "preferred_language": CITY_LANGUAGE_MAP.get(city, "English"),
                    "is_existing_customer": relationship_years > 0,
                    "created_at": now,
                    "updated_at": now,
                }
            )

            account_id = self._uuid(f"{ref}-account")
            account_refs[ref] = account_id
            balance = (annual_income * Decimal("0.12")).quantize(Decimal("0.01"))
            bundle.accounts.append(
                {
                    "account_id": str(account_id),
                    "customer_id": str(customer_id),
                    "account_number": f"SB{ref[-8:]}",
                    "account_type": "Savings" if salary_account else "Current",
                    "branch": f"{city} Main Branch",
                    "ifsc": "SBIN0001234",
                    "balance": str(balance),
                    "opened_date": datetime.combine(opened, datetime.min.time()),
                    "status": "Active",
                }
            )

            bundle.consent.append(
                {
                    "consent_id": str(self._uuid(f"{ref}-consent")),
                    "customer_id": str(customer_id),
                    "marketing_email": True,
                    "marketing_sms": True,
                    "marketing_voice": True,
                    "marketing_whatsapp": True,
                    "terms_accepted": True,
                    "consent_timestamp": now,
                }
            )

            savings_product_id = self._product_id("Savings Account")
            bundle.customer_products.append(
                {
                    "customer_product_id": str(self._uuid(f"{ref}-savings-product")),
                    "customer_id": str(customer_id),
                    "product_id": str(savings_product_id),
                    "opened_date": datetime.combine(opened, datetime.min.time()),
                    "status": "Active",
                }
            )

        product_id_map = {name: self._product_id(name) for name, _, _ in STANDARD_PRODUCTS}

        for _, row in loan_df.iterrows():
            ref = str(row["CustomerID"]).strip()
            if ref not in customer_refs:
                continue
            loan_type_raw = row.get("LoanType")
            loan_amount = Decimal(str(int(row.get("LoanAmount", 0) or 0)))
            if pd.isna(loan_type_raw) and loan_amount <= 0:
                continue
            loan_name = self._map_loan_type(loan_type_raw, loan_amount)
            if loan_name is None:
                continue
            bundle.customer_products.append(
                {
                    "customer_product_id": str(self._uuid(f"{ref}-loan-{loan_name}")),
                    "customer_id": str(customer_refs[ref]),
                    "product_id": str(product_id_map[loan_name]),
                    "opened_date": datetime.combine(date.today() - timedelta(days=400), datetime.min.time()),
                    "status": "Active" if Decimal(str(row.get("Outstanding", 0) or 0)) > 0 else "Closed",
                }
            )

        for row_idx, row in txn_df.iterrows():
            ref = str(row["CustomerID"]).strip()
            if ref not in account_refs:
                continue
            account_id = account_refs[ref]
            month = str(row["Month"]).strip()
            txn_date = self._parse_month(month)
            bundle.transactions.extend(
                self._expand_monthly_transactions(ref, account_id, txn_date, row, row_idx, month)
            )

        for _, row in digital_df.iterrows():
            ref = str(row["CustomerID"]).strip()
            if ref not in customer_refs:
                continue
            bundle.digital_activity.append(
                {
                    "customer_id": str(customer_refs[ref]),
                    "external_customer_ref": ref,
                    "net_banking_logins": int(row.get("NetBankingLogins", 0) or 0),
                    "mobile_app_logins": int(row.get("MobileAppLogins", 0) or 0),
                    "upi_transactions": int(row.get("UPITransactions", 0) or 0),
                    "bill_payments": int(row.get("BillPayments", 0) or 0),
                    "investment_transactions": int(row.get("InvestmentTransactions", 0) or 0),
                }
            )

        logger.info(
            "Banking Excel import: customers=%d accounts=%d transactions=%d digital_activity=%d",
            len(bundle.customers),
            len(bundle.accounts),
            len(bundle.transactions),
            len(bundle.digital_activity),
        )
        return bundle

    def _expand_monthly_transactions(
        self,
        ref: str,
        account_id: UUID,
        txn_date: datetime,
        row: pd.Series,
        row_idx: int,
        month: str,
    ) -> list[dict]:
        txns: list[dict] = []
        salary = Decimal(str(int(row.get("SalaryCredit", 0) or 0)))
        total_debit = Decimal(str(int(row.get("TotalDebit", 0) or 0)))
        upi_count = int(row.get("UPICount", 0) or 0)
        neft = int(row.get("NEFT", 0) or 0)
        imps = int(row.get("IMPS", 0) or 0)

        suffix = f"{month}-{row_idx}"

        if salary > 0:
            txns.append(
                self._txn(
                    ref,
                    account_id,
                    txn_date.replace(day=1, hour=10),
                    salary,
                    "Salary",
                    "credit",
                    "NEFT",
                    "Salary Credit",
                    suffix,
                )
            )

        if total_debit > 0:
            channel = "UPI" if upi_count >= max(neft, imps, 1) else "Net Banking"
            txns.append(
                self._txn(
                    ref,
                    account_id,
                    txn_date.replace(day=5, hour=14),
                    total_debit,
                    "General",
                    "debit",
                    channel,
                    "Monthly Expenses",
                    f"{suffix}-debit",
                )
            )

        return txns

    def _txn(
        self,
        ref: str,
        account_id: UUID,
        when: datetime,
        amount: Decimal,
        category: str,
        txn_type: str,
        channel: str,
        merchant: str,
        unique_suffix: str = "",
    ) -> dict:
        key = f"{ref}-{when.isoformat()}-{category}-{channel}-{amount}-{merchant}-{unique_suffix}"
        return {
            "transaction_id": str(self._uuid(key)),
            "account_id": str(account_id),
            "date": when,
            "amount": str(amount.quantize(Decimal("0.01"), ROUND_HALF_UP)),
            "merchant": merchant,
            "category": category,
            "transaction_type": txn_type,
            "channel": channel,
        }

    def _seed_products(self) -> list[dict]:
        products: list[dict] = []
        for name, ptype, desc in STANDARD_PRODUCTS:
            products.append(
                {
                    "product_id": str(self._product_id(name)),
                    "product_name": name,
                    "product_type": ptype,
                    "description": desc,
                }
            )
        return products

    @staticmethod
    def _uuid(key: str) -> UUID:
        return uuid5(INTERNAL_BANKING_NAMESPACE, key)

    def _product_id(self, product_name: str) -> UUID:
        return uuid5(PRODUCT_NAMESPACE, product_name)

    @staticmethod
    def _parse_month(month: str) -> datetime:
        try:
            parsed = datetime.strptime(month.strip(), "%Y-%m")
        except ValueError:
            parsed = datetime.utcnow()
        return parsed.replace(day=15, hour=12, minute=0, second=0, microsecond=0)

    @staticmethod
    def _normalize_occupation(raw: str) -> str:
        key = raw.strip().lower()
        return OCCUPATION_ALIASES.get(key, raw.strip().title() or "Unknown")

    @staticmethod
    def _derive_name(ref: str) -> tuple[str, str]:
        digest = hashlib.sha256(ref.encode()).hexdigest()
        first_names = ["Aarav", "Priya", "Rohan", "Ananya", "Vikram", "Kavya", "Arjun", "Meera"]
        last_names = ["Sharma", "Patel", "Reddy", "Iyer", "Singh", "Gupta", "Nair", "Das"]
        fi = int(digest[:2], 16) % len(first_names)
        li = int(digest[2:4], 16) % len(last_names)
        return first_names[fi], last_names[li]

    @staticmethod
    def _derive_phone(ref: str) -> str:
        digits = "".join(str(int(c, 16) % 10) for c in hashlib.sha256(ref.encode()).hexdigest()[:10])
        return f"+91{digits}"

    @staticmethod
    def _derive_email(first: str, last: str, ref: str) -> str:
        slug = re.sub(r"[^a-z0-9]", "", f"{first}{last}".lower())[:20]
        suffix = re.sub(r"[^A-Z0-9]", "", ref.upper())[-6:]
        return f"{slug}.{suffix}@customers.tara.bank".lower()

    @staticmethod
    def _map_loan_type(raw: object, amount: Decimal) -> str | None:
        if amount <= 0:
            return None
        if raw is None or (isinstance(raw, float) and pd.isna(raw)):
            return "Personal Loan"
        text = str(raw).strip().lower()
        if not text or text == "nan":
            return "Personal Loan"
        mapped = LOAN_TYPE_MAP.get(text, text.title())
        known = {name for name, _, _ in STANDARD_PRODUCTS}
        return mapped if mapped in known else "Personal Loan"
