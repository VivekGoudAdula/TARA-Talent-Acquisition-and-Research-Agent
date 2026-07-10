"""Unit tests for Internal Intelligence Pipeline orchestration."""

import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.internal_pipeline.orchestrator import (
    STAGE_CUSTOMER360,
    STAGE_COMPLETED,
    InternalPipelineOrchestrator,
)
from app.internal_pipeline.pipeline_service import InternalPipelineService
from app.internal_pipeline.progress_tracker import PipelineProgressTracker
from app.internal_pipeline.validator import PipelineValidator
from app.schemas.internal_pipeline import PipelineValidationDetail, CustomerPipelineResult
from app.utils.exceptions import CustomerNotFoundError


class InternalPipelineOrchestratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.customer_id = uuid4()
        self.banking_repo = MagicMock()
        self.aggregation = MagicMock()
        self.customer360 = MagicMock()
        self.financial = MagicMock()
        self.transaction = MagicMock()
        self.behaviour = MagicMock()
        self.relationship = MagicMock()
        self.channel = MagicMock()
        self.health = MagicMock()
        self.feature_repo = MagicMock()

        self.banking_repo.get_customer.return_value = MagicMock()
        self.aggregate = MagicMock()
        self.aggregation.aggregate.return_value = self.aggregate

        self.orchestrator = InternalPipelineOrchestrator(
            self.banking_repo,
            self.aggregation,
            self.customer360,
            self.financial,
            self.transaction,
            self.behaviour,
            self.relationship,
            self.channel,
            self.health,
            self.feature_repo,
        )

    def test_run_for_customer_executes_all_stages(self) -> None:
        result = self.orchestrator.run_for_customer(self.customer_id)

        self.assertTrue(result.success)
        self.assertIn(STAGE_CUSTOMER360, result.stages_completed)
        self.assertIn(STAGE_COMPLETED, result.stages_completed)
        self.customer360.build_profile.assert_called_once_with(self.aggregate)
        self.financial.compute_and_persist.assert_called_once_with(self.aggregate)
        self.transaction.compute_and_persist.assert_called_once_with(self.aggregate)
        self.behaviour.compute_and_persist.assert_called_once_with(self.aggregate)
        self.relationship.compute_and_persist.assert_called_once_with(self.aggregate)
        self.channel.compute_and_persist.assert_called_once_with(self.aggregate)
        self.health.compute_and_persist.assert_called_once_with(self.aggregate)
        self.feature_repo.mark_pipeline_completed.assert_called_once_with(self.customer_id)

    def test_run_for_customer_missing_customer(self) -> None:
        self.banking_repo.get_customer.return_value = None
        result = self.orchestrator.run_for_customer(self.customer_id)
        self.assertFalse(result.success)
        self.customer360.build_profile.assert_not_called()

    def test_run_for_customer_continues_after_stage_failure(self) -> None:
        self.financial.compute_and_persist.side_effect = RuntimeError("financial failed")
        result = self.orchestrator.run_for_customer(self.customer_id)
        self.assertFalse(result.success)
        self.assertEqual(result.stages_completed, [STAGE_CUSTOMER360])
        self.transaction.compute_and_persist.assert_not_called()


class PipelineValidatorTests(unittest.TestCase):
    def test_validate_detects_mismatch(self) -> None:
        customer_repo = MagicMock()
        profile_repo = MagicMock()
        feature_repo = MagicMock()
        customer_repo.count_customers.return_value = 100
        profile_repo.count_profiles.return_value = 1
        feature_repo.count_distinct_customers.return_value = 72
        feature_repo.count_rows.return_value = 500
        feature_repo.count_pipeline_completed_customers.return_value = 0

        validator = PipelineValidator(customer_repo, profile_repo, feature_repo)
        report = validator.validate()

        self.assertFalse(report.is_valid)
        self.assertGreater(len(report.mismatches), 0)


class InternalPipelineServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.customer_id = uuid4()
        self.customer_query = MagicMock()
        self.profile_repo = MagicMock()
        self.feature_repo = MagicMock()
        self.orchestrator = MagicMock()
        self.validator = MagicMock()
        self.tracker = PipelineProgressTracker()
        self.db = MagicMock()

        def factory(_session):
            return self.orchestrator

        self.service = InternalPipelineService(
            self.customer_query,
            self.profile_repo,
            self.feature_repo,
            factory,
            self.validator,
            self.tracker,
            self.db,
        )

        self.validator.validate.return_value = PipelineValidationDetail(
            customers=1,
            profiles=1,
            feature_store_customers=1,
            feature_store_rows=10,
            pipeline_completed=1,
            is_valid=True,
        )

    def test_build_one_raises_for_missing_customer(self) -> None:
        self.customer_query.customer_exists.return_value = False
        with self.assertRaises(CustomerNotFoundError):
            self.service.build_one(self.customer_id)

    def test_build_all_records_failures_and_continues(self) -> None:
        cid_ok = uuid4()
        cid_fail = uuid4()
        self.customer_query.get_all_customer_ids.return_value = [cid_ok, cid_fail]

        ok_result = CustomerPipelineResult(customer_id=cid_ok, success=True)
        fail_result = CustomerPipelineResult(
            customer_id=cid_fail,
            success=False,
            failed_stage="Financial Analytics",
            error="fail",
        )

        with patch.object(
            self.service, "_run_customer_isolated", side_effect=[ok_result, fail_result]
        ):
            summary = self.service.build_all()

        self.assertEqual(summary.completed, 1)
        self.assertEqual(summary.failed, 1)

    def test_get_status_pending_customers(self) -> None:
        cid_done = uuid4()
        cid_pending = uuid4()
        self.customer_query.count_customers.return_value = 2
        self.profile_repo.count_profiles.return_value = 1
        self.feature_repo.count_distinct_customers.return_value = 1
        self.feature_repo.count_pipeline_completed_customers.return_value = 1
        self.customer_query.get_all_customer_ids.return_value = [cid_done, cid_pending]

        profile = MagicMock(customer_id=cid_done)
        self.profile_repo.get_all_profiles.return_value = [profile]

        def pipeline_completed(customer_id):
            return customer_id == cid_done

        self.feature_repo.customer_has_pipeline_completed.side_effect = pipeline_completed

        status = self.service.get_status()
        self.assertEqual(status.pending_customers, 1)
        self.assertIn(str(cid_pending), status.pending_customer_ids)


if __name__ == "__main__":
    unittest.main()
