#!/usr/bin/env python3
"""Full Tara demo pipeline: L1 import → L2 intelligence → L3 scoring → L4 ready."""

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
    print("Running full demo pipeline...")
    result = orch.run_full_demo_pipeline()
    print(f"run_id={result.run_id} success={result.success}")
    for step in result.steps:
        print(f"  [{step.status}] {step.step}: {step.detail}")


if __name__ == "__main__":
    main()
