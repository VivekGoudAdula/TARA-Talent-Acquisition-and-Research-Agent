"""
Synthetic Banking Dataset Generator for SBI Tara Platform.

Generates realistic Indian banking data for customers, accounts, transactions,
products, customer-product assignments, and consent records.

Outputs CSV files and a seed.sql file (optional reference export).
Scale by changing NUM_CUSTOMERS.
"""

from __future__ import annotations

import csv
import os
import random
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
from faker import Faker

from db_env import load_db_env

load_db_env()

# ---------------------------------------------------------------------------
# Configuration — change this single constant to scale the dataset
# ---------------------------------------------------------------------------
NUM_CUSTOMERS = 100

OUTPUT_DIR = Path(__file__).parent / "output"
RANDOM_SEED = 42

# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------
OCCUPATIONS = [
    "Software Engineer",
    "Doctor",
    "Teacher",
    "Government Employee",
    "Business Owner",
    "Farmer",
    "Lawyer",
    "Chartered Accountant",
    "Student",
    "Retired",
    "Sales Executive",
    "Nurse",
    "Professor",
    "Police Officer",
]

CITIES = [
    "Hyderabad",
    "Bangalore",
    "Mumbai",
    "Delhi",
    "Chennai",
    "Pune",
    "Ahmedabad",
    "Kolkata",
    "Lucknow",
    "Jaipur",
    "Visakhapatnam",
    "Vijayawada",
]

CITY_STATE_MAP = {
    "Hyderabad": "Telangana",
    "Bangalore": "Karnataka",
    "Mumbai": "Maharashtra",
    "Delhi": "Delhi",
    "Chennai": "Tamil Nadu",
    "Pune": "Maharashtra",
    "Ahmedabad": "Gujarat",
    "Kolkata": "West Bengal",
    "Lucknow": "Uttar Pradesh",
    "Jaipur": "Rajasthan",
    "Visakhapatnam": "Andhra Pradesh",
    "Vijayawada": "Andhra Pradesh",
}

PREFERRED_LANGUAGES = [
    "English",
    "Hindi",
    "Telugu",
    "Tamil",
    "Kannada",
    "Marathi",
]

CITY_LANGUAGE_BIAS = {
    "Hyderabad": {"Telugu": 0.45, "Hindi": 0.25, "English": 0.30},
    "Bangalore": {"Kannada": 0.40, "English": 0.35, "Hindi": 0.25},
    "Mumbai": {"Marathi": 0.35, "Hindi": 0.35, "English": 0.30},
    "Delhi": {"Hindi": 0.55, "English": 0.45},
    "Chennai": {"Tamil": 0.55, "English": 0.30, "Hindi": 0.15},
    "Pune": {"Marathi": 0.45, "Hindi": 0.25, "English": 0.30},
    "Ahmedabad": {"Hindi": 0.40, "English": 0.35, "Marathi": 0.25},
    "Kolkata": {"Hindi": 0.40, "English": 0.35, "Tamil": 0.25},
    "Lucknow": {"Hindi": 0.60, "English": 0.40},
    "Jaipur": {"Hindi": 0.55, "English": 0.45},
    "Visakhapatnam": {"Telugu": 0.50, "English": 0.30, "Hindi": 0.20},
    "Vijayawada": {"Telugu": 0.55, "English": 0.30, "Hindi": 0.15},
}

ACCOUNT_TYPES = ["Savings", "Current", "Salary"]

SBI_PRODUCTS = [
    ("Savings Account", "Deposit"),
    ("Current Account", "Deposit"),
    ("Salary Account", "Deposit"),
    ("Credit Card", "Credit"),
    ("Personal Loan", "Loan"),
    ("Home Loan", "Loan"),
    ("Car Loan", "Loan"),
    ("Gold Loan", "Loan"),
    ("Education Loan", "Loan"),
    ("Fixed Deposit", "Investment"),
    ("Recurring Deposit", "Investment"),
    ("Life Insurance", "Insurance"),
    ("Health Insurance", "Insurance"),
    ("Mutual Fund", "Investment"),
]

