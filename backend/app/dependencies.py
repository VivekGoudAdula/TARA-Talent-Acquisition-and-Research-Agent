"""FastAPI dependency injection providers."""

from fastapi import Depends
from app.db.mongo import MongoDatabase, get_db
from app.repositories.customer360_repository import Customer360Repository
from app.services.customer360.customer360_service import Customer360Service
from app.services.customer360.customer_aggregation_service import CustomerAggregationService
from app.services.customer360.financial_profile_service import FinancialProfileService
from app.analytics.behaviour_analytics import BehaviourAnalyticsEngine
from app.analytics.financial_analytics import FinancialAnalyticsEngine
from app.analytics.transaction_analytics import TransactionAnalytics
from app.analytics.relationship_analytics import RelationshipAnalytics
from app.repositories.customer_query_repository import CustomerQueryRepository
from app.repositories.feature_store_repository import FeatureStoreRepository
from app.services.customer360.behaviour_analytics_service import BehaviourAnalyticsService
from app.analytics.digital_channel_analytics import DigitalChannelAnalytics
from app.analytics.customer_health_analytics import CustomerHealthAnalytics
from app.services.customer360.customer_health_analytics_service import CustomerHealthAnalyticsService
from app.services.customer360.digital_channel_analytics_service import DigitalChannelAnalyticsService
from app.services.customer360.relationship_analytics_service import RelationshipAnalyticsService
from app.services.customer360.transaction_analytics_service import TransactionAnalyticsService
from app.repositories.banking_repository import BankingRepository
from app.repositories.banking_import_repository import BankingImportRepository
from app.internal.banking_import_service import BankingImportService


def get_banking_repository(db: MongoDatabase = Depends(get_db)) -> BankingRepository:
    return BankingRepository(db)


def get_banking_import_repository(db: MongoDatabase = Depends(get_db)) -> BankingImportRepository:
    return BankingImportRepository(db)


def get_banking_import_service(
    repo: BankingImportRepository = Depends(get_banking_import_repository),
) -> BankingImportService:
    return BankingImportService(repo)


def get_customer360_repository(db: MongoDatabase = Depends(get_db)) -> Customer360Repository:
    return Customer360Repository(db)


def get_aggregation_service(
    banking_repo: BankingRepository = Depends(get_banking_repository),
) -> CustomerAggregationService:
    return CustomerAggregationService(banking_repo)


def get_customer360_service(
    profile_repo: Customer360Repository = Depends(get_customer360_repository),
) -> Customer360Service:
    return Customer360Service(profile_repo)


def get_financial_analytics_engine() -> FinancialAnalyticsEngine:
    return FinancialAnalyticsEngine()


def get_financial_profile_service(
    profile_repo: Customer360Repository = Depends(get_customer360_repository),
    engine: FinancialAnalyticsEngine = Depends(get_financial_analytics_engine),
) -> FinancialProfileService:
    return FinancialProfileService(profile_repo, engine)


def get_customer_query_repository(db: MongoDatabase = Depends(get_db)) -> CustomerQueryRepository:
    return CustomerQueryRepository(db)


def get_feature_store_repository(db: MongoDatabase = Depends(get_db)) -> FeatureStoreRepository:
    return FeatureStoreRepository(db)


def get_transaction_analytics_engine() -> TransactionAnalytics:
    return TransactionAnalytics()


def get_transaction_analytics_service(
    profile_repo: Customer360Repository = Depends(get_customer360_repository),
    feature_repo: FeatureStoreRepository = Depends(get_feature_store_repository),
    engine: TransactionAnalytics = Depends(get_transaction_analytics_engine),
) -> TransactionAnalyticsService:
    return TransactionAnalyticsService(profile_repo, feature_repo, engine)


def get_behaviour_analytics_engine() -> BehaviourAnalyticsEngine:
    return BehaviourAnalyticsEngine()


def get_behaviour_analytics_service(
    profile_repo: Customer360Repository = Depends(get_customer360_repository),
    feature_repo: FeatureStoreRepository = Depends(get_feature_store_repository),
    behaviour_engine: BehaviourAnalyticsEngine = Depends(get_behaviour_analytics_engine),
    financial_engine: FinancialAnalyticsEngine = Depends(get_financial_analytics_engine),
    transaction_engine: TransactionAnalytics = Depends(get_transaction_analytics_engine),
) -> BehaviourAnalyticsService:
    return BehaviourAnalyticsService(
        profile_repo, feature_repo, behaviour_engine, financial_engine, transaction_engine
    )


