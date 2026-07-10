"""Debug script: trace internal pipeline for first N customers."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from db_env import load_db_env

load_db_env()

from app.dependencies import (
    create_internal_pipeline_orchestrator,
    get_customer_query_repository,
    get_pipeline_progress_tracker,
    get_pipeline_validator,
)
from app.internal_pipeline.pipeline_service import InternalPipelineService
from app.repositories.customer360_repository import Customer360Repository
from app.repositories.feature_store_repository import FeatureStoreRepository
from app.utils.database import new_session


def counts(db) -> dict:
    return {
        "customers": db.customers.count_documents({}),
        "profiles": db.customer_360_profile.count_documents({}),
        "feature_store": len(db.feature_store.distinct("customer_id")),
    }


def main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    db = new_session()
    print("BEFORE:", counts(db))

    service = InternalPipelineService(
        get_customer_query_repository(db),
        Customer360Repository(db),
        FeatureStoreRepository(db),
        create_internal_pipeline_orchestrator,
        get_pipeline_validator(
            get_customer_query_repository(db),
            Customer360Repository(db),
            FeatureStoreRepository(db),
        ),
        get_pipeline_progress_tracker(),
        db,
    )

    ids = get_customer_query_repository(db).get_all_customer_ids()[:limit]
    for cid in ids:
        summary = service.build_one(cid)
        r = summary.results[0] if summary.results else None
        print(f"customer={cid} ok={summary.completed} err={r.error if r else None}")

    print("AFTER:", counts(db))
    db.close()


if __name__ == "__main__":
    main()