MERCHANTS = [
    "Amazon",
    "Flipkart",
    "Swiggy",
    "Zomato",
    "Myntra",
    "Ajio",
    "IRCTC",
    "Indian Oil",
    "HP Petrol",
    "Reliance Fresh",
    "DMart",
    "Netflix",
    "Spotify",
    "BigBasket",
    "Apollo Pharmacy",
    "Uber",
    "Ola",
    "Paytm",
    "PhonePe",
    "Google Pay",
]

MERCHANT_CATEGORY = {
    "Amazon": "Shopping",
    "Flipkart": "Shopping",
    "Swiggy": "Food",
    "Zomato": "Food",
    "Myntra": "Shopping",
    "Ajio": "Shopping",
    "IRCTC": "Travel",
    "Indian Oil": "Fuel",
    "HP Petrol": "Fuel",
    "Reliance Fresh": "Shopping",
    "DMart": "Shopping",
    "Netflix": "Entertainment",
    "Spotify": "Entertainment",
    "BigBasket": "Shopping",
    "Apollo Pharmacy": "Healthcare",
    "Uber": "Travel",
    "Ola": "Travel",
    "Paytm": "UPI Transfer",
    "PhonePe": "UPI Transfer",
    "Google Pay": "UPI Transfer",
}

TRANSACTION_CATEGORIES = [
    "Shopping",
    "Food",
    "Fuel",
    "Travel",
    "Healthcare",
    "Entertainment",
    "Bills",
    "Salary",
    "Investment",
    "UPI Transfer",
    "ATM Withdrawal",
]

CHANNELS = [
    "UPI",
    "Net Banking",
    "Debit Card",
    "ATM",
    "Mobile Banking",
    "NEFT",
    "IMPS",
]

# Annual income ranges (INR) by occupation — (min, max)
OCCUPATION_INCOME = {
    "Software Engineer": (800_000, 3_500_000),
    "Doctor": (1_200_000, 5_000_000),
    "Teacher": (300_000, 900_000),
    "Government Employee": (400_000, 1_200_000),
    "Business Owner": (600_000, 8_000_000),
    "Farmer": (150_000, 800_000),
    "Lawyer": (800_000, 4_000_000),
    "Chartered Accountant": (700_000, 3_000_000),
    "Student": (0, 200_000),
    "Retired": (200_000, 1_000_000),
    "Sales Executive": (350_000, 1_500_000),
    "Nurse": (250_000, 700_000),
    "Professor": (600_000, 1_800_000),
    "Police Officer": (400_000, 1_100_000),
}

# Typical age ranges by occupation
OCCUPATION_AGE = {
    "Software Engineer": (22, 45),
    "Doctor": (28, 60),
    "Teacher": (24, 58),
    "Government Employee": (25, 58),
    "Business Owner": (30, 65),
    "Farmer": (25, 70),
    "Lawyer": (26, 65),
    "Chartered Accountant": (24, 60),
    "Student": (18, 25),
    "Retired": (58, 70),
    "Sales Executive": (22, 50),
    "Nurse": (22, 55),
    "Professor": (30, 65),
    "Police Officer": (22, 55),
}

SBI_BRANCH_PREFIX = {
    "Hyderabad": "SBIN0020001",
    "Bangalore": "SBIN0040001",
    "Mumbai": "SBIN0000400",
    "Delhi": "SBIN0000691",
    "Chennai": "SBIN0000837",
    "Pune": "SBIN0001114",
    "Ahmedabad": "SBIN0060076",
    "Kolkata": "SBIN0000093",
    "Lucknow": "SBIN0000102",
    "Jaipur": "SBIN0031025",
    "Visakhapatnam": "SBIN0007890",
    "Vijayawada": "SBIN0012345",
}


@dataclass
class GeneratedData:
    """Container for all generated dataset tables."""

    customers: pd.DataFrame
    accounts: pd.DataFrame
    transactions: pd.DataFrame
    products: pd.DataFrame
    customer_products: pd.DataFrame
    consent: pd.DataFrame


def setup_faker(seed: int = RANDOM_SEED) -> Faker:
    """Initialize Faker with Indian locale and fixed seed for reproducibility."""
    fake = Faker("en_IN")
    Faker.seed(seed)
    random.seed(seed)
    return fake