def get_relationship_analytics_engine() -> RelationshipAnalytics:
    return RelationshipAnalytics()


def get_relationship_analytics_service(
    profile_repo: Customer360Repository = Depends(get_customer360_repository),
    feature_repo: FeatureStoreRepository = Depends(get_feature_store_repository),
    relationship_engine: RelationshipAnalytics = Depends(get_relationship_analytics_engine),
    financial_engine: FinancialAnalyticsEngine = Depends(get_financial_analytics_engine),
    transaction_engine: TransactionAnalytics = Depends(get_transaction_analytics_engine),
    behaviour_engine: BehaviourAnalyticsEngine = Depends(get_behaviour_analytics_engine),
) -> RelationshipAnalyticsService:
    return RelationshipAnalyticsService(
        profile_repo,
        feature_repo,
        relationship_engine,
        financial_engine,
        transaction_engine,
        behaviour_engine,
    )


def get_digital_channel_analytics_engine() -> DigitalChannelAnalytics:
    return DigitalChannelAnalytics()


def get_digital_channel_analytics_service(
    profile_repo: Customer360Repository = Depends(get_customer360_repository),
    feature_repo: FeatureStoreRepository = Depends(get_feature_store_repository),
    channel_engine: DigitalChannelAnalytics = Depends(get_digital_channel_analytics_engine),
    financial_engine: FinancialAnalyticsEngine = Depends(get_financial_analytics_engine),
    transaction_engine: TransactionAnalytics = Depends(get_transaction_analytics_engine),
    behaviour_engine: BehaviourAnalyticsEngine = Depends(get_behaviour_analytics_engine),
    relationship_engine: RelationshipAnalytics = Depends(get_relationship_analytics_engine),
) -> DigitalChannelAnalyticsService:
    return DigitalChannelAnalyticsService(
        profile_repo,
        feature_repo,
        channel_engine,
        financial_engine,
        transaction_engine,
        behaviour_engine,
        relationship_engine,
    )


def get_customer_health_analytics_engine() -> CustomerHealthAnalytics:
    return CustomerHealthAnalytics()


def get_customer_health_analytics_service(
    profile_repo: Customer360Repository = Depends(get_customer360_repository),
    feature_repo: FeatureStoreRepository = Depends(get_feature_store_repository),
    health_engine: CustomerHealthAnalytics = Depends(get_customer_health_analytics_engine),
    financial_engine: FinancialAnalyticsEngine = Depends(get_financial_analytics_engine),
    transaction_engine: TransactionAnalytics = Depends(get_transaction_analytics_engine),
    behaviour_engine: BehaviourAnalyticsEngine = Depends(get_behaviour_analytics_engine),
    relationship_engine: RelationshipAnalytics = Depends(get_relationship_analytics_engine),
    digital_engine: DigitalChannelAnalytics = Depends(get_digital_channel_analytics_engine),
) -> CustomerHealthAnalyticsService:
    return CustomerHealthAnalyticsService(
        profile_repo,
        feature_repo,
        health_engine,
        financial_engine,
        transaction_engine,
        behaviour_engine,
        relationship_engine,
        digital_engine,
    )


# --- External Customer Intelligence Layer ---

from app.external.external_enrichment_service import ExternalEnrichmentService
from app.external.external_import_service import ExternalImportService
from app.external.lead_enrichment import LeadEnrichmentEngine
from app.repositories.external_lead_repository import ExternalLeadRepository
from app.repositories.external_profile_repository import ExternalProfileRepository


def get_external_lead_repository(db: MongoDatabase = Depends(get_db)) -> ExternalLeadRepository:
    return ExternalLeadRepository(db)


def get_external_profile_repository(db: MongoDatabase = Depends(get_db)) -> ExternalProfileRepository:
    return ExternalProfileRepository(db)


def get_external_import_service(
    lead_repo: ExternalLeadRepository = Depends(get_external_lead_repository),
) -> ExternalImportService:
    return ExternalImportService(lead_repo)


def get_lead_enrichment_engine() -> LeadEnrichmentEngine:
    return LeadEnrichmentEngine()


