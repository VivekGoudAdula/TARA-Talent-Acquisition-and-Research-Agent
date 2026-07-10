#!/usr/bin/env python3
"""Run subset pipeline with 500 internal and 500 external customers/leads."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

from app.db.mongo import MongoDatabase
from app.pipeline.master_orchestrator import MasterPipelineOrchestrator


def main() -> None:
    db = MongoDatabase()
    orch = MasterPipelineOrchestrator(db)
    print("Running subset pipeline: target=both, limit_internal=500, limit_external=500...")
    result = orch.run_subset_pipeline(
        target="both",
        limit_internal=500,
        limit_external=500,
        train_models=True,
    )
    print(f"run_id={result.run_id} success={result.success}")
    for step in result.steps:
        print(f"  [{step.status}] {step.step}: {step.detail}")


if __name__ == "__main__":
    main()