def weighted_choice(options: dict[str, float]) -> str:
    """Select a key based on weighted probabilities."""
    keys = list(options.keys())
    weights = list(options.values())
    return random.choices(keys, weights=weights, k=1)[0]


def generate_indian_phone(fake: Faker) -> str:
    """Generate a valid 10-digit Indian mobile number."""
    prefixes = ["6", "7", "8", "9"]
    return f"+91{random.choice(prefixes)}{fake.numerify('#########')}"


def age_from_dob(dob: date, reference: date | None = None) -> int:
    """Calculate age from date of birth."""
    ref = reference or date.today()
    return ref.year - dob.year - ((ref.month, ref.day) < (dob.month, dob.day))


def generate_customers(fake: Faker, num_customers: int) -> pd.DataFrame:
    """Generate customer records with realistic Indian demographics."""
    records: list[dict[str, Any]] = []
    today = date.today()

    for _ in range(num_customers):
        customer_id = str(uuid.uuid4())
        gender = random.choice(["Male", "Female"])
        first_name = fake.first_name_male() if gender == "Male" else fake.first_name_female()
        last_name = fake.last_name()
        occupation = random.choice(OCCUPATIONS)
        age_min, age_max = OCCUPATION_AGE[occupation]
        age = random.randint(max(18, age_min), min(70, age_max))
        dob = today - timedelta(days=age * 365 + random.randint(0, 364))
        city = random.choice(CITIES)
        state = CITY_STATE_MAP[city]
        language = weighted_choice(CITY_LANGUAGE_BIAS[city])
        income_min, income_max = OCCUPATION_INCOME[occupation]
        if occupation == "Student":
            annual_income = round(random.uniform(0, income_max), 2)
        else:
            annual_income = round(random.uniform(income_min, income_max), 2)

        email_local = f"{first_name.lower()}.{last_name.lower()}{random.randint(1, 999)}"
        email = f"{email_local}@{random.choice(['gmail.com', 'yahoo.in', 'outlook.com', 'rediffmail.com'])}"
        is_existing = random.random() < 0.35
        created_at = fake.date_time_between(start_date="-3y", end_date="-30d")
        updated_at = fake.date_time_between(start_date=created_at, end_date="now")

        records.append(
            {
                "customer_id": customer_id,
                "first_name": first_name,
                "last_name": last_name,
                "gender": gender,
                "date_of_birth": dob.isoformat(),
                "age": age_from_dob(dob),
                "phone_number": generate_indian_phone(fake),
                "email": email,
                "occupation": occupation,
                "annual_income": annual_income,
                "city": city,
                "state": state,
                "preferred_language": language,
                "is_existing_customer": is_existing,
                "created_at": created_at.isoformat(sep=" ", timespec="seconds"),
                "updated_at": updated_at.isoformat(sep=" ", timespec="seconds"),
            }
        )

    return pd.DataFrame(records)


def generate_products() -> pd.DataFrame:
    """Generate SBI product catalog."""
    records = []
    for name, ptype in SBI_PRODUCTS:
        records.append(
            {
                "product_id": str(uuid.uuid4()),
                "product_name": name,
                "product_type": ptype,
                "description": f"SBI {name} — tailored for Indian retail and corporate banking needs.",
            }
        )
    return pd.DataFrame(records)