def get_external_enrichment_service(
    lead_repo: ExternalLeadRepository = Depends(get_external_lead_repository),
    profile_repo: ExternalProfileRepository = Depends(get_external_profile_repository),
    enrichment_engine: LeadEnrichmentEngine = Depends(get_lead_enrichment_engine),
) -> ExternalEnrichmentService:
    return ExternalEnrichmentService(lead_repo, profile_repo, enrichment_engine)


# --- External Lead Analytics ---

from app.external.analytics.financial_capacity_analytics import FinancialCapacityAnalytics
from app.external.analytics.lead_behaviour_analytics import LeadBehaviourAnalytics
from app.external.analytics.lead_quality_analytics import LeadQualityAnalytics
from app.external.external_analytics_service import ExternalAnalyticsService
from app.repositories.lead_feature_store_repository import LeadFeatureStoreRepository


def get_lead_feature_store_repository(db: MongoDatabase = Depends(get_db)) -> LeadFeatureStoreRepository:
    return LeadFeatureStoreRepository(db)


def get_lead_behaviour_analytics() -> LeadBehaviourAnalytics:
    return LeadBehaviourAnalytics()


def get_financial_capacity_analytics() -> FinancialCapacityAnalytics:
    return FinancialCapacityAnalytics()


def get_lead_quality_analytics() -> LeadQualityAnalytics:
    return LeadQualityAnalytics()


def get_external_analytics_service(
    lead_repo: ExternalLeadRepository = Depends(get_external_lead_repository),
    profile_repo: ExternalProfileRepository = Depends(get_external_profile_repository),
    feature_repo: LeadFeatureStoreRepository = Depends(get_lead_feature_store_repository),
    behaviour_engine: LeadBehaviourAnalytics = Depends(get_lead_behaviour_analytics),
    financial_engine: FinancialCapacityAnalytics = Depends(get_financial_capacity_analytics),
    quality_engine: LeadQualityAnalytics = Depends(get_lead_quality_analytics),
) -> ExternalAnalyticsService:
    return ExternalAnalyticsService(
        lead_repo,
        profile_repo,
        feature_repo,
        behaviour_engine,
        financial_engine,
        quality_engine,
    )


# --- External Lead Intelligence (validation) ---

from app.external.external_intelligence_service import ExternalIntelligenceService
from app.external.intelligence.fraud_screening_engine import FraudScreeningEngine
from app.external.intelligence.income_confidence_engine import IncomeConfidenceEngine
from app.external.intelligence.kyc_readiness_engine import KycReadinessEngine
from app.external.intelligence.lead_authenticity_engine import LeadAuthenticityEngine


def get_lead_authenticity_engine() -> LeadAuthenticityEngine:
    return LeadAuthenticityEngine()


def get_income_confidence_engine() -> IncomeConfidenceEngine:
    return IncomeConfidenceEngine()


def get_fraud_screening_engine() -> FraudScreeningEngine:
    return FraudScreeningEngine()


def get_kyc_readiness_engine() -> KycReadinessEngine:
    return KycReadinessEngine()


def get_external_intelligence_service(
    lead_repo: ExternalLeadRepository = Depends(get_external_lead_repository),
    profile_repo: ExternalProfileRepository = Depends(get_external_profile_repository),
    feature_repo: LeadFeatureStoreRepository = Depends(get_lead_feature_store_repository),
    authenticity_engine: LeadAuthenticityEngine = Depends(get_lead_authenticity_engine),
    income_engine: IncomeConfidenceEngine = Depends(get_income_confidence_engine),
    fraud_engine: FraudScreeningEngine = Depends(get_fraud_screening_engine),
    kyc_engine: KycReadinessEngine = Depends(get_kyc_readiness_engine),
) -> ExternalIntelligenceService:
    return ExternalIntelligenceService(
        lead_repo,
        profile_repo,
        feature_repo,
        authenticity_engine,
        income_engine,
        fraud_engine,
        kyc_engine,
    )


# --- Behaviour Analytics Summary Layer ---

from app.behaviour_summary.behaviour_summary_service import BehaviourSummaryService


def get_behaviour_summary_service(
    customer360_repo: Customer360Repository = Depends(get_customer360_repository),
    external_profile_repo: ExternalProfileRepository = Depends(get_external_profile_repository),
    feature_repo: FeatureStoreRepository = Depends(get_feature_store_repository),
    lead_feature_repo: LeadFeatureStoreRepository = Depends(get_lead_feature_store_repository),
    lead_repo: ExternalLeadRepository = Depends(get_external_lead_repository),
) -> BehaviourSummaryService:
    return BehaviourSummaryService(
        customer360_repo,
        external_profile_repo,
        feature_repo,
        lead_feature_repo,
        lead_repo,
    )


