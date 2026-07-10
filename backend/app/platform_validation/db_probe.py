"""Low-level MongoDB probe helpers for validation (read-only)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.db.mongo import MongoDatabase


class DatabaseProbe:
    """Read-only probes against MongoDB collections."""

    def __init__(self, db: MongoDatabase) -> None:
        self._db = db

    def table_exists(self, collection_name: str) -> bool:
        return collection_name in self._db._db.list_collection_names()

    def count_rows(self, collection_name: str) -> int:
        return self._db._db[collection_name].count_documents({})

    def count_distinct(self, collection_name: str, field: str) -> int:
        return len(self._db._db[collection_name].distinct(field))

    def scalar(self, sql: str, params: dict[str, Any] | None = None) -> Any:
        """Legacy SQL probe adapter — maps common validation queries to MongoDB."""
        return self._run_legacy_query(sql, params or {})

    def fetchall(self, sql: str, params: dict[str, Any] | None = None) -> list[Any]:
        raise NotImplementedError("fetchall not supported for MongoDB probes")

    def primary_key_columns(self, collection_name: str) -> list[str]:
        pk_map = {
            "customers": "customer_id",
            "accounts": "account_id",
            "transactions": "transaction_id",
            "products": "product_id",
            "customer_products": "customer_product_id",
            "consent": "consent_id",
            "customer_360_profile": "profile_id",
            "feature_store": "feature_id",
            "external_leads": "lead_id",
            "external_customer_profile": "profile_id",
            "lead_feature_store": "feature_id",
            "training_dataset": "record_id",
            "explainability_reports": "report_id",
        }
        return [pk_map.get(collection_name, "_id")]

    def index_count(self, collection_name: str) -> int:
        return len(list(self._db._db[collection_name].list_indexes()))

    def constraint_count(self, collection_name: str) -> int:
        return self.index_count(collection_name)

    def null_count(self, collection_name: str, column: str) -> int:
        return self._db._db[collection_name].count_documents({column: None})

    def duplicate_pk_count(self, collection_name: str, pk_column: str) -> int:
        pipeline = [
            {"$group": {"_id": f"${pk_column}", "cnt": {"$sum": 1}}},
            {"$match": {"cnt": {"$gt": 1}}},
            {"$count": "duplicates"},
        ]
        result = list(self._db._db[collection_name].aggregate(pipeline))
        return result[0]["duplicates"] if result else 0

    def sample_customer_id(self) -> UUID | None:
        doc = self._db.customers.find_one({}, {"customer_id": 1})
        return UUID(doc["customer_id"]) if doc else None

    def sample_profile_id(self) -> UUID | None:
        doc = self._db.customer_360_profile.find_one({}, {"profile_id": 1})
        return UUID(doc["profile_id"]) if doc else None

    def sample_lead_id(self) -> UUID | None:
        doc = self._db.external_leads.find_one({}, {"lead_id": 1})
        return UUID(doc["lead_id"]) if doc else None

    def sample_external_profile_id(self) -> UUID | None:
        doc = self._db.external_customer_profile.find_one({}, {"profile_id": 1})
        return UUID(doc["profile_id"]) if doc else None

    def sample_training_profile_id(self, profile_type: str) -> UUID | None:
        doc = self._db.training_dataset.find_one(
            {"profile_type": profile_type}, {"profile_id": 1}
        )
        return UUID(doc["profile_id"]) if doc else None

    def _run_legacy_query(self, sql: str, params: dict[str, Any]) -> Any:
        normalized = " ".join(sql.lower().split())

        if "orphan accounts" in normalized or (
            "accounts a" in normalized and "customers c" in normalized
        ):
            account_ids = {d["customer_id"] for d in self._db.accounts.find({}, {"customer_id": 1})}
            customer_ids = {d["customer_id"] for d in self._db.customers.find({}, {"customer_id": 1})}
            return len(account_ids - customer_ids)

        if "orphan transactions" in normalized or (
            "transactions t" in normalized and "accounts a" in normalized
        ):
            txn_accounts = {d["account_id"] for d in self._db.transactions.find({}, {"account_id": 1})}
            account_ids = {d["account_id"] for d in self._db.accounts.find({}, {"account_id": 1})}
            return len(txn_accounts - account_ids)

        if "customer_products" in normalized and "customers c" in normalized:
            cp_customers = {d["customer_id"] for d in self._db.customer_products.find({}, {"customer_id": 1})}
            customer_ids = {d["customer_id"] for d in self._db.customers.find({}, {"customer_id": 1})}
            return len(cp_customers - customer_ids)

        if "customer_products" in normalized and "products p" in normalized:
            cp_products = {d["product_id"] for d in self._db.customer_products.find({}, {"product_id": 1})}
            product_ids = {d["product_id"] for d in self._db.products.find({}, {"product_id": 1})}
            return len(cp_products - product_ids)

        if "consent" in normalized and "customers c" in normalized:
            consent_customers = {d["customer_id"] for d in self._db.consent.find({}, {"customer_id": 1})}
            customer_ids = {d["customer_id"] for d in self._db.customers.find({}, {"customer_id": 1})}
            return len(consent_customers - customer_ids)

        if "customer_360_profile" in normalized and "customers c" in normalized:
            profile_customers = {
                d["customer_id"] for d in self._db.customer_360_profile.find({}, {"customer_id": 1})
            }
            customer_ids = {d["customer_id"] for d in self._db.customers.find({}, {"customer_id": 1})}
            return len(profile_customers - customer_ids)

        if "feature_store" in normalized and "customers c" in normalized:
            feature_customers = {d["customer_id"] for d in self._db.feature_store.find({}, {"customer_id": 1})}
            customer_ids = {d["customer_id"] for d in self._db.customers.find({}, {"customer_id": 1})}
            return len(feature_customers - customer_ids)

        if "external_customer_profile" in normalized and "external_leads" in normalized:
            profile_leads = {d["lead_id"] for d in self._db.external_customer_profile.find({}, {"lead_id": 1})}
            lead_ids = {d["lead_id"] for d in self._db.external_leads.find({}, {"lead_id": 1})}
            return len(profile_leads - lead_ids)

        if "lead_feature_store" in normalized and "external_leads" in normalized:
            feature_leads = {d["lead_id"] for d in self._db.lead_feature_store.find({}, {"lead_id": 1})}
            lead_ids = {d["lead_id"] for d in self._db.external_leads.find({}, {"lead_id": 1})}
            return len(feature_leads - lead_ids)

        if "select count(*)" in normalized and "from customers" in normalized:
            return self.count_rows("customers")
        if "select count(*)" in normalized and "from customer_360_profile" in normalized:
            return self.count_rows("customer_360_profile")
        if "select count(distinct customer_id)" in normalized and "feature_store" in normalized:
            if "pipeline_completed" in normalized or "internal_pipeline" in normalized:
                return self._db.feature_store.count_documents(
                    {
                        "source_module": "internal_pipeline",
                        "feature_name": "pipeline_completed",
                    }
                )
            return self.count_distinct("feature_store", "customer_id")
        if "select count(*)" in normalized and "from feature_store" in normalized:
            return self.count_rows("feature_store")
        if "select count(*)" in normalized and "from external_leads" in normalized:
            if "analytics_ready" in normalized:
                return self._db.external_leads.count_documents({"lead_status": "ANALYTICS_READY"})
            if "intelligence_validated" in normalized:
                return self._db.external_leads.count_documents(
                    {"lead_status": "INTELLIGENCE_VALIDATED"}
                )
            return self.count_rows("external_leads")
        if "select count(distinct lead_id)" in normalized:
            return self.count_distinct("lead_feature_store", "lead_id")
        if "select count(*)" in normalized and "training_dataset" in normalized:
            if "profile_type = 'internal'" in normalized:
                return self._db.training_dataset.count_documents({"profile_type": "Internal"})
            if "profile_type = 'external'" in normalized:
                return self._db.training_dataset.count_documents({"profile_type": "External"})
            if "target_repayment_capacity not in" in normalized:
                valid = {"Very High", "High", "Medium", "Low"}
                return self._db.training_dataset.count_documents(
                    {"target_repayment_capacity": {"$nin": list(valid)}}
                )
            if "group by profile_id" in normalized:
                pipeline = [
                    {"$group": {"_id": {"profile_id": "$profile_id", "profile_type": "$profile_type"}, "cnt": {"$sum": 1}}},
                    {"$match": {"cnt": {"$gt": 1}}},
                    {"$count": "duplicates"},
                ]
                result = list(self._db.training_dataset.aggregate(pipeline))
                return result[0]["duplicates"] if result else 0
            return self.count_rows("training_dataset")
        if "select count(*)" in normalized and "from accounts" in normalized:
            if "balance < 0" in normalized:
                return self._db.accounts.count_documents({"balance": {"$lt": "0"}})
            return self.count_rows("accounts")
        if "age < 18" in normalized or "age > 100" in normalized:
            return self._db.customers.count_documents(
                {"$or": [{"age": {"$lt": 18}}, {"age": {"$gt": 100}}]}
            )
        if "phone_number" in normalized and "group by" in normalized:
            return self._count_duplicate_field("customers", "phone_number")
        if "external_leads" in normalized and "phone_number" in normalized and "group by" in normalized:
            return self._count_duplicate_field("external_leads", "phone_number")
        if "annual_income" in normalized and "<= 0" in normalized:
            return self._db.customers.count_documents({"annual_income": {"$lte": "0"}})
        if "emi_burden" in normalized and "> 100" in normalized:
            return self._db.customer_360_profile.count_documents({"emi_burden": {"$gt": "100"}})
        if "debt_ratio" in normalized and "> 100" in normalized:
            return self._db.customer_360_profile.count_documents({"debt_ratio": {"$gt": "100"}})
        if "customer_id" in params:
            cid = params["cid"] if "cid" in params else params.get("customer_id", params.get("lid"))
            if "customer_360_profile" in normalized and "where customer_id" in normalized:
                return self._db.customer_360_profile.count_documents({"customer_id": str(cid)})
            if "feature_store" in normalized and "pipeline_completed" in normalized:
                return self._db.feature_store.count_documents(
                    {
                        "customer_id": str(cid),
                        "source_module": "internal_pipeline",
                        "feature_name": "pipeline_completed",
                    }
                )
            if "training_dataset" in normalized and "customer_360_profile" in normalized:
                profile = self._db.customer_360_profile.find_one({"customer_id": str(cid)})
                if not profile:
                    return 0
                return self._db.training_dataset.count_documents(
                    {"profile_id": profile["profile_id"], "profile_type": "Internal"}
                )
            if "external_leads" in normalized and "lead_id" in normalized:
                return self._db.external_leads.count_documents({"lead_id": str(cid)})
            if "external_customer_profile" in normalized:
                return self._db.external_customer_profile.count_documents({"lead_id": str(cid)})
            if "lead_feature_store" in normalized and "external_lead_analytics" in normalized:
                return self._db.lead_feature_store.count_documents(
                    {"lead_id": str(cid), "source_module": "external_lead_analytics"}
                )
            if "lead_feature_store" in normalized and "distinct feature_name" in normalized:
                return len(
                    self._db.lead_feature_store.distinct("feature_name", {"lead_id": str(cid)})
                )
            if "training_dataset" in normalized and "external_customer_profile" in normalized:
                profile = self._db.external_customer_profile.find_one({"lead_id": str(cid)})
                if not profile:
                    return 0
                return self._db.training_dataset.count_documents(
                    {"profile_id": profile["profile_id"], "profile_type": "External"}
                )

        if "profiles_without_features" in normalized or (
            "customer_360_profile p" in normalized and "feature_store" in normalized
        ):
            profile_customers = {
                d["customer_id"] for d in self._db.customer_360_profile.find({}, {"customer_id": 1})
            }
            feature_customers = {d["customer_id"] for d in self._db.feature_store.find({}, {"customer_id": 1})}
            return len(profile_customers - feature_customers)

        if "profiles_without_lead_features" in normalized or (
            "external_customer_profile p" in normalized and "lead_feature_store" in normalized
        ):
            profile_leads = {d["lead_id"] for d in self._db.external_customer_profile.find({}, {"lead_id": 1})}
            feature_leads = {d["lead_id"] for d in self._db.lead_feature_store.find({}, {"lead_id": 1})}
            return len(profile_leads - feature_leads)

        if "orphan_internal" in normalized or (
            "training_dataset t" in normalized and "customer_360_profile p" in normalized
        ):
            count = 0
            for record in self._db.training_dataset.find({"profile_type": "Internal"}):
                if not self._db.customer_360_profile.find_one({"profile_id": record["profile_id"]}):
                    count += 1
            return count

        if "orphan_external" in normalized or (
            "training_dataset t" in normalized and "external_customer_profile p" in normalized
        ):
            count = 0
            for record in self._db.training_dataset.find({"profile_type": "External"}):
                if not self._db.external_customer_profile.find_one({"profile_id": record["profile_id"]}):
                    count += 1
            return count

        if "select profile_id" in normalized:
            doc = self._db.customer_360_profile.find_one({"customer_id": str(params.get("cid"))})
            return doc["profile_id"] if doc else None

        if "select count(distinct customer_id)" in normalized and "behaviour_summary" in normalized:
            return self._db.feature_store.count_documents({"source_module": "behaviour_summary"})

        if "select count(distinct lead_id)" in normalized and "behaviour_summary" in normalized:
            return self._db.lead_feature_store.count_documents({"source_module": "behaviour_summary"})

        if "select count(distinct customer_id)" in normalized and "source_module" in normalized:
            module = params.get("source_module")
            if module:
                return len(
                    self._db.feature_store.distinct(
                        "customer_id", {"source_module": module}
                    )
                )

        if "monthly_expense is not null" in normalized:
            return self._db.customer_360_profile.count_documents(
                {"monthly_expense": {"$ne": None}, "cash_flow_score": {"$ne": None}}
            )

        return 0

    def _count_duplicate_field(self, collection: str, field: str) -> int:
        pipeline = [
            {"$group": {"_id": f"${field}", "cnt": {"$sum": 1}}},
            {"$match": {"cnt": {"$gt": 1}}},
            {"$count": "duplicates"},
        ]
        result = list(self._db._db[collection].aggregate(pipeline))
        return result[0]["duplicates"] if result else 0