def generate_accounts(customers: pd.DataFrame, fake: Faker) -> pd.DataFrame:
    """Generate 1–3 bank accounts per customer."""
    records: list[dict[str, Any]] = []
    used_account_numbers: set[str] = set()

    for _, customer in customers.iterrows():
        num_accounts = random.randint(1, 3)
        types = random.sample(ACCOUNT_TYPES, k=min(num_accounts, len(ACCOUNT_TYPES)))
        if num_accounts > len(types):
            types += random.choices(ACCOUNT_TYPES, k=num_accounts - len(types))

        customer_created = datetime.fromisoformat(customer["created_at"])
        city = customer["city"]
        branch = f"State Bank of India, {city} Main Branch"
        ifsc = SBI_BRANCH_PREFIX[city]

        for account_type in types:
            account_number = fake.unique.numerify("###########")
            while account_number in used_account_numbers:
                account_number = fake.numerify("###########")
            used_account_numbers.add(account_number)

            monthly_income = float(customer["annual_income"]) / 12
            if account_type == "Savings":
                balance = round(random.uniform(max(5_000, monthly_income * 0.5), monthly_income * 6), 2)
            elif account_type == "Salary":
                balance = round(random.uniform(monthly_income * 0.3, monthly_income * 2), 2)
            else:
                balance = round(random.uniform(50_000, max(100_000, monthly_income * 12)), 2)

            opened_date = fake.date_between(
                start_date=customer_created.date() - timedelta(days=365 * 5),
                end_date=customer_created.date(),
            )

            records.append(
                {
                    "account_id": str(uuid.uuid4()),
                    "customer_id": customer["customer_id"],
                    "account_number": account_number,
                    "account_type": account_type,
                    "branch": branch,
                    "ifsc": ifsc,
                    "balance": balance,
                    "opened_date": opened_date.isoformat(),
                    "status": random.choices(["Active", "Inactive", "Dormant"], weights=[0.88, 0.08, 0.04])[0],
                }
            )

    return pd.DataFrame(records)


def _transaction_amount(category: str, monthly_income: float) -> float:
    """Derive realistic transaction amounts by category."""
    ranges = {
        "Shopping": (200, 15_000),
        "Food": (80, 1_500),
        "Fuel": (500, 4_000),
        "Travel": (300, 25_000),
        "Healthcare": (150, 8_000),
        "Entertainment": (199, 1_500),
        "Bills": (500, 12_000),
        "Salary": (monthly_income * 0.8, monthly_income * 1.1),
        "Investment": (1_000, 50_000),
        "UPI Transfer": (100, 25_000),
        "ATM Withdrawal": (500, 10_000),
    }
    low, high = ranges.get(category, (100, 5_000))
    return round(random.uniform(low, min(high, max(low, monthly_income * 0.5))), 2)


def generate_transactions(
    accounts: pd.DataFrame,
    customers: pd.DataFrame,
    fake: Faker,
    min_txn: int = 80,
    max_txn: int = 150,
) -> pd.DataFrame:
    """Generate 80–150 transactions per account over the last 12 months."""
    customer_income = customers.set_index("customer_id")["annual_income"].to_dict()
    records: list[dict[str, Any]] = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)

    for _, account in accounts.iterrows():
        num_txns = random.randint(min_txn, max_txn)

        monthly_income = float(customer_income[account["customer_id"]]) / 12
        salary_day = random.randint(1, 5)
        account_records: list[dict[str, Any]] = []

        if account["account_type"] in ("Salary", "Savings"):
            for month_offset in range(12):
                month_start = start_date + timedelta(days=30 * month_offset)
                salary_date = month_start.replace(day=min(salary_day, 28))
                account_records.append(
                    {
                        "transaction_id": str(uuid.uuid4()),
                        "account_id": account["account_id"],
                        "date": salary_date.isoformat(sep=" ", timespec="seconds"),
                        "amount": round(monthly_income * random.uniform(0.85, 1.0), 2),
                        "merchant": "SBI Payroll",
                        "category": "Salary",
                        "transaction_type": "CREDIT",
                        "channel": random.choice(["NEFT", "IMPS", "Mobile Banking"]),
                    }
                )

        remaining = max(0, num_txns - len(account_records))
        for _ in range(remaining):
            txn_time = fake.date_time_between(start_date=start_date, end_date=end_date)
            roll = random.random()

            if roll < 0.05:
                category = "ATM Withdrawal"
                merchant = None
                channel = "ATM"
            elif roll < 0.12:
                category = "Bills"
                merchant = random.choice(["Paytm", "PhonePe", "Google Pay"])
                channel = random.choice(["UPI", "Net Banking", "Mobile Banking"])
            elif roll < 0.18:
                category = "Investment"
                merchant = "SBI Mutual Fund"
                channel = random.choice(["Net Banking", "Mobile Banking"])
            else:
                merchant = random.choice(MERCHANTS)
                category = MERCHANT_CATEGORY[merchant]
                channel = random.choice(
                    ["UPI", "Debit Card", "Net Banking", "Mobile Banking"]
                    if merchant not in ("Paytm", "PhonePe", "Google Pay")
                    else ["UPI"]
                )

            amount = _transaction_amount(category, monthly_income)
            txn_type = "CREDIT" if category == "Salary" else "DEBIT"

            account_records.append(
                {
                    "transaction_id": str(uuid.uuid4()),
                    "account_id": account["account_id"],
                    "date": txn_time.isoformat(sep=" ", timespec="seconds"),
                    "amount": amount,
                    "merchant": merchant,
                    "category": category,
                    "transaction_type": txn_type,
                    "channel": channel,
                }
            )

        records.extend(account_records)

    return pd.DataFrame(records)