# --- ML Dataset Builder (Phase 3.1) ---

from app.ml.dataset_builder.dataset_service import DatasetService
from app.repositories.training_dataset_repository import TrainingDatasetRepository
from app.repositories.ml_scoring_repository import MLScoringRepository


def get_training_dataset_repository(db: MongoDatabase = Depends(get_db)) -> TrainingDatasetRepository:
    return TrainingDatasetRepository(db)


def get_dataset_service(
    customer360_repo: Customer360Repository = Depends(get_customer360_repository),
    external_profile_repo: ExternalProfileRepository = Depends(get_external_profile_repository),
    lead_repo: ExternalLeadRepository = Depends(get_external_lead_repository),
    feature_repo: FeatureStoreRepository = Depends(get_feature_store_repository),
    lead_feature_repo: LeadFeatureStoreRepository = Depends(get_lead_feature_store_repository),
    training_dataset_repo: TrainingDatasetRepository = Depends(get_training_dataset_repository),
) -> DatasetService:
    return DatasetService(
        customer360_repo,
        external_profile_repo,
        lead_repo,
        feature_repo,
        lead_feature_repo,
        training_dataset_repo,
    )


# --- Repayment Capacity Prediction (Phase 3.2) ---

from app.ml.repayment.service import RepaymentCapacityService


def get_ml_scoring_repository(db: MongoDatabase = Depends(get_db)) -> MLScoringRepository:
    return MLScoringRepository(db)


def get_repayment_capacity_service(
    training_dataset_repo: TrainingDatasetRepository = Depends(get_training_dataset_repository),
    scoring_repo: MLScoringRepository = Depends(get_ml_scoring_repository),
    customer360_repo: Customer360Repository = Depends(get_customer360_repository),
    external_profile_repo: ExternalProfileRepository = Depends(get_external_profile_repository),
) -> RepaymentCapacityService:
    return RepaymentCapacityService(
        training_dataset_repo,
        scoring_repository=scoring_repo,
        customer360_repository=customer360_repo,
        external_profile_repository=external_profile_repo,
    )


# --- Product Recommendation (Phase 3.3) ---

from app.ml.product_recommendation.recommendation_service import ProductRecommendationService


def get_product_recommendation_service(
    customer360_repo: Customer360Repository = Depends(get_customer360_repository),
    external_profile_repo: ExternalProfileRepository = Depends(get_external_profile_repository),
    lead_repo: ExternalLeadRepository = Depends(get_external_lead_repository),
    feature_repo: FeatureStoreRepository = Depends(get_feature_store_repository),
    lead_feature_repo: LeadFeatureStoreRepository = Depends(get_lead_feature_store_repository),
    repayment_service: RepaymentCapacityService = Depends(get_repayment_capacity_service),
    scoring_repo: MLScoringRepository = Depends(get_ml_scoring_repository),
) -> ProductRecommendationService:
    return ProductRecommendationService(
        customer360_repo,
        external_profile_repo,
        lead_repo,
        feature_repo,
        lead_feature_repo,
        repayment_service,
        scoring_repository=scoring_repo,
    )


# --- Lead Conversion Prediction (Phase 3.4) ---

from app.ml.conversion.service import ConversionService


def get_conversion_service(
    lead_repo: ExternalLeadRepository = Depends(get_external_lead_repository),
    external_profile_repo: ExternalProfileRepository = Depends(get_external_profile_repository),
    lead_feature_repo: LeadFeatureStoreRepository = Depends(get_lead_feature_store_repository),
    scoring_repo: MLScoringRepository = Depends(get_ml_scoring_repository),
) -> ConversionService:
    return ConversionService(lead_repo, external_profile_repo, lead_feature_repo, scoring_repository=scoring_repo)


from app.ml.scoring_persistence_service import ScoringPersistenceService


def get_scoring_persistence_service(
    customer360_repo: Customer360Repository = Depends(get_customer360_repository),
    external_profile_repo: ExternalProfileRepository = Depends(get_external_profile_repository),
    lead_repo: ExternalLeadRepository = Depends(get_external_lead_repository),
    repayment_service: RepaymentCapacityService = Depends(get_repayment_capacity_service),
    product_service: ProductRecommendationService = Depends(get_product_recommendation_service),
    conversion_service: ConversionService = Depends(get_conversion_service),
    scoring_repo: MLScoringRepository = Depends(get_ml_scoring_repository),
) -> ScoringPersistenceService:
    return ScoringPersistenceService(
        customer360_repo,
        external_profile_repo,
        lead_repo,
        repayment_service,
        product_service,
        conversion_service,
        scoring_repo,
    )


