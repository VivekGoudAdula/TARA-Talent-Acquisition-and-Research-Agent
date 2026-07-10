"""Orchestrates ML training dataset build, validation, persistence, and export."""

from uuid import UUID

from app.ml.dataset_builder.dataset_exporter import DatasetExporter
from app.ml.dataset_builder.dataset_generator import DatasetGenerator
from app.ml.dataset_builder.dataset_validator import DatasetValidator
from app.repositories.customer360_repository import Customer360Repository
from app.repositories.external_lead_repository import ExternalLeadRepository
from app.repositories.external_profile_repository import ExternalProfileRepository
from app.repositories.feature_store_repository import FeatureStoreRepository
from app.repositories.lead_feature_store_repository import LeadFeatureStoreRepository
from app.repositories.training_dataset_repository import TrainingDatasetRepository
from app.schemas.ml_dataset import (
    MLDatasetBuildResponse,
    MLDatasetPreviewResponse,
    MLDatasetRecordResponse,
    MLDatasetStatsResponse,
)
from app.utils.exceptions import MLDatasetNotFoundError
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class DatasetService:
    """
    Enterprise ML Dataset Builder.

    Reads intelligence-layer outputs and produces a unified training_dataset.
    Does not train or evaluate models.
    """

    def __init__(
        self,
        customer360_repository: Customer360Repository,
        external_profile_repository: ExternalProfileRepository,
        external_lead_repository: ExternalLeadRepository,
        feature_store_repository: FeatureStoreRepository,
        lead_feature_store_repository: LeadFeatureStoreRepository,
        training_dataset_repository: TrainingDatasetRepository,
        generator: DatasetGenerator | None = None,
        validator: DatasetValidator | None = None,
        exporter: DatasetExporter | None = None,
    ) -> None:
        self._internal_repo = customer360_repository
        self._external_repo = external_profile_repository
        self._lead_repo = external_lead_repository
        self._feature_repo = feature_store_repository
        self._lead_feature_repo = lead_feature_store_repository
        self._dataset_repo = training_dataset_repository
        self._generator = generator or DatasetGenerator()
        self._validator = validator or DatasetValidator()
        self._exporter = exporter or DatasetExporter()

    def build_dataset(
        self, limit_internal: int | None = None, limit_external: int | None = None
    ) -> MLDatasetBuildResponse:
        internal_profiles = self._internal_repo.get_all_profiles()
        if limit_internal is not None:
            internal_profiles = internal_profiles[: max(0, limit_internal)]
        external_profiles = self._external_repo.get_all_profiles()
        if limit_external is not None:
            external_profiles = external_profiles[: max(0, limit_external)]

        internal_feature_maps = self._load_internal_feature_maps(internal_profiles)
        external_feature_maps = self._load_external_feature_maps(external_profiles)
        leads = self._load_leads(external_profiles)

        internal_rows = self._generator.build_internal_rows(
            internal_profiles, internal_feature_maps
        )
        external_rows = self._generator.build_external_rows(
            external_profiles, leads, external_feature_maps
        )

        combined = self._generator.assign_targets(internal_rows + external_rows)
        cleaned, report = self._validator.validate_and_clean(combined)
        df = self._validator.rows_to_dataframe(cleaned)

        export_info = self._exporter.export(df)
        persisted = self._dataset_repo.replace_all(cleaned)

        return MLDatasetBuildResponse(
            message="ML training dataset built successfully",
            records_persisted=persisted,
            internal_records=sum(1 for r in cleaned if r.profile_type == "Internal"),
            external_records=sum(1 for r in cleaned if r.profile_type == "External"),
            duplicates_removed=report.duplicates_removed,
            csv_path=export_info["csv_path"],
            parquet_path=export_info["parquet_path"],
            target_distribution=self._validator.compute_target_distribution(df),
        )

    def preview_dataset(self, limit: int = 50) -> MLDatasetPreviewResponse:
        records = self._dataset_repo.get_preview(limit)
        if not records:
            raise MLDatasetNotFoundError()
        return MLDatasetPreviewResponse(
            total_records=self._dataset_repo.count_all(),
            preview_limit=limit,
            records=[MLDatasetRecordResponse.model_validate(r) for r in records],
        )

    def dataset_stats(self) -> MLDatasetStatsResponse:
        records = self._dataset_repo.get_all()
        if not records:
            raise MLDatasetNotFoundError()

        rows = [self._record_to_row(r) for r in records]
        df = self._validator.rows_to_dataframe(rows)

        feature_columns = [
            c
            for c in df.columns
            if c
            not in (
                "record_id",
                "profile_id",
                "created_at",
                "target_repayment_capacity",
            )
        ]

        return MLDatasetStatsResponse(
            total_records=len(records),
            internal_records=int((df["profile_type"] == "Internal").sum()),
            external_records=int((df["profile_type"] == "External").sum()),
            feature_count=len(feature_columns),
            missing_values=self._validator.compute_missing_counts(df),
            target_distribution=self._validator.compute_target_distribution(df),
            export_paths={
                "csv": str(self._exporter.csv_path),
                "parquet": str(self._exporter.parquet_path),
            },
        )

    def _load_internal_feature_maps(self, profiles) -> dict[UUID, dict]:
        from app.models.feature_store import FeatureStoreEntry
        import collections
        customer_ids = [str(p.customer_id) for p in profiles]
        features_by_customer = collections.defaultdict(list)
        if customer_ids:
            for i in range(0, len(customer_ids), 500):
                batch_cids = customer_ids[i:i+500]
                docs = self._feature_repo._db.feature_store.find({"customer_id": {"$in": batch_cids}})
                for doc in docs:
                    if doc:
                        features_by_customer[doc["customer_id"]].append(FeatureStoreEntry.from_doc(doc))
        
        maps: dict[UUID, dict] = {}
        for profile in profiles:
            entries = features_by_customer.get(str(profile.customer_id), [])
            maps[profile.customer_id] = self._feature_repo.features_to_dict(entries)
        return maps

    def _load_external_feature_maps(self, profiles) -> dict[UUID, dict]:
        from app.models.lead_feature_store import LeadFeatureStoreEntry
        import collections
        lead_ids = [str(p.lead_id) for p in profiles]
        features_by_lead = collections.defaultdict(list)
        if lead_ids:
            for i in range(0, len(lead_ids), 500):
                batch_lids = lead_ids[i:i+500]
                docs = self._lead_feature_repo._db.lead_feature_store.find({"lead_id": {"$in": batch_lids}})
                for doc in docs:
                    if doc:
                        features_by_lead[doc["lead_id"]].append(LeadFeatureStoreEntry.from_doc(doc))
        
        maps: dict[UUID, dict] = {}
        for profile in profiles:
            entries = features_by_lead.get(str(profile.lead_id), [])
            maps[profile.lead_id] = self._lead_feature_repo.features_to_dict(entries)
        return maps

    def _load_leads(self, profiles) -> dict:
        from app.models.external_lead import ExternalLead
        lead_ids = [str(p.lead_id) for p in profiles]
        leads_by_id = {}
        if lead_ids:
            for i in range(0, len(lead_ids), 500):
                batch_lids = lead_ids[i:i+500]
                docs = self._lead_repo._db.external_leads.find({"lead_id": {"$in": batch_lids}})
                for doc in docs:
                    if doc:
                        leads_by_id[doc["lead_id"]] = ExternalLead.from_doc(doc)
        
        leads: dict = {}
        for profile in profiles:
            lead = leads_by_id.get(str(profile.lead_id))
            if lead is not None:
                leads[profile.lead_id] = lead
        return leads

    @staticmethod
    def _record_to_row(record):
        from app.ml.dataset_builder.dataset_generator import DatasetRow

        def _get(name):
            return getattr(record, name, None)

        return DatasetRow(
            record_id=record.record_id,
            profile_type=record.profile_type,
            profile_id=record.profile_id,
            age=_get("age"),
            income=_get("income"),
            credit_score=_get("credit_score"),
            financial_health_score=_get("financial_health_score"),
            repayment_behaviour_score=_get("repayment_behaviour_score"),
            digital_engagement_score=_get("digital_engagement_score"),
            financial_capacity_score=_get("financial_capacity_score"),
            lead_score=_get("lead_score"),
            lead_quality_score=_get("lead_quality_score"),
            lead_authenticity_score=_get("lead_authenticity_score"),
            income_confidence_score=_get("income_confidence_score"),
            relationship_score=_get("relationship_score"),
            savings_ratio=_get("savings_ratio"),
            emi_burden=_get("emi_burden"),
            cash_flow_score=_get("cash_flow_score"),
            digital_adoption_score=_get("digital_adoption_score"),
            customer_value_score=_get("customer_value_score"),
            occupation=_get("occupation"),
            employment_type=_get("employment_type"),
            city=_get("city"),
            target_repayment_capacity=_get("target_repayment_capacity"),
            created_at=_get("created_at"),
        )
