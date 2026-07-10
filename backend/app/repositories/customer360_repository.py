"""Repository for Customer360 profile persistence."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.db.codec import encode_document
from app.db.mongo import MongoDatabase
from app.models.customer360_profile import Customer360Profile
from app.utils.exceptions import ProfileNotFoundError, UnifiedProfileNotFoundError


class Customer360Repository:
    """Data access layer for customer_360_profile collection."""

    def __init__(self, db: MongoDatabase) -> None:
        self._db = db
        self._profile_cache = {}

    def create_profile(self, profile: Customer360Profile) -> Customer360Profile:
        doc = profile.to_doc()
        self._db.customer_360_profile.replace_one(
            {"customer_id": doc["customer_id"]},
            doc,
            upsert=True,
        )
        return profile

    def update_profile(self, profile: Customer360Profile) -> Customer360Profile:
        doc = profile.to_doc()
        self._db.customer_360_profile.replace_one(
            {"profile_id": doc["profile_id"]},
            doc,
            upsert=True,
        )
        return profile

    def get_profile_by_customer_id(self, customer_id: UUID) -> Customer360Profile | None:
        doc = self._db.customer_360_profile.find_one({"customer_id": str(customer_id)})
        return Customer360Profile.from_doc(doc)

    def get_profile_by_customer_id_or_raise(self, customer_id: UUID) -> Customer360Profile:
        profile = self.get_profile_by_customer_id(customer_id)
        if profile is None:
            raise ProfileNotFoundError(customer_id)
        return profile

    def get_all_profiles(self) -> list[Customer360Profile]:
        docs = self._db.customer_360_profile.find()
        return [Customer360Profile.from_doc(d) for d in docs if d]

    def count_profiles(self) -> int:
        return self._db.customer_360_profile.count_documents({})

    def get_profile_by_profile_id(self, profile_id: UUID) -> Customer360Profile | None:
        key = str(profile_id)
        if key in self._profile_cache:
            return self._profile_cache[key]
        doc = self._db.customer_360_profile.find_one({"profile_id": key})
        profile = Customer360Profile.from_doc(doc) if doc else None
        if profile:
            self._profile_cache[key] = profile
        return profile

    def apply_behaviour_summary(
        self,
        profile_id: UUID,
        *,
        financial_health_score: Decimal,
        repayment_behaviour_score: Decimal,
        digital_engagement_score: Decimal,
        commit: bool = True,
    ) -> Customer360Profile:
        profile = self.get_profile_by_profile_id(profile_id)
        if profile is None:
            raise UnifiedProfileNotFoundError(profile_id)
        profile.financial_health_score = financial_health_score
        profile.repayment_behaviour_score = repayment_behaviour_score
        profile.digital_engagement_score = digital_engagement_score
        profile.last_updated = datetime.utcnow()
        self.update_profile(profile)
        return profile