# --- Explainable AI Layer ---

from app.explainability.decision_summary import DecisionSummaryBuilder
from app.explainability.openai_service import OpenAIService
from app.explainability.repository import ExplainabilityRepository
from app.explainability.service import ExplainabilityService


def get_explainability_repository(db: MongoDatabase = Depends(get_db)) -> ExplainabilityRepository:
    return ExplainabilityRepository(db)


def get_decision_summary_builder(
    customer360_repo: Customer360Repository = Depends(get_customer360_repository),
    external_profile_repo: ExternalProfileRepository = Depends(get_external_profile_repository),
    lead_repo: ExternalLeadRepository = Depends(get_external_lead_repository),
    feature_repo: FeatureStoreRepository = Depends(get_feature_store_repository),
    lead_feature_repo: LeadFeatureStoreRepository = Depends(get_lead_feature_store_repository),
    repayment_service: RepaymentCapacityService = Depends(get_repayment_capacity_service),
    product_service: ProductRecommendationService = Depends(get_product_recommendation_service),
    conversion_service: ConversionService = Depends(get_conversion_service),
) -> DecisionSummaryBuilder:
    return DecisionSummaryBuilder(
        customer360_repo,
        external_profile_repo,
        lead_repo,
        feature_repo,
        lead_feature_repo,
        repayment_service,
        product_service,
        conversion_service,
    )


def get_explainability_service(
    repository: ExplainabilityRepository = Depends(get_explainability_repository),
    summary_builder: DecisionSummaryBuilder = Depends(get_decision_summary_builder),
) -> ExplainabilityService:
    return ExplainabilityService(repository, summary_builder, OpenAIService())


# --- Internal Customer Intelligence Pipeline ---

from app.internal_pipeline.orchestrator import InternalPipelineOrchestrator
from app.internal_pipeline.pipeline_service import InternalPipelineService
from app.internal_pipeline.progress_tracker import PipelineProgressTracker
from app.internal_pipeline.validator import PipelineValidator

_pipeline_progress_tracker = PipelineProgressTracker()


def get_pipeline_progress_tracker() -> PipelineProgressTracker:
    return _pipeline_progress_tracker


def create_internal_pipeline_orchestrator(db: MongoDatabase) -> InternalPipelineOrchestrator:
    """Build an orchestrator bound to a specific database session."""
    return InternalPipelineOrchestrator(
        BankingRepository(db),
        CustomerAggregationService(BankingRepository(db)),
        Customer360Service(Customer360Repository(db)),
        FinancialProfileService(Customer360Repository(db), FinancialAnalyticsEngine()),
        TransactionAnalyticsService(
            Customer360Repository(db),
            FeatureStoreRepository(db),
            TransactionAnalytics(),
        ),
        BehaviourAnalyticsService(
            Customer360Repository(db),
            FeatureStoreRepository(db),
            BehaviourAnalyticsEngine(),
            FinancialAnalyticsEngine(),
            TransactionAnalytics(),
        ),
        RelationshipAnalyticsService(
            Customer360Repository(db),
            FeatureStoreRepository(db),
            RelationshipAnalytics(),
            FinancialAnalyticsEngine(),
            TransactionAnalytics(),
            BehaviourAnalyticsEngine(),
        ),
        DigitalChannelAnalyticsService(
            Customer360Repository(db),
            FeatureStoreRepository(db),
            DigitalChannelAnalytics(),
            FinancialAnalyticsEngine(),
            TransactionAnalytics(),
            BehaviourAnalyticsEngine(),
            RelationshipAnalytics(),
        ),
        CustomerHealthAnalyticsService(
            Customer360Repository(db),
            FeatureStoreRepository(db),
            CustomerHealthAnalytics(),
            FinancialAnalyticsEngine(),
            TransactionAnalytics(),
            BehaviourAnalyticsEngine(),
            RelationshipAnalytics(),
            DigitalChannelAnalytics(),
        ),
        FeatureStoreRepository(db),
        db=db,
    )