def _product_lookup(products: pd.DataFrame) -> dict[str, str]:
    return products.set_index("product_name")["product_id"].to_dict()


def assign_products(customers: pd.DataFrame, products: pd.DataFrame, fake: Faker) -> pd.DataFrame:
    """Assign realistic SBI products based on customer profile."""
    pid = _product_lookup(products)
    records: list[dict[str, Any]] = []

    for _, customer in customers.iterrows():
        age = int(customer["age"])
        occupation = customer["occupation"]
        income = float(customer["annual_income"])
        assigned: set[str] = set()

        def add_product(name: str, status_weights: list[tuple[str, float]] | None = None) -> None:
            if name in assigned:
                return
            assigned.add(name)
            opened = fake.date_between(start_date="-5y", end_date="-1m")
            if status_weights:
                status = random.choices([s for s, _ in status_weights], weights=[w for _, w in status_weights])[0]
            else:
                status = random.choices(["Active", "Closed", "Pending"], weights=[0.85, 0.10, 0.05])[0]
            records.append(
                {
                    "customer_product_id": str(uuid.uuid4()),
                    "customer_id": customer["customer_id"],
                    "product_id": pid[name],
                    "opened_date": opened.isoformat(),
                    "status": status,
                }
            )

        # Base deposit account mapping
        if occupation == "Business Owner":
            add_product("Current Account")
            add_product("Savings Account")
            if income > 500_000:
                add_product("Personal Loan")
        elif occupation == "Student":
            add_product("Savings Account")
            if age >= 21:
                add_product("Credit Card", [("Active", 0.4), ("Pending", 0.6)])
        elif occupation == "Retired":
            add_product("Savings Account")
            add_product("Fixed Deposit")
            add_product("Life Insurance")
        elif occupation in ("Software Engineer", "Doctor", "Lawyer", "Chartered Accountant"):
            add_product("Salary Account")
            add_product("Credit Card")
            if age >= 28 and income > 800_000:
                add_product("Mutual Fund")
            if age >= 30 and income > 1_500_000:
                add_product(random.choice(["Home Loan", "Car Loan"]))
        elif occupation == "Government Employee":
            add_product("Salary Account")
            add_product("Recurring Deposit")
            add_product("Health Insurance")
        elif occupation == "Farmer":
            add_product("Savings Account")
            if income > 300_000:
                add_product("Gold Loan")
        elif occupation == "Teacher":
            add_product("Salary Account")
            add_product("Recurring Deposit")
        else:
            add_product("Savings Account")
            if income > 400_000:
                add_product("Credit Card")

        # Cross-sell based on demographics
        if age >= 35 and income > 600_000 and "Health Insurance" not in assigned:
            if random.random() < 0.45:
                add_product("Health Insurance")

        if age >= 25 and age <= 40 and "Education Loan" not in assigned:
            if occupation in ("Teacher", "Professor", "Student") and random.random() < 0.2:
                add_product("Education Loan")

        if income > 2_000_000 and "Mutual Fund" not in assigned and random.random() < 0.5:
            add_product("Mutual Fund")

        if not assigned:
            add_product("Savings Account")

    return pd.DataFrame(records)


def generate_consent(customers: pd.DataFrame, fake: Faker) -> pd.DataFrame:
    """Generate one consent record per customer."""
    records: list[dict[str, Any]] = []

    for _, customer in customers.iterrows():
        created = datetime.fromisoformat(customer["created_at"])
        consent_time = fake.date_time_between(start_date=created, end_date="now")
        records.append(
            {
                "consent_id": str(uuid.uuid4()),
                "customer_id": customer["customer_id"],
                "marketing_email": random.random() < 0.55,
                "marketing_sms": random.random() < 0.62,
                "marketing_voice": random.random() < 0.28,
                "marketing_whatsapp": random.random() < 0.48,
                "terms_accepted": True,
                "consent_timestamp": consent_time.isoformat(sep=" ", timespec="seconds"),
            }
        )

    return pd.DataFrame(records)


