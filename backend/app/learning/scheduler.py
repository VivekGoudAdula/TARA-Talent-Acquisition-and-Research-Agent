"""Optional background scheduler for Layer 6 continuous improvement."""

from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler

from app.db.mongo import MongoDatabase
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


def _learning_tick() -> None:
    db = MongoDatabase()
    try:
        from app.dependencies import get_conversion_service, get_scoring_persistence_service
        from app.learning.service import LearningService
        from app.utils.database import new_session

        session = new_session()
        svc = LearningService(
            session,
            get_conversion_service(session),
            get_scoring_persistence_service(session),
        )
        svc.build_outcome_labels(limit=5000, persist=True)
        summary = svc.get_performance_summary(capture_snapshot=True)
        if summary.retrain_recommended:
            logger.info("Learning scheduler: auto-retrain — %s", summary.retrain_reason)
            result = svc.retrain_models(
                label_source="blended",
                min_outcome_labels=1,
                refresh_scores=True,
            )
            logger.info(
                "Auto-retrain complete records=%s best=%s",
                result.records_used,
                result.best_model,
            )
        logger.info(
            "Learning tick complete labels=%d retrain=%s",
            summary.outcome_labels_count,
            summary.retrain_recommended,
        )
    except Exception as exc:
        logger.warning("Learning scheduler tick failed: %s", exc)


def start_learning_scheduler(*, interval_hours: int = 24) -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        _learning_tick,
        "interval",
        hours=max(1, interval_hours),
        id="tara_learning_tick",
        replace_existing=True,
    )
    scheduler.start()
    return scheduler