def get_internal_pipeline_orchestrator(
    banking_repo: BankingRepository = Depends(get_banking_repository),
    aggregation_service: CustomerAggregationService = Depends(get_aggregation_service),
    customer360_service: Customer360Service = Depends(get_customer360_service),
    financial_service: FinancialProfileService = Depends(get_financial_profile_service),
    transaction_service: TransactionAnalyticsService = Depends(get_transaction_analytics_service),
    behaviour_service: BehaviourAnalyticsService = Depends(get_behaviour_analytics_service),
    relationship_service: RelationshipAnalyticsService = Depends(get_relationship_analytics_service),
    channel_service: DigitalChannelAnalyticsService = Depends(get_digital_channel_analytics_service),
    health_service: CustomerHealthAnalyticsService = Depends(get_customer_health_analytics_service),
    feature_repo: FeatureStoreRepository = Depends(get_feature_store_repository),
    db: MongoDatabase = Depends(get_db),
) -> InternalPipelineOrchestrator:
    return InternalPipelineOrchestrator(
        banking_repo,
        aggregation_service,
        customer360_service,
        financial_service,
        transaction_service,
        behaviour_service,
        relationship_service,
        channel_service,
        health_service,
        feature_repo,
        db=db,
    )


def get_pipeline_validator(
    customer_query_repo: CustomerQueryRepository = Depends(get_customer_query_repository),
    profile_repo: Customer360Repository = Depends(get_customer360_repository),
    feature_repo: FeatureStoreRepository = Depends(get_feature_store_repository),
) -> PipelineValidator:
    return PipelineValidator(customer_query_repo, profile_repo, feature_repo)


def get_internal_pipeline_service(
    customer_query_repo: CustomerQueryRepository = Depends(get_customer_query_repository),
    profile_repo: Customer360Repository = Depends(get_customer360_repository),
    feature_repo: FeatureStoreRepository = Depends(get_feature_store_repository),
    validator: PipelineValidator = Depends(get_pipeline_validator),
    progress_tracker: PipelineProgressTracker = Depends(get_pipeline_progress_tracker),
    db: MongoDatabase = Depends(get_db),
) -> InternalPipelineService:
    return InternalPipelineService(
        customer_query_repo,
        profile_repo,
        feature_repo,
        create_internal_pipeline_orchestrator,
        validator,
        progress_tracker,
        db,
    )


# --- Platform Validation Suite ---

from pathlib import Path


def get_platform_validation_service(db: MongoDatabase = Depends(get_db)):
    from app.platform_validation.validation_service import PlatformValidationService

    project_root = Path(__file__).resolve().parent.parent
    return PlatformValidationService(db, report_dir=project_root)


# --- Engagement Layer ---


def get_engagement_service(db: MongoDatabase = Depends(get_db)):
    from app.engagement.service import EngagementService
    from app.engagement.voice_bridge import VoiceBridge

    return EngagementService(db, VoiceBridge())


def get_onboarding_service(db: MongoDatabase = Depends(get_db)):
    from app.onboarding.service import OnboardingService

    return OnboardingService(db)


def get_learning_service(
    db: MongoDatabase = Depends(get_db),
    conversion_service: ConversionService = Depends(get_conversion_service),
    scoring_service: ScoringPersistenceService = Depends(get_scoring_persistence_service),
):
    from app.learning.service import LearningService

    return LearningService(db, conversion_service, scoring_service)


def get_pipeline_orchestrator(db: MongoDatabase = Depends(get_db)):
    from app.pipeline.master_orchestrator import MasterPipelineOrchestrator

    return MasterPipelineOrchestrator(db)


def get_complete_flow_orchestrator(db: MongoDatabase = Depends(get_db)):
    from app.pipeline.full_flow_orchestrator import CompleteFlowOrchestrator

    return CompleteFlowOrchestrator(db)


def get_activation_service(db: MongoDatabase = Depends(get_db)):
    from app.activation.service import ActivationService

    return ActivationService(db)


def get_rm_desk_service(db: MongoDatabase = Depends(get_db)):
    from app.ops.rm_desk_service import RmDeskService

    return RmDeskService(db)


def get_crm_service(db: MongoDatabase = Depends(get_db)):
    from app.ops.crm_service import CrmCustomerService

    return CrmCustomerService(db)


def get_platform_summary_service(db: MongoDatabase = Depends(get_db)):
    from app.ops.platform_summary_service import PlatformSummaryService

    return PlatformSummaryService(db)

