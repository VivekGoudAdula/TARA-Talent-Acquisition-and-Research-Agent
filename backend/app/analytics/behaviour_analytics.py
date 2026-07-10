"""
Behaviour Analytics Engine — deterministic lifestyle and spending behaviour analysis.

Uses configurable merchant classification (config/merchant_categories.json).
Does NOT recommend products, calculate risk, or use ML/LLM.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from statistics import pstdev

from app.schemas.banking import TransactionSchema
from app.schemas.behaviour_analytics import (
    BehaviourProfile,
    EducationBehaviourResult,
    EntertainmentBehaviourResult,
    FoodBehaviourResult,
    FuelBehaviourResult,
    HealthcareBehaviourResult,
    InvestmentBehaviourResult,
    ShoppingBehaviourResult,
    TravelBehaviourResult,
)
from app.schemas.behaviour_input import BehaviourAnalyticsInput
from app.schemas.customer360 import CustomerAggregate
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "merchant_categories.json"
LOOKBACK_DAYS = 365
MONEY = Decimal("0.01")
SCORE = Decimal("0.01")
RATIO = Decimal("0.01")
LUXURY_AMOUNT_THRESHOLD = Decimal("5000")
BUDGET_AMOUNT_THRESHOLD = Decimal("1500")
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

RESTAURANT_MERCHANTS = frozenset({"Dominos", "KFC", "McDonalds", "Pizza Hut"})
DELIVERY_MERCHANTS = frozenset({"Swiggy", "Zomato"})
OTT_MERCHANTS = frozenset({"Netflix", "Amazon Prime", "Disney Hotstar", "Sony LIV"})
MUSIC_MERCHANTS = frozenset({"Spotify"})
MOVIE_MERCHANTS = frozenset({"BookMyShow"})
STOCK_MERCHANTS = frozenset({"Groww", "Zerodha", "Upstox", "Angel One"})
MF_MERCHANTS = frozenset({"SBI Mutual Fund", "Paytm Money"})
PHARMACY_MERCHANTS = frozenset({"Apollo Pharmacy", "MedPlus"})
HOSPITAL_MERCHANTS = frozenset({"Hospitals", "Fortis Healthcare", "Max Healthcare"})
TRANSPORT_MERCHANTS = frozenset({"Uber", "Ola"})
RAIL_AIR_MERCHANTS = frozenset({"IRCTC", "Indigo", "Air India", "MakeMyTrip", "Goibibo"})


class MerchantCategoryConfig:
    """Loads and resolves merchant → behaviour category from external JSON config."""

    def __init__(self, config_path: Path = CONFIG_PATH) -> None:
        with config_path.open(encoding="utf-8") as f:
            raw: dict = json.load(f)

        self._merchant_to_category: dict[str, str] = {}
        self._luxury_merchants: set[str] = set()
        self._budget_merchants: set[str] = set()
        self.categories: list[str] = list(raw.keys())

        for category, cfg in raw.items():
            for merchant in cfg.get("merchants", []):
                self._merchant_to_category[merchant.lower()] = category
            for merchant in cfg.get("luxury_merchants", []):
                self._luxury_merchants.add(merchant.lower())
            for merchant in cfg.get("budget_merchants", []):
                self._budget_merchants.add(merchant.lower())

    def resolve_category(self, merchant: str | None, txn_category: str | None) -> str | None:
        if merchant and merchant.lower() in self._merchant_to_category:
            return self._merchant_to_category[merchant.lower()]
        if txn_category and txn_category in self.categories:
            return txn_category
        return None

    def is_luxury(self, merchant: str | None) -> bool:
        return bool(merchant and merchant.lower() in self._luxury_merchants)

    def is_budget(self, merchant: str | None) -> bool:
        return bool(merchant and merchant.lower() in self._budget_merchants)


def _money_sum(amounts) -> Decimal:
    return sum(amounts, Decimal("0"))


def _window_debits(aggregate: CustomerAggregate) -> list[TransactionSchema]:
    if not aggregate.transactions:
        return []
    reference = max(t.date for t in aggregate.transactions)
    start = reference - timedelta(days=LOOKBACK_DAYS)
    return [
        t for t in aggregate.transactions
        if start <= t.date <= reference and t.transaction_type == "DEBIT"
    ]


def _months_active(txns: list[TransactionSchema]) -> Decimal:
    if not txns:
        return Decimal("1")
    months = {f"{t.date.year}-{t.date.month:02d}" for t in txns}
    return Decimal(max(len(months), 1))


def _score_from_spend_and_frequency(
    total_spend: Decimal,
    monthly_income: Decimal,
    frequency_per_month: Decimal,
    spend_weight: Decimal = Decimal("0.60"),
) -> Decimal:
    """Explainable 0–100 score: spend ratio vs income + transaction frequency."""
    if monthly_income <= 0:
        spend_component = Decimal("0")
    else:
        spend_ratio = total_spend / (monthly_income * Decimal("12"))
        spend_component = min(Decimal("100"), spend_ratio * Decimal("200"))

    freq_component = min(Decimal("100"), frequency_per_month * Decimal("8"))
    composite = spend_component * spend_weight + freq_component * (Decimal("1") - spend_weight)
    return composite.quantize(SCORE, ROUND_HALF_UP)


class BaseBehaviourAnalyzer(ABC):
    """Base class for category-specific behaviour analyzers."""

    category: str

    def __init__(self, config: MerchantCategoryConfig) -> None:
        self._config = config

    def _filter_transactions(self, aggregate: CustomerAggregate) -> list[TransactionSchema]:
        return [
            t for t in _window_debits(aggregate)
            if self._config.resolve_category(t.merchant, t.category) == self.category
        ]


class ShoppingBehaviourAnalyzer(BaseBehaviourAnalyzer):
    category = "Shopping"

    def analyze(self, aggregate: CustomerAggregate, monthly_income: Decimal) -> ShoppingBehaviourResult:
        txns = self._filter_transactions(aggregate)
        months = _months_active(txns)
        total = _money_sum(t.amount for t in txns)
        monthly_spend = (total / months).quantize(MONEY, ROUND_HALF_UP)
        frequency = (Decimal(len(txns)) / months).quantize(RATIO, ROUND_HALF_UP)
        avg_amount = (total / Decimal(len(txns))).quantize(MONEY, ROUND_HALF_UP) if txns else Decimal("0.00")

        luxury_spend = Decimal("0")
        budget_spend = Decimal("0")
        for t in txns:
            if self._config.is_luxury(t.merchant) or t.amount >= LUXURY_AMOUNT_THRESHOLD:
                luxury_spend += t.amount
            elif self._config.is_budget(t.merchant) or t.amount <= BUDGET_AMOUNT_THRESHOLD:
                budget_spend += t.amount

        luxury_ratio = (luxury_spend / total * Decimal("100")).quantize(RATIO, ROUND_HALF_UP) if total else Decimal("0")
        budget_ratio = (budget_spend / total * Decimal("100")).quantize(RATIO, ROUND_HALF_UP) if total else Decimal("0")

        merchants = [t.merchant for t in txns if t.merchant]
        top_merchant = Counter(merchants).most_common(1)[0][0] if merchants else None

        day_counts = Counter(DAY_NAMES[t.date.weekday()] for t in txns)
        preferred_day = day_counts.most_common(1)[0][0] if day_counts else None

        return ShoppingBehaviourResult(
            shopping_score=_score_from_spend_and_frequency(total, monthly_income, frequency),
            monthly_shopping_spend=monthly_spend,
            shopping_frequency=frequency,
            average_shopping_amount=avg_amount,
            luxury_shopping_ratio=luxury_ratio,
            budget_shopping_ratio=budget_ratio,
            top_shopping_merchant=top_merchant,
            preferred_shopping_day=preferred_day,
        )


class FoodBehaviourAnalyzer(BaseBehaviourAnalyzer):
    category = "Food"

    def analyze(self, aggregate: CustomerAggregate, monthly_income: Decimal) -> FoodBehaviourResult:
        txns = self._filter_transactions(aggregate)
        months = _months_active(txns)
        total = _money_sum(t.amount for t in txns)

        restaurant = _money_sum(t.amount for t in txns if t.merchant in RESTAURANT_MERCHANTS)
        delivery = _money_sum(t.amount for t in txns if t.merchant in DELIVERY_MERCHANTS)
        weekend = _money_sum(t.amount for t in txns if t.date.weekday() >= 5)

        merchants = [t.merchant for t in txns if t.merchant]
        favourite = Counter(merchants).most_common(1)[0][0] if merchants else None
        frequency = (Decimal(len(txns)) / months).quantize(RATIO, ROUND_HALF_UP)

        return FoodBehaviourResult(
            food_score=_score_from_spend_and_frequency(total, monthly_income, frequency),
            restaurant_spend=restaurant.quantize(MONEY, ROUND_HALF_UP),
            food_delivery_spend=delivery.quantize(MONEY, ROUND_HALF_UP),
            dining_frequency=frequency,
            weekend_food_spend=weekend.quantize(MONEY, ROUND_HALF_UP),
            favourite_food_merchant=favourite,
        )


class TravelBehaviourAnalyzer(BaseBehaviourAnalyzer):
    category = "Travel"

    def analyze(self, aggregate: CustomerAggregate, monthly_income: Decimal) -> TravelBehaviourResult:
        txns = self._filter_transactions(aggregate)
        months = _months_active(txns)
        total = _money_sum(t.amount for t in txns)
        frequency = (Decimal(len(txns)) / months).quantize(RATIO, ROUND_HALF_UP)

        transport_spend = _money_sum(t.amount for t in txns if t.merchant in TRANSPORT_MERCHANTS)
        rail_air_spend = _money_sum(t.amount for t in txns if t.merchant in RAIL_AIR_MERCHANTS)
        if rail_air_spend > transport_spend:
            preference = "Rail/Air"
        elif transport_spend > 0:
            preference = "Ride Hailing"
        else:
            preference = None

        merchants = [t.merchant for t in txns if t.merchant]
        top = Counter(merchants).most_common(1)[0][0] if merchants else None

        return TravelBehaviourResult(
            travel_score=_score_from_spend_and_frequency(total, monthly_income, frequency),
            travel_frequency=frequency,
            travel_spend=total.quantize(MONEY, ROUND_HALF_UP),
            transport_preference=preference,
            top_travel_merchant=top,
        )


class HealthcareBehaviourAnalyzer(BaseBehaviourAnalyzer):
    category = "Healthcare"

    def analyze(self, aggregate: CustomerAggregate, monthly_income: Decimal) -> HealthcareBehaviourResult:
        txns = self._filter_transactions(aggregate)
        months = _months_active(txns)
        total = _money_sum(t.amount for t in txns)
        pharmacy = _money_sum(t.amount for t in txns if t.merchant in PHARMACY_MERCHANTS)
        hospital = _money_sum(t.amount for t in txns if t.merchant in HOSPITAL_MERCHANTS)
        frequency = (Decimal(len(txns)) / months).quantize(RATIO, ROUND_HALF_UP)

        return HealthcareBehaviourResult(
            healthcare_score=_score_from_spend_and_frequency(total, monthly_income, frequency),
            medical_spend=total.quantize(MONEY, ROUND_HALF_UP),
            pharmacy_spend=pharmacy.quantize(MONEY, ROUND_HALF_UP),
            hospital_spend=hospital.quantize(MONEY, ROUND_HALF_UP),
        )


class EntertainmentBehaviourAnalyzer(BaseBehaviourAnalyzer):
    category = "Entertainment"

    def analyze(self, aggregate: CustomerAggregate, monthly_income: Decimal) -> EntertainmentBehaviourResult:
        txns = self._filter_transactions(aggregate)
        months = _months_active(txns)
        total = _money_sum(t.amount for t in txns)
        ott = _money_sum(t.amount for t in txns if t.merchant in OTT_MERCHANTS)
        movie = _money_sum(t.amount for t in txns if t.merchant in MOVIE_MERCHANTS)
        music = _money_sum(t.amount for t in txns if t.merchant in MUSIC_MERCHANTS)
        gaming = _money_sum(
            t.amount for t in txns
            if t.merchant and "game" in t.merchant.lower()
        )
        frequency = (Decimal(len(txns)) / months).quantize(RATIO, ROUND_HALF_UP)

        return EntertainmentBehaviourResult(
            entertainment_score=_score_from_spend_and_frequency(total, monthly_income, frequency),
            ott_spend=ott.quantize(MONEY, ROUND_HALF_UP),
            movie_spend=movie.quantize(MONEY, ROUND_HALF_UP),
            music_subscription_spend=music.quantize(MONEY, ROUND_HALF_UP),
            gaming_spend=gaming.quantize(MONEY, ROUND_HALF_UP),
        )


class InvestmentBehaviourAnalyzer(BaseBehaviourAnalyzer):
    category = "Investment"

    def analyze(self, aggregate: CustomerAggregate, monthly_income: Decimal) -> InvestmentBehaviourResult:
        txns = self._filter_transactions(aggregate)
        investment_txns = [
            t for t in txns
            if self._config.resolve_category(t.merchant, t.category) == "Investment"
            or t.category == "Investment"
        ]
        months = _months_active(investment_txns)
        total = _money_sum(t.amount for t in investment_txns)
        frequency = (Decimal(len(investment_txns)) / months).quantize(RATIO, ROUND_HALF_UP)

        mf_count = sum(1 for t in investment_txns if t.merchant in MF_MERCHANTS)
        stock_count = sum(1 for t in investment_txns if t.merchant in STOCK_MERCHANTS)

        monthly_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for t in investment_txns:
            key = f"{t.date.year}-{t.date.month:02d}"
            monthly_totals[key] += t.amount

        consistency = _consistency_score(list(monthly_totals.values()))
        sip_freq = frequency if frequency <= Decimal("4") else Decimal("4")

        return InvestmentBehaviourResult(
            investment_score=_score_from_spend_and_frequency(total, monthly_income, frequency),
            investment_spend=total.quantize(MONEY, ROUND_HALF_UP),
            investment_frequency=frequency,
            sip_frequency=sip_freq,
            mutual_fund_transactions=mf_count,
            stock_transactions=stock_count,
            investment_consistency=consistency,
        )


class FuelBehaviourAnalyzer(BaseBehaviourAnalyzer):
    category = "Fuel"

    def analyze(self, aggregate: CustomerAggregate, monthly_income: Decimal) -> FuelBehaviourResult:
        txns = self._filter_transactions(aggregate)
        months = _months_active(txns)
        total = _money_sum(t.amount for t in txns)
        frequency = (Decimal(len(txns)) / months).quantize(RATIO, ROUND_HALF_UP)

        return FuelBehaviourResult(
            fuel_score=_score_from_spend_and_frequency(total, monthly_income, frequency),
            fuel_spend=total.quantize(MONEY, ROUND_HALF_UP),
            fuel_frequency=frequency,
        )


class EducationBehaviourAnalyzer(BaseBehaviourAnalyzer):
    category = "Education"

    def analyze(self, aggregate: CustomerAggregate, monthly_income: Decimal) -> EducationBehaviourResult:
        txns = self._filter_transactions(aggregate)
        months = _months_active(txns)
        total = _money_sum(t.amount for t in txns)
        frequency = (Decimal(len(txns)) / months).quantize(RATIO, ROUND_HALF_UP)

        return EducationBehaviourResult(
            education_score=_score_from_spend_and_frequency(total, monthly_income, frequency),
            learning_spend=total.quantize(MONEY, ROUND_HALF_UP),
            course_frequency=frequency,
        )


def _consistency_score(monthly_values: list[Decimal]) -> Decimal:
    if len(monthly_values) < 2:
        return Decimal("100.00")
    float_vals = [float(v) for v in monthly_values]
    avg = sum(float_vals) / len(float_vals)
    if avg == 0:
        return Decimal("100.00")
    cv = pstdev(float_vals) / avg
    score = max(0.0, round(100.0 - cv * 100.0, 2))
    return Decimal(str(score)).quantize(SCORE, ROUND_HALF_UP)


class LifestyleInferencer:
    """Derives multiple lifestyle tags from behaviour scores and ratios."""

    @staticmethod
    def infer(
        shopping: ShoppingBehaviourResult,
        food: FoodBehaviourResult,
        travel: TravelBehaviourResult,
        healthcare: HealthcareBehaviourResult,
        investment: InvestmentBehaviourResult,
        fuel: FuelBehaviourResult,
        education: EducationBehaviourResult,
        entertainment: EntertainmentBehaviourResult,
        digital_payment_ratio: Decimal,
    ) -> list[str]:
        tags: list[str] = []

        if digital_payment_ratio >= Decimal("80") and shopping.shopping_score >= Decimal("60"):
            tags.append("Digital Shopper")
        if travel.travel_score >= Decimal("70"):
            tags.append("Frequent Traveller")
        if investment.investment_score >= Decimal("60"):
            tags.append("Investor")
        if food.food_score >= Decimal("70"):
            tags.append("Food Enthusiast")
        if healthcare.healthcare_score >= Decimal("50"):
            tags.append("Health Conscious")
        if shopping.budget_shopping_ratio >= Decimal("60"):
            tags.append("Budget Conscious")
        if shopping.luxury_shopping_ratio >= Decimal("40"):
            tags.append("Luxury Lifestyle")
        if education.education_score >= Decimal("40"):
            tags.append("Learner")
        if fuel.fuel_score >= Decimal("50") and shopping.shopping_score >= Decimal("40"):
            tags.append("Family Oriented")
        if entertainment.entertainment_score >= Decimal("55"):
            tags.append("Entertainment Seeker")

        return tags


class InterestProfiler:
    """Ranks customer interests by category spend share."""

    @staticmethod
    def profile(category_spends: dict[str, Decimal]) -> tuple[str | None, str | None, str | None]:
        total = sum(category_spends.values())
        if total <= 0:
            return None, None, None

        ranked = sorted(category_spends.items(), key=lambda x: x[1], reverse=True)
        top = ranked[0][0] if len(ranked) > 0 else None
        second = ranked[1][0] if len(ranked) > 1 and ranked[1][1] > 0 else None
        third = ranked[2][0] if len(ranked) > 2 and ranked[2][1] > 0 else None
        return top, second, third


class BehaviourAnalyticsEngine:
    """
    Orchestrates all behaviour analyzers, lifestyle inference, and interest profiling.

    Input: CustomerAggregate + Financial + Transaction analytics + Customer360 profile
    Output: BehaviourProfile
    """

    def __init__(self, config: MerchantCategoryConfig | None = None) -> None:
        self._config = config or MerchantCategoryConfig()
        self._shopping = ShoppingBehaviourAnalyzer(self._config)
        self._food = FoodBehaviourAnalyzer(self._config)
        self._travel = TravelBehaviourAnalyzer(self._config)
        self._healthcare = HealthcareBehaviourAnalyzer(self._config)
        self._entertainment = EntertainmentBehaviourAnalyzer(self._config)
        self._investment = InvestmentBehaviourAnalyzer(self._config)
        self._fuel = FuelBehaviourAnalyzer(self._config)
        self._education = EducationBehaviourAnalyzer(self._config)

    def calculate(self, data: BehaviourAnalyticsInput) -> BehaviourProfile:
        aggregate = data.aggregate
        monthly_income = data.financial.monthly_income
        customer_id = aggregate.customer.customer_id

        shopping = self._shopping.analyze(aggregate, monthly_income)
        food = self._food.analyze(aggregate, monthly_income)
        travel = self._travel.analyze(aggregate, monthly_income)
        healthcare = self._healthcare.analyze(aggregate, monthly_income)
        entertainment = self._entertainment.analyze(aggregate, monthly_income)
        investment = self._investment.analyze(aggregate, monthly_income)
        fuel = self._fuel.analyze(aggregate, monthly_income)
        education = self._education.analyze(aggregate, monthly_income)

        category_spends = {
            "Shopping": shopping.monthly_shopping_spend,
            "Food": food.restaurant_spend + food.food_delivery_spend,
            "Travel": travel.travel_spend,
            "Healthcare": healthcare.medical_spend,
            "Entertainment": entertainment.ott_spend + entertainment.movie_spend + entertainment.music_subscription_spend,
            "Investment": investment.investment_spend,
            "Fuel": fuel.fuel_spend,
            "Education": education.learning_spend,
        }

        top, second, third = InterestProfiler.profile(category_spends)
        lifestyle_tags = LifestyleInferencer.infer(
            shopping, food, travel, healthcare, investment, fuel, education, entertainment,
            data.transaction.digital_payment_ratio,
        )

        profile = BehaviourProfile(
            customer_id=customer_id,
            shopping_score=shopping.shopping_score,
            travel_score=travel.travel_score,
            food_score=food.food_score,
            healthcare_score=healthcare.healthcare_score,
            investment_score=investment.investment_score,
            fuel_score=fuel.fuel_score,
            education_score=education.education_score,
            entertainment_score=entertainment.entertainment_score,
            top_interest=top,
            secondary_interest=second,
            third_interest=third,
            lifestyle_tags=lifestyle_tags,
            shopping=shopping,
            food=food,
            travel=travel,
            healthcare=healthcare,
            entertainment=entertainment,
            investment=investment,
            fuel=fuel,
            education=education,
        )

        logger.info(
            "Behaviour analytics computed for customer_id=%s tags=%s top_interest=%s",
            customer_id,
            lifestyle_tags,
            top,
        )
        return profile