def export_csv(data: GeneratedData, output_dir: Path) -> None:
    """Write all tables to CSV files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    data.customers.to_csv(output_dir / "customers.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    data.accounts.to_csv(output_dir / "accounts.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    data.transactions.to_csv(output_dir / "transactions.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    data.products.to_csv(output_dir / "products.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    data.customer_products.to_csv(output_dir / "customer_products.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    data.consent.to_csv(output_dir / "consent.csv", index=False, quoting=csv.QUOTE_MINIMAL)


def _sql_value(value: Any, col: str) -> str:
    """Format a Python value as a SQL literal."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if col in ("annual_income", "balance", "amount"):
        return str(float(value))
    if isinstance(value, (int, float)):
        return str(value)
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def export_seed_sql(data: GeneratedData, output_dir: Path) -> Path:
    """Generate SQL INSERT statements for all tables."""
    output_dir.mkdir(parents=True, exist_ok=True)
    seed_path = output_dir / "seed.sql"

    table_order = [
        ("customers", data.customers),
        ("products", data.products),
        ("accounts", data.accounts),
        ("transactions", data.transactions),
        ("customer_products", data.customer_products),
        ("consent", data.consent),
    ]

    lines = [
        "-- SBI Tara Synthetic Banking Dataset",
        f"-- Generated: {datetime.now().isoformat()}",
        f"-- Customers: {len(data.customers)}",
        "",
        "BEGIN;",
        "",
    ]

    for table_name, df in table_order:
        if df.empty:
            continue
        columns = ", ".join(df.columns)
        lines.append(f"-- {table_name}: {len(df)} rows")
        for _, row in df.iterrows():
            values = ", ".join(_sql_value(row[col], col) for col in df.columns)
            lines.append(f"INSERT INTO {table_name} ({columns}) VALUES ({values});")
        lines.append("")

    lines.append("COMMIT;")
    seed_path.write_text("\n".join(lines), encoding="utf-8")
    return seed_path


def generate_dataset(num_customers: int = NUM_CUSTOMERS) -> GeneratedData:
    """Orchestrate full dataset generation."""
    fake = setup_faker()
    print(f"Generating {num_customers} customers...")

    customers = generate_customers(fake, num_customers)
    products = generate_products()
    accounts = generate_accounts(customers, fake)
    transactions = generate_transactions(accounts, customers, fake)
    customer_products = assign_products(customers, products, fake)
    consent = generate_consent(customers, fake)

    return GeneratedData(
        customers=customers,
        accounts=accounts,
        transactions=transactions,
        products=products,
        customer_products=customer_products,
        consent=consent,
    )


def print_summary(data: GeneratedData) -> None:
    """Print dataset generation summary."""
    print("\n=== Dataset Summary ===")
    print(f"Customers:          {len(data.customers):>8,}")
    print(f"Accounts:           {len(data.accounts):>8,}")
    print(f"Transactions:       {len(data.transactions):>8,}")
    print(f"Products:           {len(data.products):>8,}")
    print(f"Customer Products:  {len(data.customer_products):>8,}")
    print(f"Consent records:    {len(data.consent):>8,}")
    print(f"\nAvg accounts/customer: {len(data.accounts) / len(data.customers):.2f}")
    print(f"Avg txns/account:      {len(data.transactions) / len(data.accounts):.2f}")


def main() -> None:
    """Entry point: generate CSVs and seed.sql."""
    data = generate_dataset(NUM_CUSTOMERS)
    print_summary(data)

    export_csv(data, OUTPUT_DIR)
    seed_path = export_seed_sql(data, OUTPUT_DIR)

    print(f"\nCSV files written to: {OUTPUT_DIR.resolve()}")
    print(f"Seed SQL written to:    {seed_path.resolve()}")


if __name__ == "__main__":
    main()
